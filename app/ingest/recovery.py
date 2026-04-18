from __future__ import annotations

import json
from typing import TYPE_CHECKING

from app.ingest.queue import ParseTask

if TYPE_CHECKING:
    from app.runtime import RapidInboxRuntime


class RecoveryScanner:
    def __init__(self, runtime: "RapidInboxRuntime") -> None:
        self.runtime = runtime

    async def run(self) -> None:
        self.runtime.storage.cleanup_stale_parts()
        policy_manifests: list[dict[str, object]] = []
        legacy_manifests: list[dict[str, object]] = []
        for manifest_path in sorted(self.runtime.settings.manifests_dir.rglob("*.json")):
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                self.runtime.validate_recovery_manifest(manifest)
            except (json.JSONDecodeError, ValueError):
                # Malformed manifests are skipped so one bad file cannot block startup recovery.
                continue
            if self._has_domain_policy(manifest):
                policy_manifests.append(manifest)
            else:
                legacy_manifests.append(manifest)

        for manifest in policy_manifests + legacy_manifests:
            try:
                await self.runtime.recover_from_manifest(manifest)
            except ValueError:
                # Legacy manifests can remain unrecoverable if the matching domain never reappears.
                continue

        for message_id in await self.runtime.find_messages_for_reparse():
            await self.runtime.parse_queue.enqueue(ParseTask(message_id=message_id))

    def _has_domain_policy(self, manifest: dict[str, object]) -> bool:
        recipients = manifest.get("recipients")
        if not isinstance(recipients, list) or not recipients:
            return False
        first_recipient = recipients[0]
        if not isinstance(first_recipient, dict):
            return False
        return first_recipient.get("domain_policy") is not None
