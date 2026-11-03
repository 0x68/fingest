# fingest

[![PyPI version](https://badge.fury.io/py/fingest.svg)](https://badge.fury.io/py/fingest)
[![Python versions](https://img.shields.io/pypi/pyversions/fingest.svg)](https://pypi.org/project/fingest/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A pytest plugin for testing code that reads data files and cloud storage:

- **Data fixtures:** turn JSON, CSV, XML (or any format you register) files into
  pytest fixtures with one decorator.
- **Cloud storage simulation:** `fake_s3`, `fake_gcs` and `fake_azure_blob`
  run **AWS S3, Google Cloud Storage and Azure Blob Storage in memory**, seeded
  from plain folders in your repo. Your code keeps using the real `boto3`,
  `google-cloud-storage` or `azure-storage-blob` API with no changes, and
  nothing goes over the network.

```bash
pip install fingest            # data fixtures + storage simulation
pip install "fingest[aws]"     # + boto3        (also: [gcp], [azure], [all])
```

---

## Simulating cloud storage

### 1. Put files in a folder per bucket

```
tests/data/
├── s3/                     # one folder per provider ...
│   └── reports/            # ... one folder per bucket / container
│       ├── users.json      # → s3://reports/users.json
│       └── 2026/11/sales.csv
├── gcs/
│   └── analytics/events/day1.jsonl
└── azure/
    └── configs/app/settings.json
```

```toml
# pyproject.toml
[tool.pytest.ini_options]
fingest_fixture_path = "tests/data"   # seed roots default to <this>/s3, /gcs, /azure
```

### 2. Test your real code

```python
# app.py: production code, unchanged
import boto3


def total_sales(bucket: str, month: str) -> float:
    s3 = boto3.client("s3")
    body = s3.get_object(Bucket=bucket, Key=f"{month}/sales.csv")["Body"].read()
    rows = body.decode().splitlines()[1:]
    return sum(float(r.split(",")[1]) for r in rows)


def archive(bucket: str, key: str) -> None:
    s3 = boto3.client("s3")
    s3.copy_object(Bucket=bucket, Key=f"archive/{key}", CopySource=f"{bucket}/{key}")
    s3.delete_object(Bucket=bucket, Key=key)
```

```python
# test_app.py
import pytest
from app import archive, total_sales


def test_total_sales(fake_s3):
    assert total_sales("reports", "2026/11") == 109.5  # read from the seed folder


def test_archive(fake_s3):
    archive("reports", "users.json")
    assert fake_s3.exists("reports", "archive/users.json")
    assert not fake_s3.exists("reports", "users.json")


def test_empty_month(fake_s3):
    fake_s3.put("reports", "2026/12/sales.csv", "id,amount\n")  # arrange in-test
    assert total_sales("reports", "2026/12") == 0


def test_missing_file(fake_s3):
    import botocore

    with pytest.raises(botocore.exceptions.ClientError, match="NoSuchKey"):
        total_sales("reports", "1999/01")
```

Every test gets a **fresh copy** of the seed data. Writes stay in memory and
never touch your files or leak into the next test.

### Provider details

| Fixture | Intercepts | Errors raised |
|---|---|---|
| `fake_s3` | **every** botocore S3 call: `boto3.client("s3")`, `boto3.resource("s3")`, paginators, `upload_file`/`download_file` (incl. multipart), clients created before the test | the real modeled exceptions: `s3.exceptions.NoSuchKey`, `NoSuchBucket`, `ClientError` with `404`, … |
| `fake_gcs` | `google.cloud.storage.Client`, `Bucket`, `Blob`, even if imported at module top before the test | `google.api_core.exceptions.NotFound`, `Conflict`, `PreconditionFailed` |
| `fake_azure_blob` | `azure.storage.blob.BlobServiceClient`, `ContainerClient`, `BlobClient` incl. `from_connection_string` / `from_*_url` | `azure.core.exceptions.ResourceNotFoundError` / `ResourceExistsError` with `error_code` |

**S3:** parameters are validated against botocore's real service model, so
a wrong argument fails just like it would against AWS. Supported operations:
Get/Put/Head/Delete/Copy object (incl. `Range`, `IfMatch`), DeleteObjects,
ListObjects(V2) with prefix/delimiter/pagination, multipart uploads, and
bucket create/delete/head/list. Anything else raises a clear
`NotImplementedError`. Other AWS services are not touched. While `fake_s3` is
active, dummy AWS credentials are set, so real ones are never used.

**GCS:** upload/download (`*_from_string|filename|file`, `download_as_*`,
`open()`), `list_blobs` with `prefix`, `delimiter` (`.prefixes`), `match_glob`,
offsets, `if_generation_match` preconditions, metadata, copy/rename, and bucket
management. As with the real SDK, `bucket.blob(name).size` is `None` until the
blob was fetched.

**Azure:** upload (with `overwrite` semantics), download (`offset`/`length`,
`encoding`), `list_blobs`, `walk_blobs`, properties/metadata, copy from URL, and
container management. Only the sync clients are simulated, not `.aio`.
`fake_azure_blob.connection_string` gives you a valid-looking connection
string for code that insists on one.

### The `fake_*` fixture API

All three fixtures share the same arrange/assert helpers:

```python
fake.put("bucket", "key.json", {"a": 1})  # bytes | str | dict/list (JSON) | file-like
fake.get_bytes / get_text / get_json / get_parsed("bucket", "key")
fake.get("bucket", "key")  # StoredObject: data, size, etag, content_type, metadata, ...
fake.exists / delete("bucket", "key")
fake.keys("bucket", prefix="2026/")  # sorted keys
fake.buckets()
fake.create_bucket("name")
fake.load_dir("some/folder", bucket="name")  # seed more data
fake.snapshot()  # {bucket: {key: bytes}} for whole-state asserts
fake_s3.calls  # [(operation, params), ...]: what your code did
fake_s3.client() / fake_gcs.client() / fake_azure_blob.service_client()
```

### Outside of pytest

The fakes are plain context managers:

```python
from fingest import FakeS3

with FakeS3() as fake:
    fake.put("bucket", "k.txt", "hi")
    boto3.client("s3", region_name="us-east-1").get_object(Bucket="bucket", Key="k.txt")
```

### Seed configuration

| ini option | default |
|---|---|
| `fingest_s3_root` | `<fingest_fixture_path>/s3` |
| `fingest_gcs_root` | `<fingest_fixture_path>/gcs` |
| `fingest_azure_root` | `<fingest_fixture_path>/azure` |

Paths are relative to the pytest rootdir. Each sub-directory of a root is a
bucket and every file below it is an object. `.gitkeep` files are ignored, so
you can commit empty buckets. Seeds are read lazily, once per session, and
only if a test uses them.

---

## Data fixtures

```python
# conftest.py
from fingest import data_fixture, JSONFixture, CSVFixture, XMLFixture


@data_fixture("users.json", description="Test users")
class users(JSONFixture): ...


@data_fixture("products.csv")
class products(CSVFixture): ...


@data_fixture("config.xml", scope="session")
class config(XMLFixture): ...


@data_fixture("orders.json")
def open_orders(data, tmp_path):  # data first, then any pytest fixtures
    return [o for o in data if o["status"] == "open"]
```

```python
def test_users(users, products, config, open_orders):
    assert users[0]["name"] == "Alice"
    assert products.filter_rows(price=lambda p: float(p) > 100)
    assert config.get_text("database/host") == "localhost"
```

- Files are resolved relative to `fingest_fixture_path`, which is relative to the
  pytest rootdir (not the current directory).
- Fixtures are scoped like hand-written ones: one defined in
  `tests/api/conftest.py` is only visible below `tests/api/`. To share fixtures
  defined in a regular module, list it in `pytest_plugins`.
- Options: `description=`, `scope=`, `name=` (defaults to the class/function
  name), `parser=` (a custom `bytes -> Any` parser).
- Function fixtures may `yield` for teardown. `async def` and positional-only
  dependencies are rejected at definition time.

### Fixtures straight from a bucket

The same, but the file comes from simulated cloud storage:

```python
from fingest import aws_bucket_fixture, gcs_fixture, azure_blob_fixture


@aws_bucket_fixture("reports", "users.json")  # s3://reports/users.json
class s3_users(JSONFixture): ...


@gcs_fixture("analytics", "events/day1.jsonl")
def events(data):
    return data


@azure_blob_fixture("configs", "app/settings.json")
class settings(JSONFixture): ...
```

If the test also uses the matching `fake_*` fixture, the object is read from
that fake, so changes made with `fake_s3.put(...)` are visible. Otherwise it
comes straight from the seed data and no SDK is patched.

**Live mode:** `mock=False` reads the object from the real service with your
ambient credentials. Leave `mock` unset and run `pytest --fingest-live` to switch
all such fixtures at once, e.g. in a nightly integration job. Live mode prints a
banner in the test header. Install the matching extra (`fingest[aws]` etc.).
For Azure, set `AZURE_STORAGE_CONNECTION_STRING`.

### Formats

| Extension | Parsed into |
|---|---|
| `.json` | `dict` / `list` |
| `.jsonl`, `.ndjson` | `list` of JSON values |
| `.csv`, `.tsv` | `list[dict[str, str]]` |
| `.xml` | `lxml` `ElementTree` (entity expansion and network access disabled) |
| `.txt`, `.text`, `.md` | `str` |

Files are decoded as UTF-8, and a BOM is tolerated. Unknown extensions raise an
error that names the file. Register your own:

```python
import yaml
from fingest import register_parser

register_parser("yaml", yaml.safe_load)  # parser receives the raw bytes
```

### Fixture classes

| Class | Highlights |
|---|---|
| `BaseFixture` | `.data`, `.description`, `len()`, `bool()`, iteration, `in`, `==` |
| `JSONFixture` | `[]`, `.get()`, `.keys()`, `.values()`, `.items()` |
| `CSVFixture` | `.rows`, `.row_count`, `.columns`, `.get_column()`, `.filter_rows(col=value_or_predicate)`, `[i]` |
| `XMLFixture` | `.root`, `.tag`, `.find()`, `.findall()`, `.xpath()`, `.get_text()`, `.to_dict()` |

---

## Upgrading from 1.x

See [CHANGELOG.md](CHANGELOG.md). In short:

- Cloud objects now live at `<root>/<provider>/<bucket>/<key>`. Before, the
  bucket was ignored and the key was looked up directly under
  `fingest_fixture_path`.
- `data_fixture(..., loader=path_fn)` became `parser=bytes_fn`.
  `register_loader` still works but is deprecated in favour of `register_parser`.
- `fingest.adapters` (`S3Adapter`, …) is gone; use the `fake_*` fixtures or
  `fingest.FakeS3` & co.
- `fingest_fixture_path` is resolved against the rootdir instead of the
  current working directory.

## License

MIT, see [LICENSE](LICENSE).
