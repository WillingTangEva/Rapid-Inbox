# Rapid Inbox Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runnable MVP that can accept inbound SMTP mail for configured domains, persist raw messages plus placeholder metadata, parse bodies asynchronously, and expose public mailbox/message pages.

**Architecture:** Use a FastAPI app for HTTP, `aiosmtpd` for SMTP ingress, SQLite for metadata, and filesystem storage for raw and parsed artifacts. Keep writes serialized behind a single async DB writer, load domain rules into memory for fast RCPT checks, and parse MIME content off the SMTP hot path with a background ingest queue.

**Tech Stack:** Python 3.12, FastAPI, Jinja2, aiosmtpd, SQLite (`sqlite3`), pytest, httpx

---

### Task 1: Project Skeleton And Configuration

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `app/__init__.py`
- Create: `app/config.py`
- Create: `app/main.py`
- Create: `app/templates/public/mailbox.html`
- Create: `app/templates/public/message.html`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
from app.config import Settings


def test_settings_derive_storage_paths(tmp_path):
    settings = Settings(storage_root=tmp_path, database_path=tmp_path / "app.db")

    assert settings.raw_dir == tmp_path / "raw"
    assert settings.text_dir == tmp_path / "text"
    assert settings.html_dir == tmp_path / "html"
    assert settings.attachments_dir == tmp_path / "attachments"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_config.py::test_settings_derive_storage_paths -v`
Expected: FAIL with `ModuleNotFoundError` or missing `Settings`

- [ ] **Step 3: Write minimal implementation**

```python
@dataclass(slots=True)
class Settings:
    storage_root: Path
    database_path: Path

    @property
    def raw_dir(self) -> Path:
        return self.storage_root / "raw"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_config.py::test_settings_derive_storage_paths -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .gitignore app tests
git commit -m "feat: bootstrap rapid inbox application skeleton"
```

### Task 2: Domain Matching And Mailbox Normalization

**Files:**
- Create: `app/smtp/matcher.py`
- Create: `app/services/domains.py`
- Test: `tests/test_domain_matching.py`

- [ ] **Step 1: Write the failing test**

```python
from app.smtp.matcher import DomainRule, DomainMatcher


def test_domain_matcher_prefers_longest_suffix_and_subdomain_flag():
    matcher = DomainMatcher(
        [
            DomainRule(domain_id=1, root_domain_ascii="adb.com", accept_exact=True, accept_subdomains=True),
            DomainRule(domain_id=2, root_domain_ascii="x.adb.com", accept_exact=True, accept_subdomains=False),
        ]
    )

    match = matcher.match_address("Foo+tag@b.x.adb.com", plus_mode="strip", case_sensitive=False)

    assert match is None
    assert matcher.match_address("Foo+tag@x.adb.com", plus_mode="strip", case_sensitive=False).address_canonical == "foo@x.adb.com"
    assert matcher.match_address("Foo@z.adb.com", plus_mode="keep", case_sensitive=False).domain_id == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_domain_matching.py::test_domain_matcher_prefers_longest_suffix_and_subdomain_flag -v`
Expected: FAIL with missing matcher implementation

- [ ] **Step 3: Write minimal implementation**

```python
@dataclass(frozen=True, slots=True)
class DomainRule:
    domain_id: int
    root_domain_ascii: str
    accept_exact: bool
    accept_subdomains: bool


class DomainMatcher:
    def match_address(self, address: str, plus_mode: str, case_sensitive: bool) -> MatchResult | None:
        ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_domain_matching.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/smtp/matcher.py app/services/domains.py tests/test_domain_matching.py
