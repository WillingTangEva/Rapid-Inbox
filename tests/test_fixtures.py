from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_shared_runtime_and_app_client_fixtures(app_client, runtime) -> None:
    response = await app_client.get("/does-not-exist")

    assert response.status_code == 404
    assert runtime.settings.storage_root.exists()
