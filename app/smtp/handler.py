from __future__ import annotations

import uuid

from app.ingest.storage import utc_now


class RapidInboxHandler:
    def __init__(self, runtime) -> None:
        self.runtime = runtime

    async def handle_RCPT(self, server, session, envelope, address: str, rcpt_options):
        session_id = self._ensure_session_id(session)
        await self.runtime.ensure_smtp_session(session_id, session, last_rcpt_to=address)
        if self.runtime.domains.match_address(address) is None:
            await self.runtime.live_state.publish(
                {"type": "rcpt_rejected", "session_id": session_id, "rcpt_to": address, "ts": utc_now()}
            )
            return "550 domain not allowed"

        if address not in envelope.rcpt_tos:
            envelope.rcpt_tos.append(address)
        await self.runtime.live_state.publish(
            {"type": "rcpt_accepted", "session_id": session_id, "rcpt_to": address, "ts": utc_now()}
        )
        return "250 OK"

    async def handle_DATA(self, server, session, envelope):
        session_id = self._ensure_session_id(session)
        await self.runtime.ensure_smtp_session(session_id, session)
        if len(envelope.content) > self.runtime.settings.max_message_size_bytes:
            return "552 message too large"
        if not envelope.rcpt_tos:
            return "554 no valid recipients"

        result = await self.runtime.accept_message(
            rcpt_tos=list(envelope.rcpt_tos),
            envelope_from=getattr(envelope, "mail_from", None),
            content=envelope.content,
            smtp_session_id=session_id,
        )
        await self.runtime.live_state.publish({"type": "queued", "session_id": session_id, "ts": utc_now()})
        return result

    def _ensure_session_id(self, session) -> str:
        session_id = getattr(session, "rapid_inbox_session_id", None)
        if session_id is None:
            session_id = f"smtp_{uuid.uuid4().hex}"
            setattr(session, "rapid_inbox_session_id", session_id)
        return session_id
