from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_admin_login_and_dashboard_page_flow(app_client, runtime) -> None:
    response = await app_client.post(
        "/admin/login",
        data={"username": "admin", "password": runtime.settings.bootstrap_admin_password},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Rapid Inbox Admin" in response.text
    assert "Domains" in response.text
