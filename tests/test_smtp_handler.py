from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.config import default_settings
from app.runtime import RapidInboxRuntime
from app import smtp_runner
from app.smtp.handler import RapidInboxHandler


@pytest.mark.asyncio
async def test_smtp_handler_accepts_allowed_domain_and_rejects_unknown(tmp_path, sample_email_bytes: bytes) -> None:
    settings = default_settings(tmp_path)
    runtime = RapidInboxRuntime(settings)
    handler = RapidInboxHandler(runtime)

    await runtime.start()
    try:
        await runtime.create_domain("adb.com")

        session = SimpleNamespace(peer=("127.0.0.1", 2525), host_name="mx1.test", ssl=None)
        envelope = SimpleNamespace(rcpt_tos=[], mail_from="sender@example.com", content=sample_email_bytes)

        allowed = await handler.handle_RCPT(None, session, envelope, "foo@adb.com", [])
        rejected = await handler.handle_RCPT(None, session, envelope, "foo@example.com", [])
        queued = await handler.handle_DATA(None, session, envelope)
        await runtime.drain_parser_queue()
        mailbox = await runtime.get_mailbox_view("foo@adb.com")

        assert allowed == "250 OK"
        assert rejected.startswith("550")
        assert queued.startswith("250 queued as ")
        assert mailbox["items"][0]["parse_status"] == "parsed"
    finally:
        await runtime.stop()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("failure_stage", "expected_server_stop_calls"),
    [
        ("init", 0),
        ("start", 1),
    ],
)
async def test_smtp_runner_stops_runtime_on_startup_failure(
    monkeypatch,
    failure_stage: str,
    expected_server_stop_calls: int,
) -> None:
    runtime_holder: dict[str, object] = {}
    server_holder: dict[str, object] = {}

    class FakeRuntime:
        def __init__(self, settings) -> None:
            self.settings = settings
            self.start_calls = 0
            self.stop_calls = 0
            runtime_holder["runtime"] = self

        async def start(self) -> None:
            self.start_calls += 1

        async def stop(self) -> None:
            self.stop_calls += 1

    class FakeServer:
        def __init__(self, runtime) -> None:
            self.runtime = runtime
            self.stop_calls = 0
            server_holder["server"] = self
            if failure_stage == "init":
                raise RuntimeError("smtp bootstrap failed")

        def start(self) -> None:
            if failure_stage == "start":
                raise RuntimeError("smtp bootstrap failed")

        def stop(self) -> None:
            self.stop_calls += 1

    monkeypatch.setattr(smtp_runner, "default_settings", lambda base_dir: object())
    monkeypatch.setattr(smtp_runner, "RapidInboxRuntime", FakeRuntime)
    monkeypatch.setattr(smtp_runner, "SMTPServer", FakeServer)

    with pytest.raises(RuntimeError, match="smtp bootstrap failed"):
        await smtp_runner.main_async()

    runtime = runtime_holder["runtime"]
    assert isinstance(runtime, FakeRuntime)
    assert runtime.start_calls == 1
    assert runtime.stop_calls == 1

    server = server_holder["server"]
    assert isinstance(server, FakeServer)
    assert server.stop_calls == expected_server_stop_calls
