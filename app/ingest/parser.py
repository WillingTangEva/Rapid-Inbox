from __future__ import annotations

import json
import mimetypes
import re
import uuid
from dataclasses import dataclass
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import parseaddr

from app.ingest.storage import FileStorage


def build_preview(text_body: str | None, html_body: str | None) -> str | None:
    source = text_body or re.sub(r"<[^>]+>", " ", html_body or "")
    cleaned = re.sub(r"\s+", " ", source).strip()
    return cleaned[:200] or None


@dataclass(frozen=True, slots=True)
class ParsedAttachment:
    attachment_id: str
    part_index: int
    filename: str | None
    safe_filename: str
    content_type: str
    content_disposition: str | None
    content_id: str | None
    storage_path: str
    sha256: str | None
    size_bytes: int
    is_inline: bool


@dataclass(frozen=True, slots=True)
class ParsedMessage:
    message_id_header: str | None
    subject: str | None
    from_name: str | None
    from_addr: str | None
    reply_to: str | None
    date_header: str | None
    has_text: bool
    has_html: bool
    has_attachments: bool
    attachment_count: int
    text_preview: str | None
    text_body_path: str | None
    html_body_path: str | None
    headers_json: str
    attachments: list[ParsedAttachment]


class MessageParser:
    def __init__(self, storage: FileStorage) -> None:
        self._storage = storage

    def parse_message(self, message_id: str, raw_content: bytes, received_at: str) -> ParsedMessage:
        parsed = BytesParser(policy=policy.default).parsebytes(raw_content)
        text_body, html_body, attachments = self._extract_parts(message_id, parsed)
        text_path = self._storage.write_text_body(message_id, received_at, text_body) if text_body else None
        html_path = self._storage.write_html_body(message_id, received_at, html_body) if html_body else None
        from_name, from_addr = parseaddr(parsed.get("From", ""))

        return ParsedMessage(
            message_id_header=parsed.get("Message-ID"),
            subject=parsed.get("Subject"),
            from_name=from_name or None,
            from_addr=from_addr or None,
            reply_to=parsed.get("Reply-To"),
            date_header=parsed.get("Date"),
            has_text=text_body is not None,
            has_html=html_body is not None,
            has_attachments=bool(attachments),
            attachment_count=len(attachments),
            text_preview=build_preview(text_body, html_body),
            text_body_path=text_path,
            html_body_path=html_path,
            headers_json=json.dumps(list(parsed.items()), ensure_ascii=False),
            attachments=attachments,
        )

    def _extract_parts(self, message_id: str, parsed: EmailMessage) -> tuple[str | None, str | None, list[ParsedAttachment]]:
        text_body: str | None = None
        html_body: str | None = None
        attachments: list[ParsedAttachment] = []

        for index, part in enumerate(parsed.walk()):
            if part.is_multipart():
                continue

            content_disposition = part.get_content_disposition()
            content_type = part.get_content_type()

            if content_disposition != "attachment" and content_type == "text/plain" and text_body is None:
                text_body = part.get_content()
                continue

            if content_disposition != "attachment" and content_type == "text/html" and html_body is None:
                html_body = part.get_content()
                continue

            filename = part.get_filename()
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            content_id = part.get("Content-ID")
            if not filename:
                if content_disposition not in {"attachment", "inline"} and content_id is None:
                    continue
                filename = self._synthesized_attachment_filename(index, content_type, content_id)

            attachment_id = f"att_{uuid.uuid4().hex}"
            storage_path, safe_name = self._storage.write_attachment(message_id, attachment_id, filename, payload)
            attachments.append(
                ParsedAttachment(
                    attachment_id=attachment_id,
                    part_index=index,
                    filename=filename,
                    safe_filename=safe_name,
                    content_type=content_type,
                    content_disposition=content_disposition,
                    content_id=content_id,
                    storage_path=storage_path,
                    sha256=None,
                    size_bytes=len(payload),
                    is_inline=content_disposition == "inline",
                )
            )

        return text_body, html_body, attachments

    def _synthesized_attachment_filename(self, part_index: int, content_type: str, content_id: str | None) -> str:
        base_name = self._normalize_synthesized_name(content_id) or f"inline-{part_index}"
        extension = mimetypes.guess_extension(self._normalize_content_type(content_type)) or ""
        return f"{base_name}{extension}"

    def _normalize_synthesized_name(self, value: str | None) -> str:
        if value is None:
            return ""
        return re.sub(r"[^A-Za-z0-9._-]+", "-", str(value).strip().strip("<>")).strip("._-")

    def _normalize_content_type(self, value: str | None) -> str:
        return str(value or "").split(";", 1)[0].strip().lower()
