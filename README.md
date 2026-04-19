# Rapid Inbox

Rapid Inbox is a local-first inbound mailbox service. It receives mail over SMTP, stores raw messages and metadata on disk, and exposes public and admin HTTP surfaces for browsing and operations.

## Local Development

1. `python3.12 -m venv .venv`
2. `.venv/bin/pip install -e .[dev]`
3. `.venv/bin/rapid-inbox-http`
4. Open `http://127.0.0.1:8000/admin/login`

The default HTTP launcher starts the FastAPI app and an embedded SMTP listener in one process, using the current working directory as the storage root. Running it from the repository root creates `./storage/` and `./storage/app.db`.
If you need a standalone SMTP listener for a custom setup, you can still run `.venv/bin/rapid-inbox-smtp` in a separate terminal.

## Defaults

The startup defaults live in `app/config.py` and are mirrored in `.env.example` for reference:

- Bootstrap admin username: `admin`
- Bootstrap admin password: `change-me-now`
- Session cookie name: `rapid_inbox_session`
- HTTP host and port: `127.0.0.1:8000`
- SMTP host and port: `127.0.0.1:25`
- Max message size: `52428800`
- Max recipients per message: `20`

The default launcher flow creates the bootstrap admin with username `admin` and password `change-me-now`, so the login step is immediately usable on a fresh local checkout.

The app does not auto-load `.env` yet, so treat `.env.example` as a reference template unless you add your own loader. If you want a different bootstrap admin password, override `bootstrap_admin_password` when constructing `Settings` in a custom launcher.

## Notes

- The HTTP runner starts the FastAPI app and the embedded `aiosmtpd` listener with Uvicorn.
- The SMTP runner starts the standalone `aiosmtpd` listener and keeps it alive until interrupted.
- The admin login page uses the bootstrap admin credentials created on startup.
