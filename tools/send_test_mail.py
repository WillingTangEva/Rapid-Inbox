#!/usr/bin/env python3
from __future__ import annotations

import argparse
import smtplib
import sys
import time
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import default_settings  # noqa: E402
from app.db.connection import connect_database  # noqa: E402


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def _load_default_recipient(local_part: str) -> str:
    settings = default_settings(PROJECT_ROOT)
    with connect_database(settings.database_path) as connection:
        row = connection.execute(
            """
            SELECT root_domain_ascii
            FROM domains
            WHERE is_active = 1
              AND accept_exact = 1
            ORDER BY
              CASE dns_status WHEN 'ok' THEN 0 WHEN 'warning' THEN 1 ELSE 2 END,
              id
            LIMIT 1
            """
        ).fetchone()
    if row is None:
        raise RuntimeError("数据库里没有可接收的启用域名，请使用 --to 指定收件地址。")
    return f"{local_part}@{row['root_domain_ascii']}"


def _build_message(
    *,
    sender: str,
    recipient: str,
    subject: str,
    text: str,
    html: str | None,
    attachments: list[Path],
) -> EmailMessage:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid(domain="rapid-inbox.local")
    message.set_content(text)

    if html:
        message.add_alternative(html, subtype="html")

    for attachment in attachments:
        data = attachment.read_bytes()
        message.add_attachment(
            data,
            maintype="application",
            subtype="octet-stream",
            filename=attachment.name,
        )

    return message


def _send_once(args: argparse.Namespace, index: int, recipient: str, smtp: smtplib.SMTP) -> None:
    subject = args.subject
    if args.count > 1:
        subject = f"{subject} #{index}"
    text = args.text or (
        f"这是一封 Rapid Inbox 本地 SMTP 投递测试邮件。\n"
        f"序号: {index}\n"
        f"时间: {datetime.now().isoformat(timespec='seconds')}\n"
        f"收件人: {recipient}\n"
    )
    html = args.html
    if html is None and not args.no_html:
        html = (
            "<!doctype html>"
            "<html><body>"
            "<h1>Rapid Inbox 投递测试</h1>"
            f"<p>序号：<strong>{index}</strong></p>"
            f"<p>收件人：<code>{recipient}</code></p>"
            "<p>如果你在公开收件箱或管理后台看到这封邮件，SMTP 接收链路就是通的。</p>"
            "</body></html>"
        )

    message = _build_message(
        sender=args.sender,
        recipient=recipient,
        subject=subject,
        text=text,
        html=html,
        attachments=args.attachment,
    )

    smtp.send_message(message, from_addr=args.sender, to_addrs=[recipient])

    print(f"已投递: {recipient} | {subject}")


def parse_args() -> argparse.Namespace:
    settings = default_settings(PROJECT_ROOT)
    stamp = _utc_stamp()

    parser = argparse.ArgumentParser(description="向本机 Rapid Inbox SMTP 服务投递临时测试邮件。")
    parser.add_argument("--host", default=settings.smtp_host, help=f"SMTP 主机，默认 {settings.smtp_host}")
    parser.add_argument("--port", type=int, default=settings.smtp_port, help=f"SMTP 端口，默认 {settings.smtp_port}")
    parser.add_argument("--to", help="收件地址；不填时自动选择数据库中第一个启用域名。")
    parser.add_argument("--local-part", default=f"codex-test-{stamp}", help="自动生成收件地址时使用的本地部分。")
    parser.add_argument("--sender", default="sender@example.test", help="发件地址。")
    parser.add_argument("--subject", default=f"Rapid Inbox 临时投递测试 {stamp}", help="邮件主题。")
    parser.add_argument("--text", help="纯文本正文；不填时生成默认正文。")
    parser.add_argument("--html", help="HTML 正文；不填时生成默认 HTML 正文。")
    parser.add_argument("--no-html", action="store_true", help="只发送纯文本正文。")
    parser.add_argument("--attachment", action="append", type=Path, default=[], help="添加附件，可重复传入。")
    parser.add_argument("--count", type=int, default=1, help="投递邮件数量。")
    parser.add_argument("--interval", type=float, default=0.2, help="多封邮件之间的间隔秒数。")
    parser.add_argument("--timeout", type=float, default=10.0, help="SMTP 连接超时秒数。")
    parser.add_argument("--starttls", action="store_true", help="先执行 STARTTLS 再投递。")
    parser.add_argument("--debug", action="store_true", help="输出 SMTP 对话调试信息。")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.count < 1:
        raise SystemExit("--count 必须大于等于 1")

    missing = [path for path in args.attachment if not path.is_file()]
    if missing:
        raise SystemExit("附件不存在: " + ", ".join(str(path) for path in missing))

    recipient = args.to or _load_default_recipient(args.local_part)
    with smtplib.SMTP(args.host, args.port, timeout=args.timeout) as smtp:
        if args.debug:
            smtp.set_debuglevel(1)
        if args.starttls:
            smtp.starttls()
        for index in range(1, args.count + 1):
            _send_once(args, index, recipient, smtp)
            if index < args.count:
                time.sleep(args.interval)

    print(f"收件箱: http://127.0.0.1:8000/mail/{recipient}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
