from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import chats, documents, stream, usage, workspaces
from app.core.config import get_settings
from app.db.session import connect_pool


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def startup() -> None:
        app.state.db_pool = await connect_pool(settings.database_url)

    @app.on_event("shutdown")
    async def shutdown() -> None:
        if app.state.db_pool is not None:
            await app.state.db_pool.close()

    @app.get("/health")
    async def health():
        return {"ok": True}

    app.include_router(workspaces.router, prefix=settings.api_prefix)
    app.include_router(chats.router, prefix=settings.api_prefix)
    app.include_router(stream.router, prefix=settings.api_prefix)
    app.include_router(documents.router, prefix=settings.api_prefix)
    app.include_router(usage.router, prefix=settings.api_prefix)
    return app


app = create_app()
