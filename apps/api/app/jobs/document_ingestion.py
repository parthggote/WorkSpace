"""Background tasks for document ingestion and future document embeddings."""

from __future__ import annotations

from uuid import UUID

from app.jobs.celery_app import celery_app
from app.services.document_ingestion import DocumentIngestionService, IngestionResult
from app.services.redis_service import RedisService


def ingest_document_sync(
    *,
    workspace_id: UUID,
    filename: str,
    content: bytes,
    uploaded_by: UUID | None = None,
    embed: bool = True,
    task_id: str | None = None,
    service: DocumentIngestionService | None = None,
    redis_service: RedisService | None = None,
) -> IngestionResult:
    redis = redis_service or RedisService()
    if task_id:
        redis.mark_task_state(task_id, "processing", {"filename": filename})

    try:
        ingestion_service = service or DocumentIngestionService()
        result = ingestion_service.ingest_bytes(
            workspace_id=workspace_id,
            filename=filename,
            content=content,
            uploaded_by=uploaded_by,
            embed=embed,
        )
    except Exception as exc:
        if task_id:
            redis.mark_task_state(task_id, "failed", {"filename": filename, "error": str(exc)})
        raise

    if task_id:
        redis.mark_task_state(
            task_id,
            "ready",
            {
                "document_id": str(result.document.id),
                "filename": filename,
                "chunk_count": len(result.chunks),
            },
        )
    return result


@celery_app.task(name="documents.ingest")
def ingest_document_task(
    workspace_id: str,
    filename: str,
    content: bytes,
    uploaded_by: str | None = None,
    task_id: str | None = None,
) -> dict[str, object]:
    result = ingest_document_sync(
        workspace_id=UUID(workspace_id),
        filename=filename,
        content=content,
        uploaded_by=UUID(uploaded_by) if uploaded_by else None,
        task_id=task_id,
    )
    return {
        "document_id": str(result.document.id),
        "workspace_id": str(result.document.workspace_id),
        "chunk_count": len(result.chunks),
        "status": result.document.status,
    }

