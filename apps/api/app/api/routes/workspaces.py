from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, get_current_user, assert_workspace_owner
from app.db.session import get_pool
from app.schemas.chat import WorkspaceCreate, WorkspaceUpdate

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("")
async def list_workspaces(user: CurrentUser = Depends(get_current_user), pool=Depends(get_pool)):
    rows = await pool.fetch("SELECT id, name, color, icon FROM workspaces WHERE user_id = $1 ORDER BY created_at DESC", user.id)
    return [dict(row) | {"id": str(row["id"])} for row in rows]


@router.post("")
async def create_workspace(payload: WorkspaceCreate, user: CurrentUser = Depends(get_current_user), pool=Depends(get_pool)):
    row = await pool.fetchrow(
        "INSERT INTO workspaces (user_id, name, color, icon) VALUES ($1, $2, $3, $4) RETURNING id, name, color, icon",
        user.id,
        payload.name,
        payload.color,
        payload.icon,
    )
    return dict(row) | {"id": str(row["id"])}


@router.patch("/{workspace_id}")
async def update_workspace(workspace_id: str, payload: WorkspaceUpdate, user: CurrentUser = Depends(get_current_user), pool=Depends(get_pool)):
    await assert_workspace_owner(pool, user.id, workspace_id)
    row = await pool.fetchrow(
        """
        UPDATE workspaces
        SET name = $1
        WHERE id = $2 AND user_id = $3
        RETURNING id, name, color, icon
        """,
        payload.name,
        workspace_id,
        user.id,
    )
    return dict(row) | {"id": str(row["id"])}


@router.delete("/{workspace_id}")
async def delete_workspace(workspace_id: str, user: CurrentUser = Depends(get_current_user), pool=Depends(get_pool)):
    await assert_workspace_owner(pool, user.id, workspace_id)
    await pool.execute("DELETE FROM workspaces WHERE id = $1 AND user_id = $2", workspace_id, user.id)
    return {"ok": True}
