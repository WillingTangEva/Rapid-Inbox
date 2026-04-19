# Mailbox Verification Code Shortcut Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add high-confidence verification code extraction and one-click copy actions to the public mailbox list page.

**Architecture:** Extend mailbox list rows with preview/body paths in `app/runtime.py`, enrich them in `app/services/messages.py` with a focused verification-code detector, and render copy controls in `app/templates/public/mailbox.html`. Keep extraction server-side so templates remain simple and recognition rules are testable.

**Tech Stack:** Python 3.12, FastAPI, Jinja2, SQLite (`sqlite3`), pytest, httpx

---

### Task 1: Add Failing Recognition Tests

**Files:**
- Modify: `tests/test_public_routes.py`
- Test: `tests/test_public_routes.py`

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_public_mailbox_page_shows_copy_button_for_openai_verification_code(app_client, runtime) -> None:
    ...
    assert "复制验证码" in response.text
    assert "654321" in response.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest /data/Rapid-Inbox/tests/test_public_routes.py::test_public_mailbox_page_shows_copy_button_for_openai_verification_code -v`
Expected: FAIL because the mailbox page does not render any verification code action

- [ ] **Step 3: Add more failing coverage**

```python
@pytest.mark.asyncio
async def test_public_mailbox_page_ignores_numbers_without_verification_keywords(...):
    ...
    assert "复制验证码" not in response.text


@pytest.mark.asyncio
async def test_public_mailbox_page_ignores_mail_with_multiple_candidate_codes(...):
    ...
    assert "复制验证码" not in response.text
```

- [ ] **Step 4: Run targeted tests**

Run: `pytest /data/Rapid-Inbox/tests/test_public_routes.py -k "verification_code or copy_button" -v`
Expected: FAIL with missing rendering/recognition behavior

### Task 2: Implement Runtime And Service Enrichment

**Files:**
- Modify: `app/runtime.py`
- Modify: `app/services/messages.py`
- Test: `tests/test_public_routes.py`

- [ ] **Step 1: Extend mailbox list rows with body metadata**

```python
SELECT
    d.id AS delivery_id,
    ...
    m.text_preview,
    m.text_body_path,
    m.html_body_path
FROM message_deliveries AS d
JOIN messages AS m ON m.id = d.message_id
```

- [ ] **Step 2: Add failing service-level expectations by re-running tests**

Run: `pytest /data/Rapid-Inbox/tests/test_public_routes.py -k "verification_code or copy_button" -v`
Expected: FAIL because service still returns no `verification_code`

- [ ] **Step 3: Write minimal recognition implementation**

```python
def _extract_verification_code(self, item: dict[str, Any]) -> str | None:
    if item.get("parse_status") != "parsed":
        return None
    ...
    return code_or_none
```

- [ ] **Step 4: Re-run targeted tests**

Run: `pytest /data/Rapid-Inbox/tests/test_public_routes.py -k "verification_code or copy_button" -v`
Expected: PASS once enrichment returns the expected values

### Task 3: Render Copy Controls On Mailbox Page

**Files:**
- Modify: `app/templates/public/mailbox.html`
- Test: `tests/test_public_routes.py`

- [ ] **Step 1: Add list item UI for recognized codes**

```html
{% if item.verification_code %}
  <button class="copy-code-btn" data-code="{{ item.verification_code }}">复制验证码</button>
{% endif %}
```

- [ ] **Step 2: Add clipboard feedback script**

```html
<script>
  document.addEventListener("click", async (event) => {
    ...
  });
</script>
```

- [ ] **Step 3: Run page tests**

Run: `pytest /data/Rapid-Inbox/tests/test_public_routes.py -k "verification_code or copy_button" -v`
Expected: PASS

### Task 4: Verify Broader Public Route Coverage

**Files:**
- Modify: `tests/test_public_routes.py`

- [ ] **Step 1: Run focused public route suite**

Run: `pytest /data/Rapid-Inbox/tests/test_public_routes.py -v`
Expected: PASS

- [ ] **Step 2: Run delivery-format regression coverage**

Run: `pytest /data/Rapid-Inbox/tests/test_smtp_delivery_formats.py -v`
Expected: PASS
