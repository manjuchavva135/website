from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import Engine, text


@dataclass(frozen=True, slots=True)
class StoredDocument:
    id: int
    checksum_sha256: str
    storage_key: str


@dataclass(frozen=True, slots=True)
class SourceDocumentRecord:
    source_name: str
    publisher: str
    source_url: str
    canonical_url: str
    title: str
    document_type: str
    mime_type: str | None
    publication_date: object | None
    checksum_sha256: str
    content_length_bytes: int | None
    storage_bucket: str
    storage_key: str
    fetch_etag: str | None
    parser_version: str
    review_status: str
    review_notes: str | None


@dataclass(frozen=True, slots=True)
class FetchRunRecord:
    source_name: str
    requested_url: str
    resolved_url: str
    http_status_code: int | None
    status: str
    fetched_checksum_sha256: str | None
    response_headers: dict[str, str]
    error_message: str | None
    source_document_id: int | None


class SourcePersistenceService:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def find_document_by_checksum(self, checksum_sha256: str) -> StoredDocument | None:
        with self.engine.begin() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT id, checksum_sha256, storage_key
                    FROM source_documents
                    WHERE checksum_sha256 = :checksum_sha256
                    ORDER BY id ASC
                    LIMIT 1
                    """
                ),
                {"checksum_sha256": checksum_sha256},
            ).mappings().first()

        if row is None:
            return None
        return StoredDocument(
            id=int(row["id"]),
            checksum_sha256=str(row["checksum_sha256"]),
            storage_key=str(row["storage_key"]),
        )

    def create_source_document(self, record: SourceDocumentRecord) -> int:
        with self.engine.begin() as connection:
            document_id = connection.execute(
                text(
                    """
                    INSERT INTO source_documents (
                        source_name,
                        publisher,
                        source_url,
                        canonical_url,
                        title,
                        document_type,
                        mime_type,
                        publication_date,
                        checksum_sha256,
                        content_length_bytes,
                        storage_bucket,
                        storage_key,
                        fetch_etag,
                        parser_version,
                        review_status,
                        review_notes
                    )
                    VALUES (
                        :source_name,
                        :publisher,
                        :source_url,
                        :canonical_url,
                        :title,
                        :document_type,
                        :mime_type,
                        :publication_date,
                        :checksum_sha256,
                        :content_length_bytes,
                        :storage_bucket,
                        :storage_key,
                        :fetch_etag,
                        :parser_version,
                        :review_status,
                        :review_notes
                    )
                    RETURNING id
                    """
                ),
                record.__dict__,
            ).scalar_one()
        return int(document_id)

    def record_fetch_run(self, record: FetchRunRecord) -> int:
        with self.engine.begin() as connection:
            if record.fetched_checksum_sha256:
                existing_row = connection.execute(
                    text(
                        """
                        SELECT id
                        FROM source_fetch_runs
                        WHERE source_name = :source_name
                          AND requested_url = :requested_url
                          AND fetched_checksum_sha256 = :fetched_checksum_sha256
                        ORDER BY id ASC
                        LIMIT 1
                        """
                    ),
                    {
                        "source_name": record.source_name,
                        "requested_url": record.requested_url,
                        "fetched_checksum_sha256": record.fetched_checksum_sha256,
                    },
                ).mappings().first()
                if existing_row is not None:
                    return int(existing_row["id"])

            fetch_run_id = connection.execute(
                text(
                    """
                    INSERT INTO source_fetch_runs (
                        source_name,
                        requested_url,
                        resolved_url,
                        http_status_code,
                        status,
                        fetched_checksum_sha256,
                        response_headers_json,
                        error_message,
                        completed_at,
                        source_document_id
                    )
                    VALUES (
                        :source_name,
                        :requested_url,
                        :resolved_url,
                        :http_status_code,
                        :status,
                        :fetched_checksum_sha256,
                        :response_headers_json,
                        :error_message,
                        CURRENT_TIMESTAMP,
                        :source_document_id
                    )
                    RETURNING id
                    """
                ),
                {
                    "source_name": record.source_name,
                    "requested_url": record.requested_url,
                    "resolved_url": record.resolved_url,
                    "http_status_code": record.http_status_code,
                    "status": record.status,
                    "fetched_checksum_sha256": record.fetched_checksum_sha256,
                    "response_headers_json": json.dumps(record.response_headers, sort_keys=True),
                    "error_message": record.error_message,
                    "source_document_id": record.source_document_id,
                },
            ).scalar_one()
        return int(fetch_run_id)