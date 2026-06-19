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


import httpx

SUPPORTED_DOCUMENT_SUFFIXES = {".pdf", ".docx", ".txt", ".md", ".csv", ".json", ".log"}

@router.post("")
async def upload_document(workspace_id: str, file: UploadFile = File(...), user: CurrentUser = Depends(get_current_user), pool=Depends(get_pool)):
    await assert_workspace_owner(pool, user.id, workspace_id)
    settings = get_settings()
    
    suffix = Path(file.filename or "upload.bin").suffix.lower()
    if suffix not in SUPPORTED_DOCUMENT_SUFFIXES:
        return {
            "ok": False,
            "error": f"unsupported_file_type:{suffix or 'unknown'}",
            "supported_types": sorted(SUPPORTED_DOCUMENT_SUFFIXES),
        }

    stored_name = f"{uuid4()}{suffix}"
    
    content = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        return {"ok": False, "error": "file_too_large"}
        
    # Upload to Supabase Storage
    headers = {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key,
        "Content-Type": file.content_type or "application/octet-stream"
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.supabase_url}/storage/v1/object/Documents/{stored_name}",
            headers=headers,
            content=content,
            timeout=30.0
        )
        if resp.status_code >= 400:
            return {"ok": False, "error": f"Upload failed: {resp.text}"}
            
    storage_path = f"Documents/{stored_name}"
    
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
        storage_path,
    )
    ingest_document_task.delay(str(row["id"]), workspace_id, storage_path)
    return {"id": str(row["id"]), "status": row["status"]}
