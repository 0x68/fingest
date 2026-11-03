"""AWS S3 simulation for boto3/botocore.

:class:`FakeS3` patches ``botocore.client.BaseClient._make_api_call``, the single
choke point every botocore client goes through. Every S3 client is served from
the in-memory store, regardless of where or when it was created. This includes
``boto3.client("s3")``, ``boto3.resource("s3")``, paginators, waiters and
``upload_file``/``download_file``. Other AWS services are passed through
untouched.

Parameters are validated against the real botocore service model and errors
are raised as the real modeled exceptions, e.g. ``client.exceptions.NoSuchKey``.
"""

from __future__ import annotations

import base64
import hashlib
import io
import re
import threading
import uuid
from collections.abc import Callable
from typing import Any

from fingest.cloud.base import FakeCloud
from fingest.cloud.store import (
    BucketAlreadyExists,
    BucketNotEmpty,
    BucketNotFound,
    ObjectNotFound,
    ObjectStore,
    StoredObject,
    to_bytes,
)

_RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")


class S3Error(Exception):
    """Internal: converted into a botocore ``ClientError`` at the boundary."""

    def __init__(self, code: str, message: str, status: int, **extra: Any) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.extra = extra


def _no_such_bucket(bucket: str) -> S3Error:
    return S3Error(
        "NoSuchBucket", "The specified bucket does not exist", 404, BucketName=bucket
    )


def _no_such_key(key: str) -> S3Error:
    return S3Error("NoSuchKey", "The specified key does not exist.", 404, Key=key)


def _quoted(etag: str) -> str:
    return f'"{etag}"'


