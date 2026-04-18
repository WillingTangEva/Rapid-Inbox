from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from app.db.connection import connect_database
from app.db.writer import DatabaseWriter
from app.ingest.storage import utc_now
from app.smtp.matcher import DomainMatch, DomainMatcher, DomainRule, normalize_domain


class DomainService:
    def __init__(self, database_path: Path, writer: DatabaseWriter) -> None:
        self._database_path = database_path
        self._writer = writer
        self._matcher = DomainMatcher([])

    def reload(self) -> None:
        with connect_database(self._database_path) as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    root_domain_ascii,
                    accept_exact,
                    accept_subdomains,
                    plus_addressing_mode,
                    local_part_case_sensitive
                FROM domains
                WHERE is_active = 1
                """
            ).fetchall()
        self._matcher = DomainMatcher(
            [
                DomainRule(
                    domain_id=row["id"],
                    root_domain_ascii=row["root_domain_ascii"],
                    accept_exact=bool(row["accept_exact"]),
                    accept_subdomains=bool(row["accept_subdomains"]),
                    plus_addressing_mode=row["plus_addressing_mode"],
                    local_part_case_sensitive=bool(row["local_part_case_sensitive"]),
                )
                for row in rows
            ]
        )

    async def create_domain(
        self,
        root_domain: str,
        *,
        accept_exact: bool = True,
        accept_subdomains: bool = True,
        public_web_enabled: bool = True,
        public_api_enabled: bool = True,
        plus_addressing_mode: str = "keep",
        local_part_case_sensitive: bool = False,
        is_active: bool = True,
        max_message_size_bytes: int = 52_428_800,
    ) -> dict[str, Any]:
        now = utc_now()
        root_domain_ascii = self._coerce_root_domain(root_domain)
        accept_exact = self._coerce_bool("accept_exact", accept_exact)
        accept_subdomains = self._coerce_bool("accept_subdomains", accept_subdomains)
        public_web_enabled = self._coerce_bool("public_web_enabled", public_web_enabled)
        public_api_enabled = self._coerce_bool("public_api_enabled", public_api_enabled)
        local_part_case_sensitive = self._coerce_bool("local_part_case_sensitive", local_part_case_sensitive)
        is_active = self._coerce_bool("is_active", is_active)
        max_message_size_bytes = self._coerce_positive_int("max_message_size_bytes", max_message_size_bytes)
        plus_addressing_mode = self._coerce_plus_addressing_mode(plus_addressing_mode)

        def operation(connection: sqlite3.Connection) -> int:
            cursor = connection.execute(
                """
                INSERT INTO domains (
                    root_domain_ascii,
                    root_domain_unicode,
                    accept_exact,
                    accept_subdomains,
                    public_web_enabled,
                    public_api_enabled,
                    is_active,
                    plus_addressing_mode,
                    local_part_case_sensitive,
                    max_message_size_bytes,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    root_domain_ascii,
                    root_domain,
                    int(accept_exact),
                    int(accept_subdomains),
                    int(public_web_enabled),
                    int(public_api_enabled),
                    int(is_active),
                    plus_addressing_mode,
                    int(local_part_case_sensitive),
                    max_message_size_bytes,
                    now,
                    now,
                ),
            )
            return int(cursor.lastrowid)

        domain_id = await self._writer.execute(operation)
        self.reload()
        return {
            "id": domain_id,
            "root_domain_ascii": root_domain_ascii,
            "accept_exact": accept_exact,
            "accept_subdomains": accept_subdomains,
            "public_web_enabled": public_web_enabled,
            "public_api_enabled": public_api_enabled,
        }

    def list_domains(self) -> list[dict[str, Any]]:
        with connect_database(self._database_path) as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    root_domain_ascii,
                    accept_exact,
                    accept_subdomains,
                    public_web_enabled,
                    public_api_enabled,
                    is_active,
                    created_at,
                    updated_at
                FROM domains
                ORDER BY root_domain_ascii ASC
                """
            ).fetchall()
        return [self._normalize_domain_row(row) for row in rows]

    def get_domain(self, domain_id: int) -> dict[str, Any]:
        with connect_database(self._database_path) as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    root_domain_ascii,
                    root_domain_unicode,
                    accept_exact,
                    accept_subdomains,
                    public_web_enabled,
                    public_api_enabled,
                    is_active,
                    is_hidden,
                    local_part_case_sensitive,
                    plus_addressing_mode,
                    max_message_size_bytes,
                    retention_days,
                    dns_status,
                    dns_last_checked_at,
                    dns_details_json,
                    notes,
                    created_at,
                    updated_at
                FROM domains
                WHERE id = ?
                """,
                (domain_id,),
            ).fetchone()
        if row is None:
            raise LookupError("domain not found")
        return self._normalize_domain_row(row)

    def match_address(self, address: str) -> DomainMatch | None:
        return self._matcher.match_address(address)

    def _coerce_root_domain(self, value: Any) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("invalid root_domain")
        try:
            return normalize_domain(value)
        except Exception as exc:  # noqa: BLE001
            raise ValueError("invalid root_domain") from exc

    def _coerce_bool(self, field_name: str, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int) and not isinstance(value, bool) and value in (0, 1):
            return bool(value)
        raise ValueError(f"invalid {field_name}")

    def _coerce_plus_addressing_mode(self, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("invalid plus_addressing_mode")
        if value not in {"keep", "strip"}:
            raise ValueError("invalid plus_addressing_mode")
        return value

    def _coerce_positive_int(self, field_name: str, value: Any) -> int:
        if isinstance(value, bool):
            raise ValueError(f"invalid {field_name}")
        if isinstance(value, float) and not value.is_integer():
            raise ValueError(f"invalid {field_name}")
        try:
            normalized = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid {field_name}") from exc
        if normalized < 1:
            raise ValueError(f"invalid {field_name}")
        if isinstance(value, float) and normalized != value:
            raise ValueError(f"invalid {field_name}")
        return normalized

    def _normalize_domain_row(self, row: sqlite3.Row) -> dict[str, Any]:
        payload = dict(row)
        for key in (
            "accept_exact",
            "accept_subdomains",
            "public_web_enabled",
            "public_api_enabled",
            "is_active",
            "is_hidden",
            "local_part_case_sensitive",
        ):
            if key in payload:
                payload[key] = bool(payload[key])
        return payload
