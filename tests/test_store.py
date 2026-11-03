import threading

import pytest

from fingest.cloud.store import (
    BucketAlreadyExists,
    BucketNotEmpty,
    BucketNotFound,
    ObjectNotFound,
    ObjectStore,
)


def test_put_coerces_payloads_and_guesses_content_type():
    store = ObjectStore()
    assert store.put("b", "a.json", {"x": 1}).content_type == "application/json"
    assert store.put("b", "a.txt", "héllo").data == "héllo".encode()
    assert store.put("b", "blob", b"\x00").content_type == "application/octet-stream"
    assert store.get_json("b", "a.json") == {"x": 1}
    assert store.get_parsed("b", "a.json") == {"x": 1}


def test_generations_increase_and_etag_is_md5():
    store = ObjectStore()
    first = store.put("b", "k", b"1")
    second = store.put("b", "k", b"1")
    assert second.generation > first.generation
    assert first.etag == "c4ca4238a0b923820dcc509a6f75849b"


def test_bucket_lifecycle_errors():
    store = ObjectStore()
    store.create_bucket("b")
    with pytest.raises(BucketAlreadyExists):
        store.create_bucket("b")
    store.put("b", "k", b"")
    with pytest.raises(BucketNotEmpty):
        store.delete_bucket("b")
    store.delete_bucket("b", force=True)
    with pytest.raises(BucketNotFound, match="'b' does not exist"):
        store.head("b", "k")
    with pytest.raises(BucketNotFound):
        store.put("b", "k", b"", create_bucket=False)


def test_missing_object():
    store = ObjectStore()
    store.create_bucket("b")
    with pytest.raises(ObjectNotFound, match="'k' does not exist in bucket 'b'"):
        store.get_bytes("b", "k")
    store.delete("b", "k", missing_ok=True)
    with pytest.raises(ObjectNotFound):
        store.delete("b", "k")


def test_load_dir_layouts(tmp_path):
    (tmp_path / "b1" / "nested").mkdir(parents=True)
    (tmp_path / "b1" / "nested" / "x.txt").write_text("x")
    (tmp_path / "b1" / ".gitkeep").write_text("")
    (tmp_path / "b2").mkdir()
    (tmp_path / "stray.txt").write_text("ignored: not in a bucket dir")

    store = ObjectStore()
    store.load_dir(tmp_path)
    assert store.snapshot() == {"b1": {"nested/x.txt": b"x"}, "b2": {}}

    single = ObjectStore()
    single.load_dir(tmp_path / "b1", bucket="custom")
    assert single.snapshot() == {"custom": {"nested/x.txt": b"x"}}

    with pytest.raises(NotADirectoryError):
        store.load_dir(tmp_path / "nope")


def test_copy_is_independent():
    store = ObjectStore()
    store.put("b", "k", b"1")
    clone = store.copy()
    clone.put("b", "k", b"2")
    clone.put("other", "k", b"3")
    assert store.snapshot() == {"b": {"k": b"1"}}
    assert clone.snapshot() == {"b": {"k": b"2"}, "other": {"k": b"3"}}


def test_list_prefix_sorted():
    store = ObjectStore()
    for key in ("b/2", "a/1", "b/1"):
        store.put("bk", key, b"")
    assert [o.key for o in store.list("bk", "b/")] == ["b/1", "b/2"]


def test_concurrent_puts():
    store = ObjectStore()

    def worker(n):
        for i in range(100):
            store.put("b", f"{n}/{i}", b"x")

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(store.list("b")) == 800
    assert len({o.generation for o in store.list("b")}) == 800
