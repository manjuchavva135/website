from __future__ import annotations

from botocore.client import BaseClient
import boto3


class S3StorageAdapter:
    def __init__(
        self,
        endpoint_url: str,
        region: str,
        access_key: str,
        secret_key: str,
        use_ssl: bool = False,
    ) -> None:
        self.client: BaseClient = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            use_ssl=use_ssl,
        )

    def ensure_bucket(self, bucket_name: str) -> None:
        existing = self.client.list_buckets().get("Buckets", [])
        if not any(bucket["Name"] == bucket_name for bucket in existing):
            self.client.create_bucket(Bucket=bucket_name)

    def upload_bytes(self, bucket_name: str, key: str, payload: bytes, content_type: str) -> None:
        self.client.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=payload,
            ContentType=content_type,
        )

    def get_object_bytes(self, bucket_name: str, key: str) -> bytes:
        response = self.client.get_object(Bucket=bucket_name, Key=key)
        return response["Body"].read()
