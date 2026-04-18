from __future__ import annotations

import httpx
import pytest

from app.config import Settings
from app.main import create_app


@pytest.mark.asyncio
async def test_admin_domain_api_creates_and_lists_domains(tmp_path) -> None:
    settings = Settings(
        storage_root=tmp_path / "storage",
        database_path=tmp_path / "storage" / "app.db",
        admin_token="admin-secret",
    )
    app = create_app(settings=settings)

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            created = await client.post(
                "/api/v1/admin/domains",
                headers={"X-API-Key": settings.admin_token},
                json={"root_domain": "adb.com", "accept_subdomains": True},
            )
            listed = await client.get(
                "/api/v1/admin/domains",
                headers={"X-API-Key": settings.admin_token},
            )

        assert created.status_code == 201
        assert created.json()["root_domain_ascii"] == "adb.com"
        assert listed.status_code == 200
        assert listed.json()["items"][0]["root_domain_ascii"] == "adb.com"


@pytest.mark.asyncio
async def test_admin_api_supports_message_reparse_and_settings_update(admin_client, runtime, seeded_message) -> None:
    reparse = await admin_client.post(f"/api/v1/admin/messages/{seeded_message.message_id}/reparse")
    settings_response = await admin_client.patch(
        "/api/v1/admin/settings",
        json={"max_recipients_per_message": "25"},
    )
    audit = await admin_client.get("/api/v1/admin/audit-logs")

    assert reparse.status_code == 202
    assert settings_response.status_code == 200
    assert audit.status_code == 200
    assert any(item["action"] == "settings.update" for item in audit.json()["items"])
