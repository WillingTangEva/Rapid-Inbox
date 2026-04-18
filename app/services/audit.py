from __future__ import annotations

import json
import sqlite3
from typing import Any

from app.db.connection import connect_database
from app.ingest.storage import utc_now


class AuditService:
    def __init__(self, runtime: Any) -> None:
        self._runtime = runtime

    async def log(
        self,
        actor_type: str,
        actor_ref: str | None,
        action: str,
        resource_type: str,
        resource_ref: str | None,
        status: str,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
        details: Any | None = None,
    ) -> dict[str, Any]:
        created_at = utc_now()
        details_json = None if details is None else json.dumps(details, ensure_ascii=False)

        def operation(connection: sqlite3.Connection) -> dict[str, Any]:
            cursor = connection.execute(
                """
                INSERT INTO audit_logs (
                    actor_type,
                    actor_ref,
                    action,
                    resource_type,
                    resource_ref,
                    status,
                    ip,
                    user_agent,
                    details_json,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    actor_type,
                    actor_ref,
                    action,
                    resource_type,
                    resource_ref,
                    status,
                    ip,
                    user_agent,
                    details_json,
                    created_at,
                ),
            )
            return {
                "id": int(cursor.lastrowid),
                "actor_type": actor_type,
                "actor_ref": actor_ref,
                "action": action,
                "resource_type": resource_type,
                "resource_ref": resource_ref,
                "status": status,
                "ip": ip,
                "user_agent": user_agent,
                "details": details,
                "created_at": created_at,
            }

        return await self._runtime.writer.execute(operation)

    def list_logs(self, *, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        with connect_database(self._runtime.settings.database_path) as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    actor_type,
                    actor_ref,
                    action,
                    resource_type,
                    resource_ref,
                    status,
                    ip,
                    user_agent,
                    details_json,
                    created_at
                FROM audit_logs
                ORDER BY created_at DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()

        items: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            details_json = item.get("details_json")
            item["details"] = json.loads(details_json) if details_json else None
            items.append(item)
        return {"items": items}


__all__ = ["AuditService"]
