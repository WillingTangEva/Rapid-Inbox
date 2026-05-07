from __future__ import annotations

import asyncio
import logging

from aiosmtpd.controller import Controller
from aiosmtpd.smtp import SMTP

from app.smtp.handler import RapidInboxHandler


logger = logging.getLogger(__name__)


def _log_disconnect_task_exception(task) -> None:
    try:
        task.result()
    except asyncio.CancelledError:
        return
    except Exception:
        logger.exception("SMTP disconnect cleanup failed")


class RapidInboxSMTP(SMTP):
    def connection_lost(self, error) -> None:
        session = getattr(self, "session", None)
        envelope = getattr(self, "envelope", None)
        handler = getattr(self, "event_handler", None)
        session_id = getattr(session, "rapid_inbox_session_id", None)
        super().connection_lost(error)
        if session_id is None or not hasattr(handler, "handle_DISCONNECT"):
            return
        try:
            task = self.loop.create_task(handler.handle_DISCONNECT(self, session, envelope, error))
            task.add_done_callback(_log_disconnect_task_exception)
        except RuntimeError:
            return


class RapidInboxController(Controller):
    def factory(self):
        return RapidInboxSMTP(self.handler, **self.SMTP_kwargs)


class SMTPServer:
    def __init__(self, runtime) -> None:
        self._controller = RapidInboxController(
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
