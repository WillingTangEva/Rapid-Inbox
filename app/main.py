from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.templating import Jinja2Templates

from app.config import Settings, default_settings
from app.http.admin_views import router as admin_views_router
from app.http.admin_api import router as admin_api_router
from app.http.public_api import router as public_api_router
from app.http.public_views import router as public_views_router
from app.runtime import RapidInboxRuntime
from app.smtp.server import SMTPServer


def create_app(*, settings: Settings | None = None, embed_smtp: bool = False) -> FastAPI:
    resolved_settings = settings or default_settings(Path.cwd())
    runtime = RapidInboxRuntime(resolved_settings)
    templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = resolved_settings
        app.state.runtime = runtime
        app.state.templates = templates
        smtp_server: SMTPServer | None = None
        try:
            await runtime.start()
            if embed_smtp:
                smtp_server = SMTPServer(runtime)
                smtp_server.start()
            yield
        finally:
            try:
                if smtp_server is not None:
                    smtp_server.stop()
            finally:
                await runtime.stop()

    app = FastAPI(title="Rapid Inbox", lifespan=lifespan)
    app.include_router(public_views_router)
    app.include_router(public_api_router)
    app.include_router(admin_views_router)
    app.include_router(admin_api_router)
    return app


app = create_app()
