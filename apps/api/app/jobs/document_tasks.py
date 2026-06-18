import os
import tempfile
import httpx
from pathlib import Path
import asyncio
import asyncpg

from app.core.config import get_settings
from app.jobs.celery_app import celery_app
from app.services.document_ingestion import clean_text_for_postgres
from app.services.embeddings import get_embedding_service
from app.services.memory import vector_literal


def extract_text(path: str) -> str:
    source = Path(path)
    if source.suffix.lower() == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(source))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if source.suffix.lower() in {".docx"}:
        import docx

        doc = docx.Document(str(source))
        return "\n".join(paragraph.text for paragraph in doc.paragraphs)
    return source.read_text(encoding="utf-8", errors="ignore")


def chunk_text(text: str, size: int = 2200, overlap: int = 250) -> list[str]:
    text = clean_text_for_postgres(text)
    clean = " ".join(text.split())
    chunks = []
    index = 0
    while index < len(clean):
        chunk = clean[index:index + size]
        if len(chunk) > 150:
            chunks.append(chunk)
        index += max(size - overlap, 1)
    return chunks


def iter_batches(items: list[str], batch_size: int) -> list[list[str]]:
    size = max(batch_size, 1)
    return [items[index:index + size] for index in range(0, len(items), size)]


@celery_app.task(name="documents.ingest")
def ingest_document_task(document_id: str, workspace_id: str, path: str) -> dict:
    return asyncio.run(_ingest_document(document_id, workspace_id, path))


async def _ingest_document(document_id: str, workspace_id: str, path: str) -> dict:
    settings = get_settings()
    if not settings.database_url:
        return {"document_id": document_id, "workspace_id": workspace_id, "status": "skipped_no_database"}

    pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=1)
    embedding_service = get_embedding_service()
    
    suffix = Path(path).suffix.lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        temp_path = tmp.name
        
    try:
        await pool.execute("UPDATE documents SET status = 'processing', updated_at = now() WHERE id = $1", document_id)
        
        if path.startswith("Documents/"):
            headers = {
                "Authorization": f"Bearer {settings.supabase_service_role_key}",
                "apikey": settings.supabase_service_role_key
            }
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{settings.supabase_url}/storage/v1/object/public/{path}", headers=headers, timeout=60.0)
                if resp.status_code == 404 or resp.status_code == 403:
                    # Try authenticated download
                    resp = await client.get(f"{settings.supabase_url}/storage/v1/object/{path}", headers=headers, timeout=60.0)
                if resp.status_code >= 400:
                    raise Exception(f"Failed to download document: {resp.status_code} {resp.text}")
                with open(temp_path, "wb") as f:
                    f.write(resp.content)
            
            text = clean_text_for_postgres(extract_text(temp_path))
        else:
            text = clean_text_for_postgres(extract_text(path))
            
        chunks = chunk_text(text)
        vectors: list[list[float]] = []
        for batch in iter_batches(chunks, settings.embedding_batch_size):
            vectors.extend(embedding_service.embed_texts(batch))

        async with pool.acquire() as conn:
            async with conn.transaction():
                for chunk_index, chunk in enumerate(chunks):
                    chunk = clean_text_for_postgres(chunk)
                    if not chunk:
                        continue
                    vector = vector_literal(vectors[chunk_index])
                    chunk_row = await conn.fetchrow(
                        """
                        INSERT INTO document_chunks (workspace_id, document_id, chunk_index, content, token_count)
                        VALUES ($1, $2, $3, $4, $5)
                        ON CONFLICT (document_id, chunk_index)
                        DO UPDATE SET content = EXCLUDED.content, token_count = EXCLUDED.token_count
                        RETURNING id
                        """,
                        workspace_id,
                        document_id,
                        chunk_index,
                        chunk,
                        len(chunk.split()),
                    )
                    await conn.execute(
                        """
                        INSERT INTO message_embeddings (
                            message_id,
                            workspace_id,
                            chat_id,
                            source_type,
                            content_chunk,
                            embedding,
                            document_id,
                            document_chunk_id,
                            chunk_index,
                            token_count
                        )
                        VALUES (NULL, $1, NULL, 'document', $2, $3::vector, $4, $5, $6, $7)
                        """,
                        workspace_id,
                        chunk,
                        vector,
                        document_id,
                        str(chunk_row["id"]),
                        chunk_index,
                        len(chunk.split()),
                    )
                await conn.execute("UPDATE documents SET status = 'ready', updated_at = now() WHERE id = $1", document_id)
        return {"document_id": document_id, "workspace_id": workspace_id, "status": "ready", "chunk_count": len(chunks)}
    except Exception as exc:
        await pool.execute("UPDATE documents SET status = 'failed', error = $2, updated_at = now() WHERE id = $1", document_id, str(exc)[:1000])
        raise
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        await pool.close()
