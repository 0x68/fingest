"""FakeAzureBlob exercised through the real azure-storage-blob entry points."""

import pytest

pytest.importorskip("azure.storage.blob")
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import (
    BlobClient,
    BlobServiceClient,
    ContainerClient,
    ContentSettings,
)

from fingest.cloud.azure import FakeAzureBlob, FakeBlobServiceClient


@pytest.fixture
def service(fake_azure_blob):
    return BlobServiceClient.from_connection_string(fake_azure_blob.connection_string)


def test_seeded_and_read(service):
    container = service.get_container_client("configs")
    names = [b.name for b in container.list_blobs()]
    assert names == ["app/config.xml", "app/settings.json"]  # .gitkeep ignored
    data = container.download_blob("app/settings.json").readall()
    assert data == b'{"feature_flags":{"beta":true}}'
    text = service.get_blob_client("configs", "app/settings.json").download_blob(
        encoding="utf-8"
    )
    assert text.readall().startswith("{")


def test_all_constructors_are_faked(fake_azure_blob):
    fake_azure_blob.put("c", "k", b"v")
    url = "https://acct.blob.core.windows.net"
    assert isinstance(BlobServiceClient(url, credential="key"), FakeBlobServiceClient)
    assert ContainerClient(url, "c").exists()
    assert ContainerClient.from_container_url(f"{url}/c").exists()
    assert BlobClient(url, "c", "k").download_blob().readall() == b"v"
    assert BlobClient.from_blob_url(f"{url}/c/k?sv=sas").exists()
    conn = fake_azure_blob.connection_string
    assert BlobClient.from_connection_string(conn, "c", "k").exists()


def test_upload_overwrite_semantics(service, fake_azure_blob):
    container = service.get_container_client("configs")
    container.upload_blob(
        "new.csv", "a,b\n1,2", content_settings=ContentSettings(content_type="text/csv")
    )
    assert fake_azure_blob.get("configs", "new.csv").content_type == "text/csv"
    with pytest.raises(ResourceExistsError) as exc:
        container.upload_blob("new.csv", "again")
    assert exc.value.error_code == "BlobAlreadyExists"
    assert exc.value.status_code == 409
    container.upload_blob("new.csv", "again", overwrite=True, metadata={"v": "2"})
    props = container.get_blob_client("new.csv").get_blob_properties()
    assert props.size == 5
    assert props.metadata == {"v": "2"}
    assert props["name"] == "new.csv"


def test_not_found_errors(service):
    with pytest.raises(ResourceNotFoundError) as exc:
        service.get_blob_client("configs", "missing").download_blob()
    assert exc.value.error_code == "BlobNotFound"
    with pytest.raises(ResourceNotFoundError) as exc:
        service.get_container_client("missing").upload_blob("k", b"")
    assert exc.value.error_code == "ContainerNotFound"
    assert not service.get_blob_client("configs", "missing").exists()


def test_walk_blobs_and_ranges(service):
    container = service.get_container_client("configs")
    assert [b.name for b in container.walk_blobs()] == ["app/"]
    assert [b.name for b in container.walk_blobs(name_starts_with="app/")] == [
        "app/config.xml",
        "app/settings.json",
    ]
    part = container.download_blob("app/settings.json", offset=2, length=7).readall()
    assert part == b"feature"


def test_container_lifecycle_and_copy(service, fake_azure_blob):
    service.create_container("fresh")
    with pytest.raises(ResourceExistsError):
        service.create_container("fresh")
    assert [c.name for c in service.list_containers()] == ["configs", "fresh"]
    src = service.get_blob_client("configs", "app/config.xml")
    dst = service.get_blob_client("fresh", "copy.xml")
    assert dst.start_copy_from_url(src.url)["copy_status"] == "success"
    assert fake_azure_blob.get_bytes("fresh", "copy.xml") == fake_azure_blob.get_bytes(
        "configs", "app/config.xml"
    )
    dst.delete_blob()
    service.delete_container("fresh")
    assert fake_azure_blob.buckets() == ["configs"]


def test_stop_restores_real_clients():
    with FakeAzureBlob():
        pass
    real = BlobServiceClient("https://acct.blob.core.windows.net")
    assert type(real) is BlobServiceClient
