from __future__ import annotations

from aiosmtpd.controller import Controller

from app.smtp.handler import RapidInboxHandler


class SMTPServer:
    def __init__(self, runtime) -> None:
        self._controller = Controller(
            RapidInboxHandler(runtime),
            hostname=runtime.settings.smtp_host,
            port=runtime.settings.smtp_port,
            timeout=runtime.settings.smtp_idle_timeout_seconds,
            data_size_limit=int(runtime.settings.max_message_size_bytes),
        )

    def start(self) -> None:
        self._controller.start()

    def stop(self) -> None:
        self._controller.stop()
