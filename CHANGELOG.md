# Changelog

## 2.0.0

### Added
- **Cloud storage simulation:** the `fake_s3`, `fake_gcs` and `fake_azure_blob`
  fixtures (and the `FakeS3` / `FakeGCS` / `FakeAzureBlob` context managers) run
  S3, GCS and Azure Blob Storage in memory, seeded from `<root>/<bucket>/<key>`
  folders, with per-test isolation. Code under test keeps using the real SDKs.
- `fingest_s3_root`, `fingest_gcs_root`, `fingest_azure_root` ini options.
- `--fingest-live` flag for cloud object fixtures without an explicit `mock=`.
- `data_fixture(scope=..., name=..., parser=...)`; generator (yield) fixtures.
- Parsers for `.jsonl`/`.ndjson`, `.tsv`, `.txt`/`.text`/`.md`; `register_parser`.
- Optional extras: `fingest[aws]`, `fingest[gcp]`, `fingest[azure]`, `fingest[all]`.
- `py.typed`; the package is checked with `mypy --strict`.

### Changed (breaking)
- Fixtures are registered in the module that defines them. Fixtures in nested
  `conftest.py` files now work and are scoped to their directory. Before, they
  were injected globally at session start and nested conftests were missed.
- `fingest_fixture_path` is resolved against the pytest rootdir, not the CWD.
- Cloud object fixtures read `<provider root>/<bucket>/<key>`. Before, the
  bucket was ignored and `<fingest_fixture_path>/<key>` was used.
- Cloud object decorators take keyword-only options; `mock` defaults to `None`
  (follow `--fingest-live`).
- Custom loaders are now `bytes -> Any` parsers (`parser=`); the
  `data_fixture(loader=...)` argument was removed.
- XML is parsed with entity expansion and network access disabled.
- Function fixtures always receive the data as their first parameter,
  whatever it is named. `async def` functions and positional-only dependencies
  are rejected at definition time.

### Deprecated
- `register_loader(ext, path_fn)`: use `register_parser(ext, bytes_fn)`.

### Removed
- `fingest.adapters` (`CloudAdapter`, `S3Adapter`, `GCSAdapter`, `AzureBlobAdapter`).

### Fixed
- 6 tests in `test_types.py` were shadowed by duplicate names and never ran.
- The project could not be installed on Python 3.14 (lxml 5 pin).

### Tooling
- uv + ruff + mypy replace poetry/black/isort/flake8. CI tests CPython
  3.11–3.14, the lowest supported dependency versions, and an install
  without cloud SDKs.
