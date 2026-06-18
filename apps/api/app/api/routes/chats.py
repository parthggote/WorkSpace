from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, assert_chat_owner, assert_workspace_owner, get_current_user
from app.db.session import get_pool
from app.schemas.chat import ChatCreate, ChatUpdate

router = APIRouter(tags=["chats"])


@router.get("/workspaces/{workspace_id}/chats")
async def list_chats(workspace_id: str, user: CurrentUser = Depends(get_current_user), pool=Depends(get_pool)):
    await assert_workspace_owner(pool, user.id, workspace_id)
    rows = await pool.fetch(
        "SELECT id, workspace_id, title, updated_at FROM chat_sessions WHERE workspace_id = $1 ORDER BY updated_at DESC",
        workspace_id,
    )
    return [dict(row) | {"id": str(row["id"]), "workspace_id": str(row["workspace_id"])} for row in rows]


@router.post("/workspaces/{workspace_id}/chats")
async def create_chat(workspace_id: str, payload: ChatCreate, user: CurrentUser = Depends(get_current_user), pool=Depends(get_pool)):
    await assert_workspace_owner(pool, user.id, workspace_id)
    row = await pool.fetchrow(
        "INSERT INTO chat_sessions (workspace_id, title) VALUES ($1, $2) RETURNING id, workspace_id, title",
        workspace_id,
        payload.title or "New chat",
    )
    return dict(row) | {"id": str(row["id"]), "workspace_id": str(row["workspace_id"])}


@router.patch("/workspaces/{workspace_id}/chats/{chat_id}")
async def update_chat(workspace_id: str, chat_id: str, payload: ChatUpdate, user: CurrentUser = Depends(get_current_user), pool=Depends(get_pool)):
    await assert_chat_owner(pool, user.id, workspace_id, chat_id)
    row = await pool.fetchrow(
        """
        UPDATE chat_sessions
        SET title = $1, updated_at = now()
        WHERE id = $2 AND workspace_id = $3
        RETURNING id, workspace_id, title, updated_at
        """,
        payload.title,
        chat_id,
        workspace_id,
    )
    return dict(row) | {"id": str(row["id"]), "workspace_id": str(row["workspace_id"])}


@router.delete("/workspaces/{workspace_id}/chats/{chat_id}")
async def delete_chat(workspace_id: str, chat_id: str, user: CurrentUser = Depends(get_current_user), pool=Depends(get_pool)):
    await assert_chat_owner(pool, user.id, workspace_id, chat_id)
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("DELETE FROM message_embeddings WHERE workspace_id = $1 AND chat_id = $2", workspace_id, chat_id)
            await conn.execute("DELETE FROM retrieval_results WHERE retrieval_run_id IN (SELECT id FROM retrieval_runs WHERE workspace_id = $1 AND chat_id = $2)", workspace_id, chat_id)
            await conn.execute("DELETE FROM retrieval_runs WHERE workspace_id = $1 AND chat_id = $2", workspace_id, chat_id)
            await conn.execute("DELETE FROM usage_logs WHERE workspace_id = $1 AND chat_id = $2", workspace_id, chat_id)
            await conn.execute("DELETE FROM messages WHERE workspace_id = $1 AND chat_id = $2", workspace_id, chat_id)
            await conn.execute("DELETE FROM chat_sessions WHERE id = $1 AND workspace_id = $2", chat_id, workspace_id)
    return {"ok": True}


@router.get("/workspaces/{workspace_id}/chats/{chat_id}/messages")
async def list_messages(workspace_id: str, chat_id: str, user: CurrentUser = Depends(get_current_user), pool=Depends(get_pool)):
    await assert_chat_owner(pool, user.id, workspace_id, chat_id)
    rows = await pool.fetch(
        "SELECT id, role, content, reasoning_summary, created_at FROM messages WHERE workspace_id = $1 AND chat_id = $2 ORDER BY created_at ASC",
        workspace_id,
        chat_id,
    )
    return [dict(row) | {"id": str(row["id"])} for row in rows]
