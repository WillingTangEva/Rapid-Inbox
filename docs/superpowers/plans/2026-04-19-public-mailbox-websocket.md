# Public Mailbox WebSocket Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add WebSocket-driven real-time updates to the public mailbox first page without introducing a new event system.

**Architecture:** Reuse `runtime.live_state` by publishing mailbox-focused delivery events, add a public WebSocket route that filters those events by mailbox, and update the mailbox page client-side with the same card payload shape used by the initial render. Keep first-page pagination stable by inserting at the top and trimming overflow.

**Tech Stack:** Python 3.12, FastAPI, Jinja2, SQLite (`sqlite3`), pytest, httpx, FastAPI TestClient

---

### Task 1: Add Failing WebSocket And Template Tests

**Files:**
- Modify: `tests/test_public_routes.py`
- Test: `tests/test_public_routes.py`

- [ ] **Step 1: Write the failing WebSocket mailbox test**

```python
def test_public_mailbox_websocket_receives_new_delivery_payload():
    ...
    assert payload["type"] == "mailbox_delivery"
    assert payload["item"]["delivery_id"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_public_routes.py::test_public_mailbox_websocket_receives_new_delivery_payload -v`
Expected: FAIL because the WebSocket route does not exist

- [ ] **Step 3: Add failing template assertion**

```python
async def test_public_mailbox_page_includes_websocket_bootstrap(...):
    ...
    assert "/mail/foo@adb.com/ws" in response.text
```

- [ ] **Step 4: Run the focused tests**

Run: `pytest tests/test_public_routes.py -k "websocket or bootstrap" -v`
Expected: FAIL with missing route or missing page script

### Task 2: Publish Mailbox-Focused Live Events

**Files:**
- Modify: `app/runtime.py`
- Test: `tests/test_public_routes.py`

- [ ] **Step 1: Return delivery payloads from accept_message write path**

```python
delivery_events.append(
    {"delivery_id": delivery_id, "rcpt_to": rcpt_to, "mailbox": match.address_canonical}
)
```

- [ ] **Step 2: Publish mailbox_delivery events after insert**

Run: `pytest tests/test_public_routes.py::test_public_mailbox_websocket_receives_new_delivery_payload -v`
Expected: still FAIL because route/service wiring is missing

- [ ] **Step 3: Publish mailbox_delivery_updated events after parse completes**

```python
await self.live_state.publish({"type": "mailbox_delivery_updated", ...})
```

- [ ] **Step 4: Re-run the focused test**

Run: `pytest tests/test_public_routes.py::test_public_mailbox_websocket_receives_new_delivery_payload -v`
Expected: still FAIL until route exists, but emitted events now contain mailbox delivery data

### Task 3: Add Public WebSocket Route And Mailbox Item Loader

**Files:**
- Modify: `app/http/public_views.py`
- Modify: `app/services/messages.py`
- Modify: `app/http/sse.py`
- Test: `tests/test_public_routes.py`

- [ ] **Step 1: Add mailbox item lookup helper**

```python
async def get_public_mailbox_item(...):
    ...
```

- [ ] **Step 2: Add raw live event iterator reusable by SSE and WebSocket**

```python
async def stream_live_events(...):
    yield event
```

- [ ] **Step 3: Add `/mail/{mailbox_address}/ws` route**

```python
@router.websocket("/mail/{mailbox_address}/ws")
async def mailbox_ws(...):
    ...
```

- [ ] **Step 4: Run the focused WebSocket tests**

Run: `pytest tests/test_public_routes.py -k "websocket or bootstrap" -v`
Expected: PASS

### Task 4: Wire The Mailbox Page Client

**Files:**
- Modify: `app/templates/public/mailbox.html`
- Test: `tests/test_public_routes.py`

- [ ] **Step 1: Add stable DOM ids and mailbox page bootstrap data**

```html
<div class="mail-list" id="mail-list" data-mailbox-address="{{ mailbox_address }}">
```

- [ ] **Step 2: Add WebSocket client script for first page only**

```html
<script>
  const socket = new WebSocket(...)
</script>
```

- [ ] **Step 3: Re-run focused public route tests**

Run: `pytest tests/test_public_routes.py -k "websocket or bootstrap or mailbox_page" -v`
Expected: PASS

### Task 5: Run Regression Coverage

**Files:**
- Modify: `tests/test_public_routes.py`

- [ ] **Step 1: Run the full public route suite**

Run: `pytest tests/test_public_routes.py -v`
Expected: PASS

- [ ] **Step 2: Run the full test suite**

Run: `pytest`
Expected: PASS
