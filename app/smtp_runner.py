from __future__ import annotations

import asyncio
from pathlib import Path

from app.config import default_settings
from app.runtime import RapidInboxRuntime
from app.smtp.server import SMTPServer


async def main_async() -> None:
    settings = default_settings(Path.cwd())
    runtime = RapidInboxRuntime(settings)
    server: SMTPServer | None = None
    try:
        await runtime.start()
        server = SMTPServer(runtime)
        server.start()
        await asyncio.Event().wait()
    finally:
        try:
            if server is not None:
                server.stop()
        finally:
            await runtime.stop()


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
