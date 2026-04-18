from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.config import Settings
from app.runtime import RapidInboxRuntime


@pytest.mark.asyncio
async def test_accept_message_writes_manifest_for_recovery(tmp_path, sample_email_bytes: bytes) -> None:
    settings = Settings(
        storage_root=tmp_path / "storage",
        database_path=tmp_path / "storage" / "app.db",
    )
    runtime = RapidInboxRuntime(settings)

    await runtime.start()
    try:
        await runtime.create_domain("adb.com")
        await runtime.ensure_smtp_session(
            "smtp_test_1",
            SimpleNamespace(peer=("127.0.0.1", 2525), host_name="localhost", ssl=None),
        )
        response = await runtime.accept_message(
            rcpt_tos=["foo@adb.com", "bar@adb.com"],
            envelope_from="sender@example.com",
            content=sample_email_bytes,
            smtp_session_id="smtp_test_1",
        )
        await runtime.drain_parser_queue()

        manifest_paths = list(settings.manifests_dir.rglob("*.json"))
        assert response.startswith("250 queued as ")
        assert len(manifest_paths) == 1

        manifest = json.loads(manifest_paths[0].read_text(encoding="utf-8"))
        assert manifest["smtp_session_id"] == "smtp_test_1"
        assert manifest["envelope_from"] == "sender@example.com"
        assert manifest["rcpt_tos"] == ["foo@adb.com", "bar@adb.com"]
        assert manifest["raw_path"].endswith(".eml")
    finally:
        await runtime.stop()


@pytest.mark.asyncio
async def test_placeholder_insert_and_parse_roundtrip(tmp_path, sample_email_bytes: bytes) -> None:
    settings = Settings(
        storage_root=tmp_path / "storage",
        database_path=tmp_path / "storage" / "app.db",
    )
    runtime = RapidInboxRuntime(settings)

    await runtime.start()
    try:
        await runtime.create_domain("adb.com")

        result = await runtime.accept_message(
            rcpt_tos=["foo@adb.com"],
            envelope_from="sender@example.com",
            content=sample_email_bytes,
        )
        await runtime.drain_parser_queue()

        mailbox = await runtime.get_mailbox_view("foo@adb.com")
        detail = await runtime.get_delivery_detail("foo@adb.com", mailbox["items"][0]["delivery_id"])

        assert result.startswith("250 queued as ")
        assert mailbox["items"][0]["parse_status"] == "parsed"
        assert mailbox["message_count"] == 1
        assert detail["subject"] == "Hello Rapid Inbox"
        assert detail["text_body"].startswith("Hello from tests.")
        assert detail["html_body"].startswith("<html>")
        assert detail["from_addr"] == "sender@example.com"
        assert any(settings.raw_dir.rglob("*.eml"))
    finally:
        await runtime.stop()
