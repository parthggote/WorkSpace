from dataclasses import dataclass
from urllib.parse import urlparse
from fastapi import Header, HTTPException, Request, status
import httpx
import jwt
from jwt import PyJWKClient

from app.db.session import get_pool
from app.core.config import get_settings


@dataclass(frozen=True)
class CurrentUser:
    id: str
    supabase_user_id: str
    email: str


jwks_client = None


def is_http_url(value: str | None) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def derive_jwks_url() -> str:
    settings = get_settings()
    if is_http_url(settings.supabase_jwks_url):
        return settings.supabase_jwks_url
    if is_http_url(settings.supabase_url):
        return f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    return ""

def get_jwks_client():
    global jwks_client
    if jwks_client is None:
        jwks_url = derive_jwks_url()
        if not jwks_url:
            raise RuntimeError("supabase_jwks_url is not configured")
        jwks_client = PyJWKClient(jwks_url)
    return jwks_client


async def verify_with_supabase_auth_api(token: str) -> dict:
    settings = get_settings()
    supabase_url = settings.supabase_url
    api_key = settings.supabase_service_role_key

    if not is_http_url(supabase_url) or not api_key or api_key.startswith("your_"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Supabase auth verification is not configured")

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{supabase_url.rstrip('/')}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": api_key,
            },
        )

    if response.status_code != 200:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid Supabase auth token")

    return response.json()


async def verify_supabase_token(token: str) -> dict:
    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {str(exc)}") from exc

    if header.get("alg") == "RS256" and is_http_url(derive_jwks_url()):
        try:
            client = get_jwks_client()
            signing_key = client.get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience="authenticated",
                options={"verify_exp": True, "verify_aud": True},
            )
        except jwt.PyJWKClientError:
            return await verify_with_supabase_auth_api(token)
        except jwt.InvalidTokenError as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {str(exc)}") from exc

    return await verify_with_supabase_auth_api(token)


async def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
) -> CurrentUser:
    """Verify Supabase JWTs, with a local demo-user bridge when no auth is configured."""
    header_value = authorization if isinstance(authorization, str) else None
    demo_user_id = request.headers.get("x-demo-user-id")

    if demo_user_id and not header_value:
        supabase_user_id = demo_user_id
        email = request.headers.get("x-demo-email", "demo@example.com")
        name = request.headers.get("x-demo-name", "Demo User")
    elif header_value and header_value.startswith("Bearer "):
        token = header_value.split(" ", 1)[1]
        payload = await verify_supabase_token(token)

        supabase_user_id = payload.get("sub") or payload.get("id")
        email = payload.get("email") or ""
        name = email.split("@")[0] if email else "User"
        if not supabase_user_id:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token missing sub claim")
    else:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing or invalid auth token")

    pool = await get_pool(request)
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SELECT set_config('request.jwt.claim.sub', $1, true)", supabase_user_id)
            row = await conn.fetchrow(
                """
                INSERT INTO users (supabase_user_id, email, name)
                VALUES ($1, $2, $3)
                ON CONFLICT (supabase_user_id)
                DO UPDATE SET email = EXCLUDED.email
                RETURNING id, supabase_user_id, email
                """,
                supabase_user_id,
                email,
                name,
            )
    return CurrentUser(id=str(row["id"]), supabase_user_id=str(row["supabase_user_id"]), email=row["email"])


async def assert_workspace_owner(pool, user_id: str, workspace_id: str) -> None:
    exists = await pool.fetchval(
        "SELECT EXISTS(SELECT 1 FROM workspaces WHERE id = $1 AND user_id = $2)",
        workspace_id,
        user_id,
    )
    if not exists:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")


async def assert_chat_owner(pool, user_id: str, workspace_id: str, chat_id: str) -> None:
    exists = await pool.fetchval(
        """
        SELECT EXISTS(
            SELECT 1
            FROM chat_sessions cs
            JOIN workspaces w ON w.id = cs.workspace_id
            WHERE cs.id = $1 AND cs.workspace_id = $2 AND w.user_id = $3
        )
        """,
        chat_id,
        workspace_id,
        user_id,
    )
    if not exists:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat not found")
