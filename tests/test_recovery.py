from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.config import Settings
from app.runtime import RapidInboxRuntime
from conftest import connect_database


@pytest.mark.asyncio
async def test_recovery_scanner_rebuilds_missing_message_and_delivery(tmp_path, sample_email_bytes: bytes) -> None:
    settings = Settings(
        storage_root=tmp_path / "storage",
        database_path=tmp_path / "storage" / "app.db",
    )
    runtime = RapidInboxRuntime(settings)

    await runtime.start()
    try:
        await runtime.create_domain("adb.com")
        await runtime.ensure_smtp_session(
            "smtp_recover_1",
            SimpleNamespace(peer=("127.0.0.1", 2525), host_name="localhost", ssl=None),
        )
        await runtime.accept_message(
            rcpt_tos=["foo@adb.com"],
            envelope_from="sender@example.com",
            content=sample_email_bytes,
            smtp_session_id="smtp_recover_1",
        )
        await runtime.drain_parser_queue()
    finally:
        await runtime.stop()

    with connect_database(settings.database_path) as connection:
        connection.execute("DELETE FROM message_deliveries")
        connection.execute("DELETE FROM messages")
        connection.commit()

    repaired = RapidInboxRuntime(settings)
    await repaired.start()
    try:
        mailbox = await repaired.get_mailbox_view("foo@adb.com")
        await repaired.drain_parser_queue()
        assert mailbox["message_count"] == 1
        assert mailbox["items"][0]["parse_status"] in {"pending", "parsed"}
    finally:
        await repaired.stop()
