from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


DEFAULT_BASE_URL = "https://code.xhyovo.cn"
DEFAULT_SESSION_DIR = Path.home() / ".cli-anything-qiaoya"
DEFAULT_SESSION_FILE = DEFAULT_SESSION_DIR / "session.json"


def normalize_base_url(base_url: Optional[str]) -> str:
    return (base_url or DEFAULT_BASE_URL).rstrip("/")


def generate_device_id() -> str:
    return uuid.uuid4().hex


@dataclass
class SessionData:
    base_url: str = DEFAULT_BASE_URL
    token: Optional[str] = None
    user: Optional[Any] = None
    device_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_url": normalize_base_url(self.base_url),
            "token": self.token,
            "user": self.user,
            "device_id": self.device_id,
        }

    @classmethod
    def from_dict(cls, data: Optional[dict[str, Any]], default_base_url: Optional[str] = None) -> "SessionData":
        payload = data or {}
        return cls(
            base_url=normalize_base_url(payload.get("base_url") or default_base_url),
            token=payload.get("token"),
            user=payload.get("user"),
            device_id=payload.get("device_id"),
        )


class SessionStore:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path or DEFAULT_SESSION_FILE)

    def load(self, default_base_url: Optional[str] = None) -> SessionData:
        payload: dict[str, Any] = {}
        should_write_back = False

        if self.path.exists():
            try:
                raw = self.path.read_text(encoding="utf-8")
                payload = json.loads(raw) if raw.strip() else {}
            except Exception:
                payload = {}
                should_write_back = True
        else:
            should_write_back = True

        session = SessionData.from_dict(payload, default_base_url=default_base_url)
        if not session.device_id:
            session.device_id = generate_device_id()
            should_write_back = True

        if not session.base_url:
            session.base_url = normalize_base_url(default_base_url)
            should_write_back = True

        if should_write_back:
            self.save(session)

        return session

    def save(self, session: SessionData | dict[str, Any]) -> SessionData:
        data = session if isinstance(session, SessionData) else SessionData.from_dict(session)
        data.base_url = normalize_base_url(data.base_url)
        if not data.device_id:
            data.device_id = generate_device_id()

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(data.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return data

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()
