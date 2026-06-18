from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, get_current_user
from app.db.session import get_pool

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("")
async def usage_summary(user: CurrentUser = Depends(get_current_user), pool=Depends(get_pool)):
    rows = await pool.fetch(
        """
        SELECT
            w.id AS workspace_id,
            w.name AS workspace_name,
            COALESCE(SUM(ul.total_tokens), 0) AS total_tokens,
            COALESCE(SUM(ul.estimated_cost_usd), 0) AS estimated_cost_usd
        FROM workspaces w
        LEFT JOIN usage_logs ul ON ul.workspace_id = w.id
        WHERE w.user_id = $1
        GROUP BY w.id, w.name
        ORDER BY w.name ASC
        """,
        user.id,
    )
    return [
        {
            "workspace_id": str(row["workspace_id"]),
            "workspace_name": row["workspace_name"],
            "total_tokens": int(row["total_tokens"] or 0),
            "estimated_cost_usd": float(row["estimated_cost_usd"] or 0),
        }
        for row in rows
    ]
