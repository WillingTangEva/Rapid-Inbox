from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI

from app.config import Settings
from app.db.connection import connect_database
from app.main import create_app
from app.runtime import RapidInboxRuntime


@dataclass(slots=True)
class SeededMessage:
    message_id: str
    delivery_id: str
    public_api_key: str


@pytest.fixture
def sample_email_bytes() -> bytes:
    return (
        b"From: Sender <sender@example.com>\r\n"
        b"To: Foo <foo@adb.com>\r\n"
        b"Subject: Hello Rapid Inbox\r\n"
        b"Message-ID: <hello@example.com>\r\n"
        b"Date: Sat, 18 Apr 2026 20:00:00 +0000\r\n"
        b"MIME-Version: 1.0\r\n"
        b"Content-Type: multipart/alternative; boundary=boundary42\r\n"
        b"\r\n"
        b"--boundary42\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n"
        b"\r\n"
        b"Hello from tests.\r\n"
        b"\r\n"
        b"--boundary42\r\n"
        b"Content-Type: text/html; charset=utf-8\r\n"
        b"\r\n"
        b"<html><body><p>Hello from tests.</p></body></html>\r\n"
        b"\r\n"
        b"--boundary42--\r\n"
    )


@pytest_asyncio.fixture
async def app_fixture(tmp_path) -> AsyncIterator[tuple[FastAPI, RapidInboxRuntime]]:
    settings = Settings(
        storage_root=tmp_path / "storage",
        database_path=tmp_path / "storage" / "app.db",
    )
    app = create_app(settings=settings)
    async with app.router.lifespan_context(app):
        yield app, app.state.runtime


@pytest_asyncio.fixture
async def runtime(app_fixture) -> RapidInboxRuntime:
    _, runtime = app_fixture
    return runtime


@pytest_asyncio.fixture
async def app_client(app_fixture) -> AsyncIterator[httpx.AsyncClient]:
    app, _ = app_fixture
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


__all__ = [
    "SeededMessage",
    "app_client",
    "app_fixture",
    "connect_database",
    "runtime",
    "sample_email_bytes",
]
