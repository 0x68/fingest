"""AWS S3 adapter and fixture decorator."""

from typing import Any, Callable

from fingest.adapters.base import CloudAdapter
from fingest.plugin import data_fixture


class S3Adapter(CloudAdapter):
    """Adapter for AWS S3 buckets."""

    def _load_remote(self) -> Any:
        """Load data from AWS S3 using boto3."""
        try:
            import boto3
        except ImportError:
            raise ImportError(
                "boto3 is required for live S3 loading. "
                "Install it with: pip install boto3"
            )

        s3 = boto3.client("s3")
        response = s3.get_object(Bucket=self.bucket, Key=self.key)
        content = response["Body"].read()

        return self._parse_content(content)


def aws_bucket_fixture(
    bucket: str,
    key: str,
    description: str = "",
    mock: bool = True,
) -> Callable:
    """Decorator for AWS S3 bucket fixtures.

    Args:
        bucket: Name of the S3 bucket.
        key: Key/path of the object in the bucket.
        description: Optional fixture description.
        mock: If True (default), loads from the local file mapping.

    Returns:
        The decorated class or function.
    """
    loader = S3Adapter(bucket, key, mock=mock)

    def decorator(obj: Any) -> Any:
        # Use 'key' as path so fingest can resolve local file for mocking
        return data_fixture(file_path=key, description=description, loader=loader)(obj)

    return decorator
