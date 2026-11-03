# Contributing to fingest

## Setup

You need [uv](https://docs.astral.sh/uv/) and Python 3.11+.

```bash
git clone https://github.com/0x68/fingest.git
cd fingest
uv sync                      # creates .venv with dev tools and all cloud SDKs
uv run pre-commit install    # optional: run checks on every commit
```

## Checks

CI runs all of these; please run them before opening a PR:

```bash
uv run pytest                 # tests (the real boto3 / GCS / Azure SDKs drive the fakes)
uv run ruff check src tests   # lint
uv run ruff format src tests  # format
uv run mypy                   # strict type checking of src/
```

CI also runs the suite against the **lowest** supported dependency versions and
**without** any cloud SDK installed. Keep both working:

```bash
uv venv /tmp/fg-low -p 3.11 && VIRTUAL_ENV=/tmp/fg-low uv pip install --resolution lowest-direct -e ".[all]" && /tmp/fg-low/bin/python -m pytest
```

## Layout

| Path | Purpose |
|---|---|
| `src/fingest/fixtures.py` | `@data_fixture` and fixture registration |
| `src/fingest/loaders.py` | parser registry (json, jsonl, csv, tsv, xml, txt) |
| `src/fingest/types.py` | `BaseFixture`, `JSONFixture`, `CSVFixture`, `XMLFixture` |
| `src/fingest/plugin.py` | pytest hooks, ini options, `fake_s3` / `fake_gcs` / `fake_azure_blob` |
| `src/fingest/cloud/store.py` | the provider-agnostic in-memory object store |
| `src/fingest/cloud/{s3,gcs,azure}.py` | the provider fakes |
| `src/fingest/cloud/decorators.py` | `@aws_bucket_fixture`, `@gcs_fixture`, `@azure_blob_fixture` |

## Adding support for another cloud SDK call

1. Implement it in the provider fake. For S3, add an `_op_<OperationName>` method
   returning the botocore-shaped response.
2. Raise the SDK's real error types, the way the existing operations do.
3. Add a test in `tests/test_fake_<provider>.py` that calls it through the
   **real SDK**, not the fake class directly.

## Releasing

Bump `version` in `pyproject.toml`, add a `CHANGELOG.md` entry, and push a tag.
The workflow publishes to PyPI through trusted publishing.
