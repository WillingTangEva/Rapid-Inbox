from __future__ import annotations

from app.http.template_helpers import cn_datetime, cn_time


def test_cn_datetime_converts_utc_to_shanghai_time() -> None:
    assert cn_datetime("2026-04-18T20:00:00Z") == "2026-04-19 04:00:00"


def test_cn_time_converts_utc_to_shanghai_time() -> None:
    assert cn_time("2026-04-18T20:00:00Z") == "04:00:00"
