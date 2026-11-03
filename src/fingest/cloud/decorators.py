"""``@data_fixture`` counterparts that read from a (simulated) cloud bucket."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

import pytest

from fingest._config import live_mode
from fingest.fixtures import Scope, register
from fingest.loaders import Parser

T = TypeVar("T")

_FAKE_FIXTURE = {"s3": "fake_s3", "gcs": "fake_gcs", "azure": "fake_azure_blob"}


@dataclass(frozen=True)
class CloudSource:
    """An object in a bucket, served by the matching fake unless running live."""

    provider: str
    bucket: str
    key: str
    mock: bool | None

    @property
    def name(self) -> str:
        return self.key

    def read(self, request: pytest.FixtureRequest) -> bytes:
        mock = self.mock if self.mock is not None else not live_mode(request.config)
        if not mock:
            return _LIVE_READERS[self.provider](self.bucket, self.key)
        from fingest.plugin import seed_store

        fake_name = _FAKE_FIXTURE[self.provider]
        if request.scope == "function" and fake_name in request.fixturenames:
            # The test also uses the fake: read from it, so arrange steps
            # (fake_s3.put(...)) are visible to the data fixture.
            fake = request.getfixturevalue(fake_name)
            return fake.get_bytes(self.bucket, self.key)  # type: ignore[no-any-return]
        # Otherwise read the pristine seed data; no SDK gets patched.
        return seed_store(request.config, self.provider).get_bytes(
            self.bucket, self.key
        )


def _read_s3(bucket: str, key: str) -> bytes:
    try:
        import boto3
    except ImportError as exc:
        raise ImportError(
            "live S3 access requires: pip install 'fingest[aws]'"
        ) from exc
    body = boto3.client("s3").get_object(Bucket=bucket, Key=key)["Body"]
    return body.read()  # type: ignore[no-any-return,unused-ignore]


def _read_gcs(bucket: str, key: str) -> bytes:
    try:
        from google.cloud import storage
    except ImportError as exc:
        raise ImportError(
            "live GCS access requires: pip install 'fingest[gcp]'"
        ) from exc
    return storage.Client().bucket(bucket).blob(key).download_as_bytes()  # type: ignore[no-any-return]


def _read_azure(container: str, blob: str) -> bytes:
    try:
        from azure.storage.blob import BlobServiceClient
    except ImportError as exc:
        raise ImportError(
            "live Azure access requires: pip install 'fingest[azure]'"
        ) from exc
    conn_str = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    if not conn_str:
        raise RuntimeError(
            "live Azure access requires the AZURE_STORAGE_CONNECTION_STRING "
            "environment variable"
        )
    client = BlobServiceClient.from_connection_string(conn_str)
    return client.get_blob_client(container, blob).download_blob().readall()


_LIVE_READERS: dict[str, Callable[[str, str], bytes]] = {
    "s3": _read_s3,
    "gcs": _read_gcs,
    "azure": _read_azure,
}


def _cloud_fixture(
    provider: str,
    bucket: str,
    key: str,
    *,
    description: str,
    parser: Parser | None,
    scope: Scope,
    name: str | None,
    mock: bool | None,
) -> Callable[[T], T]:
    source = CloudSource(provider, bucket, key, mock)

    def decorator(obj: T) -> T:
        return register(
            obj, source, description=description, parser=parser, scope=scope, name=name
        )

    return decorator


def aws_bucket_fixture(
    bucket: str,
    key: str,
    *,
    description: str = "",
    parser: Parser | None = None,
    scope: Scope = "function",
    name: str | None = None,
    mock: bool | None = None,
) -> Callable[[T], T]:
    """Like ``@data_fixture``, for the S3 object ``s3://<bucket>/<key>``.

    In mock mode (the default) the object is read from the simulated S3, which
    is seeded from ``<fingest_s3_root>/<bucket>/<key>``. ``mock=False`` (or the
    ``--fingest-live`` flag when ``mock`` is left unset) reads it from real S3.
    """
    return _cloud_fixture(
        "s3", bucket, key, description=description, parser=parser,
        scope=scope, name=name, mock=mock,
    )  # fmt: skip


def gcs_fixture(
    bucket: str,
    key: str,
    *,
    description: str = "",
    parser: Parser | None = None,
    scope: Scope = "function",
    name: str | None = None,
    mock: bool | None = None,
) -> Callable[[T], T]:
    """Like ``@data_fixture``, for the GCS object ``gs://<bucket>/<key>``.

    Seeded from ``<fingest_gcs_root>/<bucket>/<key>`` in mock mode.
    """
    return _cloud_fixture(
        "gcs", bucket, key, description=description, parser=parser,
        scope=scope, name=name, mock=mock,
    )  # fmt: skip


def azure_blob_fixture(
    container: str,
    blob: str,
    *,
    description: str = "",
    parser: Parser | None = None,
    scope: Scope = "function",
    name: str | None = None,
    mock: bool | None = None,
) -> Callable[[T], T]:
    """Like ``@data_fixture``, for an Azure blob in ``container``.

    Seeded from ``<fingest_azure_root>/<container>/<blob>`` in mock mode. Live
    mode authenticates with ``AZURE_STORAGE_CONNECTION_STRING``.
    """
    return _cloud_fixture(
        "azure", container, blob, description=description, parser=parser,
        scope=scope, name=name, mock=mock,
    )  # fmt: skip


__all__: list[str] = [
    "CloudSource",
    "aws_bucket_fixture",
    "azure_blob_fixture",
    "gcs_fixture",
]