git commit -m "feat: implement domain matching and mailbox normalization"
```

### Task 3: SQLite, Storage, And Ingest Pipeline

**Files:**
- Create: `app/db/connection.py`
- Create: `app/db/writer.py`
- Create: `app/ingest/storage.py`
- Create: `app/ingest/parser.py`
- Create: `app/ingest/queue.py`
- Create: `app/ingest/recovery.py`
- Test: `tests/test_ingest_pipeline.py`

- [ ] **Step 1: Write the failing test**

```python
def test_placeholder_insert_and_parse_roundtrip(app_runtime, sample_email_bytes):
    result = app_runtime.accept_message(
        rcpt_tos=["foo@adb.com"],
        envelope_from="sender@example.com",
        content=sample_email_bytes,
    )

    app_runtime.wait_for_parser()

    mailbox = app_runtime.fetch_mailbox("foo@adb.com")
    detail = app_runtime.fetch_delivery("foo@adb.com", mailbox["deliveries"][0]["delivery_id"])

    assert result.startswith("250 queued as ")
    assert mailbox["items"][0]["parse_status"] == "parsed"
    assert detail["subject"] == "Hello Rapid Inbox"
    assert detail["text_body"].startswith("Hello from tests")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_ingest_pipeline.py::test_placeholder_insert_and_parse_roundtrip -v`
Expected: FAIL because runtime/storage/DB pipeline does not exist

- [ ] **Step 3: Write minimal implementation**

```python
def store_raw_message(...):
    with open(part_path, "wb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(part_path, final_path)


class ParseWorker:
    async def enqueue(self, task: ParseTask) -> None:
        await self._queue.put(task)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_ingest_pipeline.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/db app/ingest tests/test_ingest_pipeline.py
git commit -m "feat: implement sqlite writer and ingest pipeline"
```

### Task 4: Public Web Views And Public JSON API

**Files:**
- Create: `app/http/public_views.py`
- Create: `app/http/public_api.py`
- Create: `app/schemas.py`
- Test: `tests/test_public_routes.py`

- [ ] **Step 1: Write the failing test**

```python
def test_mailbox_page_and_public_api_show_received_message(client, seeded_message):
    page = client.get("/mail/foo@adb.com")
    detail = client.get(f"/mail/foo@adb.com/{seeded_message.delivery_id}")
    api = client.get(
        "/api/v1/public/mailboxes/foo@adb.com/messages",
        headers={"X-API-Key": seeded_message.public_api_key},
    )

    assert page.status_code == 200
    assert "Hello Rapid Inbox" in page.text
    assert detail.status_code == 200
    assert api.status_code == 200
    assert api.json()["items"][0]["delivery_id"] == seeded_message.delivery_id
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_public_routes.py::test_mailbox_page_and_public_api_show_received_message -v`
Expected: FAIL because routes do not exist

- [ ] **Step 3: Write minimal implementation**

```python
router = APIRouter()


@router.get("/mail/{mailbox_address}", response_class=HTMLResponse)
def mailbox_page(...):
    ...


@router.get("/api/v1/public/mailboxes/{mailbox_address}/messages")
def list_mailbox_messages(...):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_public_routes.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/http app/schemas.py tests/test_public_routes.py
git commit -m "feat: add public mailbox pages and json api"
```

### Task 5: SMTP Handler, Live Session State, And Minimal Admin Domain API

**Files:**
- Create: `app/http/admin_api.py`
- Create: `app/smtp/live_state.py`
- Create: `app/smtp/handler.py`
- Create: `app/smtp/server.py`
- Test: `tests/test_smtp_handler.py`

- [ ] **Step 1: Write the failing test**

```python
async def test_smtp_handler_accepts_allowed_domain_and_rejects_unknown(runtime):
    allowed = await runtime.smtp_handler.handle_RCPT(
        runtime.server,
        runtime.session,
        runtime.envelope,
        "foo@adb.com",
        [],
    )
    rejected = await runtime.smtp_handler.handle_RCPT(
        runtime.server,
        runtime.session,
        runtime.envelope,
        "foo@example.com",
        [],
    )

    assert allowed == "250 OK"
    assert rejected.startswith("550")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_smtp_handler.py::test_smtp_handler_accepts_allowed_domain_and_rejects_unknown -v`
Expected: FAIL because SMTP handler/admin API are missing

- [ ] **Step 3: Write minimal implementation**

```python
class RapidInboxHandler:
    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        if not self._domains.is_allowed(address):
            return "550 domain not allowed"
        envelope.rcpt_tos.append(address)
        return "250 OK"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_smtp_handler.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/http/admin_api.py app/smtp tests/test_smtp_handler.py
git commit -m "feat: add smtp ingress and minimal admin domain api"
```

## Self-Review

- Spec coverage: This plan implements Phase 1 fully and adds the minimum admin domain-management surface needed to make the SMTP path usable without manual SQL edits.
- Placeholder scan: No `TODO`/`TBD` placeholders remain; every task names concrete files, tests, and commands.
- Type consistency: Shared concepts stay consistent across tasks: `Settings`, `DomainRule`, `DomainMatcher`, `ParseTask`, `delivery_id`, `mailbox_address`.