class FakeS3(FakeCloud):
    """In-memory S3 that every botocore S3 client talks to while active."""

    provider = "s3"

    def __init__(self, store: ObjectStore | None = None) -> None:
        super().__init__(store)
        self._uploads: dict[str, dict[str, Any]] = {}
        self._uploads_lock = threading.Lock()
        self.calls: list[tuple[str, dict[str, Any]]] = []
        """Every S3 operation served, as ``(operation_name, params)``."""

    def client(self, **kwargs: Any) -> Any:
        """A ``boto3`` S3 client (region defaults to ``us-east-1``)."""
        import boto3

        kwargs.setdefault("region_name", "us-east-1")
        return boto3.client("s3", **kwargs)

    def resource(self, **kwargs: Any) -> Any:
        import boto3

        kwargs.setdefault("region_name", "us-east-1")
        return boto3.resource("s3", **kwargs)

    # -- patching --------------------------------------------------------------

    def _patches(self) -> list[tuple[str, str, Any]]:
        try:
            from botocore.client import BaseClient
        except ImportError:
            return []
        original = BaseClient._make_api_call
        fake = self

        def _make_api_call(
            client: Any, operation_name: str, api_params: dict[str, Any]
        ) -> Any:
            if client.meta.service_model.service_name != "s3":
                return original(client, operation_name, api_params)
            return fake._dispatch(client, operation_name, api_params)

        return [("botocore.client:BaseClient", "_make_api_call", _make_api_call)]

    def _dispatch(self, client: Any, operation: str, params: dict[str, Any]) -> Any:
        from botocore.validate import validate_parameters

        operation_model = client.meta.service_model.operation_model(operation)
        source = params.get("CopySource")
        if isinstance(source, dict):  # botocore's handle_copy_source_param
            params = {**params, "CopySource": f"{source['Bucket']}/{source['Key']}"}
        if operation_model.input_shape is not None:
            validate_parameters(params, operation_model.input_shape)

        handler: Callable[[dict[str, Any]], dict[str, Any]] | None = getattr(
            self, f"_op_{operation}", None
        )
        if handler is None:
            raise NotImplementedError(
                f"fingest FakeS3 does not support S3 operation {operation!r}"
            )
        self.calls.append((operation, dict(params)))
        try:
            response = handler(params)
        except S3Error as err:
            raise self._client_error(client, operation, err) from None
        except BucketNotFound as err:
            raise self._client_error(
                client, operation, _no_such_bucket(err.bucket)
            ) from None
        except ObjectNotFound as err:
            raise self._client_error(client, operation, _no_such_key(err.key)) from None
        response.setdefault(
            "ResponseMetadata",
            {
                "RequestId": "fingest",
                "HTTPStatusCode": 200,
                "HTTPHeaders": {},
                "RetryAttempts": 0,
            },
        )
        return response

    @staticmethod
    def _client_error(client: Any, operation: str, err: S3Error) -> Exception:
        response = {
            "Error": {"Code": err.code, "Message": err.message, **err.extra},
            "ResponseMetadata": {
                "RequestId": "fingest",
                "HTTPStatusCode": err.status,
                "HTTPHeaders": {},
                "RetryAttempts": 0,
            },
        }
        error_class = client.exceptions.from_code(err.code)
        exc: Exception = error_class(response, operation)
        return exc

    # -- buckets ---------------------------------------------------------------

    def _op_ListBuckets(self, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "Buckets": [
                {"Name": b.name, "CreationDate": b.created}
                for b in self.store.buckets()
            ],
            "Owner": {"DisplayName": "fingest", "ID": "fingest"},
        }

    def _op_CreateBucket(self, params: dict[str, Any]) -> dict[str, Any]:
        bucket = params["Bucket"]
        try:
            self.store.create_bucket(bucket)
        except BucketAlreadyExists:
            raise S3Error(
                "BucketAlreadyOwnedByYou",
                "Your previous request to create the named bucket succeeded "
                "and you already own it.",
                409,
                BucketName=bucket,
            ) from None
        return {"Location": f"/{bucket}"}

    def _op_DeleteBucket(self, params: dict[str, Any]) -> dict[str, Any]:
        bucket = params["Bucket"]
        try:
            self.store.delete_bucket(bucket)
        except BucketNotEmpty:
            raise S3Error(
                "BucketNotEmpty",
                "The bucket you tried to delete is not empty",
                409,
                BucketName=bucket,
            ) from None
        return {}

    def _op_HeadBucket(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self.store.has_bucket(params["Bucket"]):
            raise S3Error("404", "Not Found", 404)
        return {"BucketRegion": "us-east-1"}

    def _op_GetBucketLocation(self, params: dict[str, Any]) -> dict[str, Any]:
        self.store.bucket(params["Bucket"])
        return {"LocationConstraint": None}

    # -- objects ---------------------------------------------------------------

    def _op_PutObject(self, params: dict[str, Any]) -> dict[str, Any]:
        obj = self.store.put(
            params["Bucket"],
            params["Key"],
            to_bytes(params.get("Body", b"")),
            content_type=params.get("ContentType"),
            metadata=params.get("Metadata"),
            create_bucket=False,
        )
        return {"ETag": _quoted(obj.etag)}

    def _head(self, params: dict[str, Any], status_only: bool) -> StoredObject:
        bucket, key = params["Bucket"], params["Key"]
        if status_only and not self.store.exists(bucket, key):
            raise S3Error("404", "Not Found", 404)
        obj = self.store.head(bucket, key)
        if_match = params.get("IfMatch")
        if if_match and if_match.strip('"') not in (obj.etag, "*"):
            raise S3Error(
                "PreconditionFailed",
                "At least one of the pre-conditions you specified did not hold",
                412,
                Condition="If-Match",
            )
        if_none_match = params.get("IfNoneMatch")
        if if_none_match and if_none_match.strip('"') in (obj.etag, "*"):
            raise S3Error("304", "Not Modified", 304)
        return obj

    @staticmethod
    def _object_headers(obj: StoredObject) -> dict[str, Any]:
        return {
            "AcceptRanges": "bytes",
            "ContentLength": obj.size,
            "ContentType": obj.content_type,
            "ETag": _quoted(obj.etag),
            "LastModified": obj.last_modified,
            "Metadata": dict(obj.metadata),
        }

    def _op_HeadObject(self, params: dict[str, Any]) -> dict[str, Any]:
        return self._object_headers(self._head(params, status_only=True))

    def _op_GetObject(self, params: dict[str, Any]) -> dict[str, Any]:
        from botocore.response import StreamingBody

        obj = self._head(params, status_only=False)
        response = self._object_headers(obj)
        data = obj.data
        if params.get("Range"):
            start, end = self._parse_range(params["Range"], obj.size)
            data = data[start : end + 1]
            response["ContentRange"] = f"bytes {start}-{end}/{obj.size}"
            response["ContentLength"] = len(data)
        response["Body"] = StreamingBody(io.BytesIO(data), len(data))
        return response

    @staticmethod
    def _parse_range(header: str, size: int) -> tuple[int, int]:
        match = _RANGE_RE.match(header.strip())
        invalid = S3Error("InvalidRange", "The requested range is not satisfiable", 416)
        if not match or not any(match.groups()):
            raise invalid
        first, last = match.groups()
        if first == "":  # suffix range: last N bytes
            start, end = max(size - int(last), 0), size - 1
        else:
            start = int(first)
            end = min(int(last), size - 1) if last else size - 1
        if start >= size or start > end:
            raise invalid
        return start, end

    def _op_DeleteObject(self, params: dict[str, Any]) -> dict[str, Any]:
        self.store.delete(params["Bucket"], params["Key"], missing_ok=True)
        return {}

    def _op_DeleteObjects(self, params: dict[str, Any]) -> dict[str, Any]:
        bucket = params["Bucket"]
        deleted = []
        for entry in params["Delete"]["Objects"]:
            self.store.delete(bucket, entry["Key"], missing_ok=True)
            deleted.append({"Key": entry["Key"]})
        return {} if params["Delete"].get("Quiet") else {"Deleted": deleted}

    def _op_CopyObject(self, params: dict[str, Any]) -> dict[str, Any]:
        source = params["CopySource"]
        if isinstance(source, str):
            src_bucket, _, src_key = source.lstrip("/").partition("/")
            src_key = src_key.split("?versionId=")[0]
        else:
            src_bucket, src_key = source["Bucket"], source["Key"]
        src = self.store.head(src_bucket, src_key)
        replace = params.get("MetadataDirective") == "REPLACE"
        obj = self.store.put(
            params["Bucket"],
            params["Key"],
            src.data,
            content_type=params.get("ContentType") if replace else src.content_type,
            metadata=params.get("Metadata", {}) if replace else src.metadata,
            create_bucket=False,
        )
        return {
            "CopyObjectResult": {
                "ETag": _quoted(obj.etag),
                "LastModified": obj.last_modified,
            }
        }

    # -- listing ---------------------------------------------------------------

    def _list(
        self, params: dict[str, Any], marker: str
    ) -> tuple[list[StoredObject], list[str], bool, str]:
        """Shared listing core: returns (objects, common_prefixes, truncated, last)."""
        prefix = params.get("Prefix", "")
        delimiter = params.get("Delimiter", "")
        max_keys = params.get("MaxKeys", 1000)
        objects: list[StoredObject] = []
        prefixes: list[str] = []
        last = ""
        truncated = False
        for obj in self.store.list(params["Bucket"], prefix):
            name, is_prefix = obj.key, False
            if delimiter:
                idx = obj.key.find(delimiter, len(prefix))
                if idx >= 0:
                    name, is_prefix = obj.key[: idx + len(delimiter)], True
            if name <= marker or (is_prefix and prefixes and prefixes[-1] == name):
                continue
            if len(objects) + len(prefixes) >= max_keys:
                truncated = True
                break
            if is_prefix:
                prefixes.append(name)
            else:
                objects.append(obj)
            last = name
        return objects, prefixes, truncated, last

    @staticmethod
    def _contents(objects: list[StoredObject]) -> list[dict[str, Any]]:
        return [
            {
                "Key": o.key,
                "LastModified": o.last_modified,
                "ETag": _quoted(o.etag),
                "Size": o.size,
                "StorageClass": "STANDARD",
            }
            for o in objects
        ]

    def _listing_response(
        self,
        params: dict[str, Any],
        objects: list[StoredObject],
        prefixes: list[str],
        truncated: bool,
    ) -> dict[str, Any]:
        response: dict[str, Any] = {
            "IsTruncated": truncated,
            "Name": params["Bucket"],
            "Prefix": params.get("Prefix", ""),
            "MaxKeys": params.get("MaxKeys", 1000),
        }
        if "Delimiter" in params:
            response["Delimiter"] = params["Delimiter"]
        if objects:
            response["Contents"] = self._contents(objects)
        if prefixes:
            response["CommonPrefixes"] = [{"Prefix": p} for p in prefixes]
        return response

    def _op_ListObjectsV2(self, params: dict[str, Any]) -> dict[str, Any]:
        marker = params.get("StartAfter", "")
        token = params.get("ContinuationToken")
        if token:
            try:
                marker = base64.urlsafe_b64decode(token.encode()).decode()
            except ValueError:
                raise S3Error(
                    "InvalidArgument",
                    "The continuation token provided is incorrect",
                    400,
                ) from None
        objects, prefixes, truncated, last = self._list(params, marker)
        response = self._listing_response(params, objects, prefixes, truncated)
        response["KeyCount"] = len(objects) + len(prefixes)
        for name in ("StartAfter", "ContinuationToken"):
            if name in params:
                response[name] = params[name]
        if truncated:
            response["NextContinuationToken"] = base64.urlsafe_b64encode(
                last.encode()
            ).decode()
        return response

    def _op_ListObjects(self, params: dict[str, Any]) -> dict[str, Any]:
        marker = params.get("Marker", "")
        objects, prefixes, truncated, last = self._list(params, marker)
        response = self._listing_response(params, objects, prefixes, truncated)
        response["Marker"] = marker
        if truncated and params.get("Delimiter"):
            response["NextMarker"] = last
        return response

    # -- multipart uploads -----------------------------------------------------

    def _op_CreateMultipartUpload(self, params: dict[str, Any]) -> dict[str, Any]:
        bucket, key = params["Bucket"], params["Key"]
        self.store.bucket(bucket)
        upload_id = uuid.uuid4().hex
        with self._uploads_lock:
            self._uploads[upload_id] = {
                "Bucket": bucket,
                "Key": key,
                "ContentType": params.get("ContentType"),
                "Metadata": params.get("Metadata"),
                "Parts": {},
            }
        return {"Bucket": bucket, "Key": key, "UploadId": upload_id}

    def _upload(self, params: dict[str, Any]) -> dict[str, Any]:
        with self._uploads_lock:
            upload = self._uploads.get(params["UploadId"])
        if upload is None or (upload["Bucket"], upload["Key"]) != (
            params["Bucket"],
            params["Key"],
        ):
            raise S3Error(
                "NoSuchUpload",
                "The specified multipart upload does not exist.",
                404,
                UploadId=params["UploadId"],
            )
        return upload

    def _op_UploadPart(self, params: dict[str, Any]) -> dict[str, Any]:
        upload = self._upload(params)
        data = to_bytes(params.get("Body", b""))
        with self._uploads_lock:
            upload["Parts"][params["PartNumber"]] = data
        return {"ETag": _quoted(hashlib.md5(data).hexdigest())}

    def _op_CompleteMultipartUpload(self, params: dict[str, Any]) -> dict[str, Any]:
        upload = self._upload(params)
        requested = params.get("MultipartUpload", {}).get("Parts", [])
        chunks: list[bytes] = []
        for part in sorted(requested, key=lambda p: p["PartNumber"]):
            data = upload["Parts"].get(part["PartNumber"])
            if (
                data is None
                or part.get("ETag", "").strip('"') != hashlib.md5(data).hexdigest()
            ):
                raise S3Error(
                    "InvalidPart",
                    "One or more of the specified parts could not be found.",
                    400,
                )
            chunks.append(data)
        digests = b"".join(hashlib.md5(c).digest() for c in chunks)
        etag = f"{hashlib.md5(digests).hexdigest()}-{len(chunks)}"
        obj = self.store.put(
            upload["Bucket"],
            upload["Key"],
            b"".join(chunks),
            content_type=upload["ContentType"],
            metadata=upload["Metadata"],
            create_bucket=False,
            etag=etag,
        )
        with self._uploads_lock:
            self._uploads.pop(params["UploadId"], None)
        return {
            "Location": f"/{upload['Bucket']}/{upload['Key']}",
            "Bucket": upload["Bucket"],
            "Key": upload["Key"],
            "ETag": _quoted(obj.etag),
        }

    def _op_AbortMultipartUpload(self, params: dict[str, Any]) -> dict[str, Any]:
        self._upload(params)
        with self._uploads_lock:
            self._uploads.pop(params["UploadId"], None)
        return {}

    def _op_ListMultipartUploads(self, params: dict[str, Any]) -> dict[str, Any]:
        bucket = params["Bucket"]
        self.store.bucket(bucket)
        with self._uploads_lock:
            uploads = [
                {"UploadId": uid, "Key": u["Key"]}
                for uid, u in self._uploads.items()
                if u["Bucket"] == bucket
            ]
        return {"Bucket": bucket, "Uploads": uploads, "IsTruncated": False}
