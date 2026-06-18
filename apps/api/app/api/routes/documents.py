from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, UploadFile

from app.core.auth import CurrentUser, assert_workspace_owner, get_current_user
from app.core.config import get_settings
from app.db.session import get_pool
from app.jobs.document_tasks import ingest_document_task

router = APIRouter(prefix="/workspaces/{workspace_id}/documents", tags=["documents"])


@router.get("")
async def list_documents(workspace_id: str, user: CurrentUser = Depends(get_current_user), pool=Depends(get_pool)):
    await assert_workspace_owner(pool, user.id, workspace_id)
    rows = await pool.fetch(
        """
        SELECT id, filename, file_type, status, error, created_at, updated_at
        FROM documents
        WHERE workspace_id = $1
        ORDER BY created_at DESC
        """,
        workspace_id,
    )
    return [dict(row) | {"id": str(row["id"])} for row in rows]


@router.post("")
async def upload_document(workspace_id: str, file: UploadFile = File(...), user: CurrentUser = Depends(get_current_user), pool=Depends(get_pool)):
    await assert_workspace_owner(pool, user.id, workspace_id)
    settings = get_settings()
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "upload.bin").suffix.lower()
    stored_name = f"{uuid4()}{suffix}"
    destination = upload_dir / stored_name
    content = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        return {"ok": False, "error": "file_too_large"}
    destination.write_bytes(content)
    row = await pool.fetchrow(
        """
        INSERT INTO documents (workspace_id, uploaded_by, filename, file_type, storage_url, status)
        VALUES ($1, $2, $3, $4, $5, 'uploaded')
        RETURNING id, status
        """,
        workspace_id,
        user.id,
        file.filename or stored_name,
        suffix.replace(".", ""),
        str(destination),
    )
    ingest_document_task.delay(str(row["id"]), workspace_id, str(destination))
    return {"id": str(row["id"]), "status": row["status"]}
