# rapid-inbox-ingestd

`rapid-inbox-ingestd` is the C++ SMTP ingest process for Rapid Inbox.

The ingest process accepts SMTP mail, queues it in memory, and batch-writes raw
mail, recovery manifests, parsed text/html bodies, attachments, verification
codes, and SQLite message/delivery rows. Python remains the HTTP/admin service
and compatibility parser for old pending rows.

## Build

```bash
cmake -S cpp/ingestd -B cpp/ingestd/build
cmake --build cpp/ingestd/build
ctest --test-dir cpp/ingestd/build --output-on-failure
```

## Run

```bash
SMTP_HOST=127.0.0.1 SMTP_PORT=2525 \
  cpp/ingestd/build/rapid-inbox-ingestd --base-dir .
```

## Durability Semantics

`250 queued` means the message is in the ingestd process memory queue. A normal
SIGTERM/SIGINT stops accepting new connections and drains returned-250 mail to
storage and SQLite before exit. A crash, kill -9, machine reboot, or power loss
can lose messages that have not yet been written.
