"""Resolution of fingest ini options into filesystem paths."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURE_PATH_INI = "fingest_fixture_path"
LIVE_OPTION = "fingest_live"

PROVIDER_ROOT_INI = {
    "s3": "fingest_s3_root",
    "gcs": "fingest_gcs_root",
    "azure": "fingest_azure_root",
}


def _resolve(config: pytest.Config, raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = config.rootpath / path
    return path


def fixture_root(config: pytest.Config) -> Path:
    """Base directory for ``@data_fixture`` files (relative to the rootdir)."""
    return _resolve(config, str(config.getini(FIXTURE_PATH_INI)))


def provider_root(config: pytest.Config, provider: str) -> Path:
    """Seed directory for a simulated storage provider.

    Defaults to ``<fingest_fixture_path>/<provider>`` (e.g. ``tests/data/s3``).
    """
    raw = str(config.getini(PROVIDER_ROOT_INI[provider]) or "")
    if raw:
        return _resolve(config, raw)
    return fixture_root(config) / provider


def live_mode(config: pytest.Config) -> bool:
    """Whether cloud fixtures without an explicit ``mock=`` hit real services."""
    return bool(config.getoption(LIVE_OPTION, default=False))
