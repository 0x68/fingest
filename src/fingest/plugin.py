"""pytest entry point: ini options, CLI flags and the cloud storage fixtures."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

import pytest

from fingest._config import (
    FIXTURE_PATH_INI,
    LIVE_OPTION,
    PROVIDER_ROOT_INI,
    live_mode,
    provider_root,
)
from fingest.cloud.store import ObjectStore

if TYPE_CHECKING:  # the fakes are imported lazily, only when a fixture is used
    from fingest.cloud.azure import FakeAzureBlob
    from fingest.cloud.base import FakeCloud
    from fingest.cloud.gcs import FakeGCS
    from fingest.cloud.s3 import FakeS3

_AWS_TEST_ENV = {
    "AWS_ACCESS_KEY_ID": "fingest",
    "AWS_SECRET_ACCESS_KEY": "fingest",
    "AWS_DEFAULT_REGION": "us-east-1",
    "AWS_EC2_METADATA_DISABLED": "true",
}

_SEED_CACHE = pytest.StashKey[dict[str, ObjectStore]]()


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("fingest", "fingest data fixtures and cloud storage fakes")
    group.addoption(
        "--fingest-live",
        action="store_true",
        dest=LIVE_OPTION,
        default=False,
        help="cloud fixtures without an explicit mock= read from the real services",
    )
    parser.addini(
        FIXTURE_PATH_INI,
        help="base directory of @data_fixture files, relative to the rootdir",
        default="data",
    )
    for provider, ini in PROVIDER_ROOT_INI.items():
        parser.addini(
            ini,
            help=f"seed directory for the simulated {provider} storage "
            f"(<bucket>/<key> layout); default: <{FIXTURE_PATH_INI}>/{provider}",
            default="",
        )


def pytest_configure(config: pytest.Config) -> None:
    config.stash[_SEED_CACHE] = {}


def pytest_report_header(config: pytest.Config) -> str | None:
    if live_mode(config):
        return (
            "fingest: LIVE mode - cloud fixtures without mock= read from real "
            "S3/GCS/Azure using your ambient credentials"
        )
    return None


def seed_store(config: pytest.Config, provider: str) -> ObjectStore:
    """The provider's seed data, read from disk once per session.

    Treat it as read-only; tests get independent copies via the fake fixtures.
    """
    cache = config.stash[_SEED_CACHE]
    if provider not in cache:
        store = ObjectStore()
        root = provider_root(config, provider)
        if root.is_dir():
            store.load_dir(root)
        cache[provider] = store
    return cache[provider]


def _fake(request: pytest.FixtureRequest, fake: FakeCloud) -> Iterator[FakeCloud]:
    fake.store = seed_store(request.config, fake.provider).copy()
    with fake:
        yield fake


@pytest.fixture
def fake_s3(request: pytest.FixtureRequest) -> Iterator[FakeS3]:
    """Simulated AWS S3, seeded from ``fingest_s3_root``.

    Every boto3/botocore S3 client is served from memory for the duration of the
    test; writes never touch the seed files and never leak into other tests.
    """
    from fingest.cloud.s3 import FakeS3

    # Dummy credentials: avoids slow credential-chain lookups (EC2 metadata) and
    # guarantees real credentials are never used while S3 is faked.
    with pytest.MonkeyPatch.context() as mp:
        for name, value in _AWS_TEST_ENV.items():
            mp.setenv(name, value)
        for name in ("AWS_PROFILE", "AWS_SESSION_TOKEN", "AWS_SECURITY_TOKEN"):
            mp.delenv(name, raising=False)
        yield from _fake(request, FakeS3())  # type: ignore[misc]


@pytest.fixture
def fake_gcs(request: pytest.FixtureRequest) -> Iterator[FakeGCS]:
    """Simulated Google Cloud Storage, seeded from ``fingest_gcs_root``."""
    from fingest.cloud.gcs import FakeGCS

    yield from _fake(request, FakeGCS())  # type: ignore[misc]


@pytest.fixture
def fake_azure_blob(request: pytest.FixtureRequest) -> Iterator[FakeAzureBlob]:
    """Simulated Azure Blob Storage, seeded from ``fingest_azure_root``."""
    from fingest.cloud.azure import FakeAzureBlob

    yield from _fake(request, FakeAzureBlob())  # type: ignore[misc]
