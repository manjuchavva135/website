from __future__ import annotations

from urllib.parse import urlsplit

from shared_py import S3StorageAdapter


class RawArtifactStorage:
    def __init__(self, adapter: S3StorageAdapter, bucket_name: str) -> None:
        self.adapter = adapter
        self.bucket_name = bucket_name

    def ensure_bucket(self) -> None:
        self.adapter.ensure_bucket(self.bucket_name)

    def build_storage_key(
        self,
        source_name: str,
        document_family: str,
        checksum_sha256: str,
        source_url: str,
        content_type: str | None,
    ) -> str:
        extension = _infer_extension(source_url=source_url, content_type=content_type)
        return f"raw/{source_name}/{document_family}/{checksum_sha256}.{extension}"

    def store_artifact(
        self,
        source_name: str,
        document_family: str,
        checksum_sha256: str,
        source_url: str,
        payload: bytes,
        content_type: str | None,
    ) -> str:
        storage_key = self.build_storage_key(
            source_name=source_name,
            document_family=document_family,
            checksum_sha256=checksum_sha256,
            source_url=source_url,
            content_type=content_type,
        )
        self.adapter.upload_bytes(
            bucket_name=self.bucket_name,
            key=storage_key,
            payload=payload,
            content_type=content_type or "application/octet-stream",
        )
        return storage_key


def _infer_extension(source_url: str, content_type: str | None) -> str:
    path = urlsplit(source_url).path.lower()
    if path.endswith(".pdf") or (content_type and "pdf" in content_type.lower()):
        return "pdf"
    if path.endswith(".json") or (content_type and "json" in content_type.lower()):
        return "json"
    if path.endswith(".csv") or (content_type and "csv" in content_type.lower()):
        return "csv"
    return "html"