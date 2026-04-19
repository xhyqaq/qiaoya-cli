"""Qiaoya CLI 输出格式化工具。"""
from __future__ import annotations

from datetime import datetime
from typing import Any


def text_or_dash(value: Any) -> str:
    if value is None:
        return "-"
    text = str(value).strip()
    return text if text else "-"


def short_id(value: Any, size: int = 8) -> str:
    text = text_or_dash(value)
    if text == "-":
        return text
    return text if len(text) <= size else f"{text[:size]}…"


def compact_text(value: Any, limit: int = 80) -> str:
    text = text_or_dash(value)
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return f"{text[: max(1, limit - 1)]}…"


def yes_no(value: Any) -> str:
    return "是" if bool(value) else "否"


def format_time(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    text = str(value)
    if "T" in text:
        text = text.replace("T", " ")
    return text[:19]
