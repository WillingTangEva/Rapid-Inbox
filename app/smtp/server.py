from __future__ import annotations

from aiosmtpd.controller import Controller

from app.smtp.handler import RapidInboxHandler


class SMTPServer:
    def __init__(self, runtime) -> None:
        self._controller = Controller(
            RapidInboxHandler(runtime),
            hostname=runtime.settings.smtp_host,
            port=runtime.settings.smtp_port,
        )

    def start(self) -> None:
        self._controller.start()

    def stop(self) -> None:
        self._controller.stop()
