import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from cli_anything.qiaoya.core.session_store import SessionData, SessionStore
from cli_anything.qiaoya.utils.api_client import APIError, QiaoyaClient


class DummyResponse:
    def __init__(self, status_code=200, body=None, text="", ok=None):
        self.status_code = status_code
        self._body = body
        self.text = text
        self.ok = status_code < 400 if ok is None else ok

    def json(self):
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


def _make_client(tmp_path: Path, base_url: str = "https://code.xhyovo.cn") -> QiaoyaClient:
    store = SessionStore(path=tmp_path / "session.json")
    store.save(
        SessionData(
            base_url=base_url,
            token="token-123",
            user={"id": "user-1", "name": "Alice"},
            device_id="device-abc",
        )
    )
    return QiaoyaClient(base_url=base_url, session_store=store)


def test_session_store_creates_and_backfills_device_id(tmp_path):
    store_path = tmp_path / "session.json"
    store = SessionStore(path=store_path)

    session = store.load(default_base_url="https://code.xhyovo.cn")

    assert store_path.exists()
    assert session.base_url == "https://code.xhyovo.cn"
    assert session.device_id

    persisted = json.loads(store_path.read_text(encoding="utf-8"))
    assert persisted["base_url"] == "https://code.xhyovo.cn"
    assert persisted["token"] is None
    assert persisted["user"] is None
    assert persisted["device_id"] == session.device_id

    store_path.write_text(
        json.dumps(
            {
                "base_url": "https://code.xhyovo.cn",
                "token": "token-xyz",
                "user": {"id": "user-2"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    repaired = store.load(default_base_url="https://code.xhyovo.cn")
    repaired_raw = json.loads(store_path.read_text(encoding="utf-8"))

    assert repaired.token == "token-xyz"
    assert repaired.user == {"id": "user-2"}
    assert repaired.device_id
    assert repaired_raw["device_id"] == repaired.device_id


def test_client_injects_auth_and_device_headers(tmp_path):
    client = _make_client(tmp_path)
    captured = {}

    def fake_request(method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["headers"] = kwargs.get("headers", {})
        return DummyResponse(body={"code": 200, "data": {"id": "user-1"}})

    client.session.request = fake_request

    client.get_me()

    assert captured["method"] == "GET"
    assert captured["url"] == "https://code.xhyovo.cn/api/user"
    assert captured["headers"]["Authorization"] == "Bearer token-123"
    assert captured["headers"]["X-Device-ID"] == "device-abc"


def test_remove_other_sessions_deletes_only_non_current_ips(tmp_path):
    client = _make_client(tmp_path)
    removed = []

    client.list_active_sessions = lambda: [
        {"ip": "1.1.1.1", "current": True},
        {"ip": "2.2.2.2", "isCurrent": False},
        {"ip": "3.3.3.3", "current": False},
    ]
    client.remove_active_session = lambda ip: removed.append(ip)

    result = client.remove_other_sessions()

    assert removed == ["2.2.2.2", "3.3.3.3"]
    assert result == removed


def test_update_post_status_uses_patch_and_published_payload(tmp_path):
    client = _make_client(tmp_path)
    captured = {}

    def fake_request(method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        return DummyResponse(body={"code": 200, "data": {"id": "post-1"}})

    client.session.request = fake_request

    client.update_post_status("post-1", "PUBLISHED")

    assert captured["method"] == "PATCH"
    assert captured["url"] == "https://code.xhyovo.cn/api/user/posts/post-1/status"
    assert captured["json"] == {"status": "PUBLISHED"}


def test_reply_comment_uses_reply_endpoint_and_payload(tmp_path):
    client = _make_client(tmp_path)
    captured = {}

    def fake_request(method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        return DummyResponse(body={"code": 200, "data": {"id": "comment-2"}})

    client.session.request = fake_request

    client.reply_comment(
        "comment-1",
        business_id="post-9",
        business_type="POST",
        content="reply body",
    )

    assert captured["method"] == "POST"
    assert captured["url"] == "https://code.xhyovo.cn/api/user/comments/comment-1/reply"
    assert captured["json"] == {
        "parentCommentId": "comment-1",
        "businessId": "post-9",
        "businessType": "POST",
        "content": "reply body",
    }


def test_report_learning_progress_maps_payload_aliases(tmp_path):
    client = _make_client(tmp_path)
    captured = {}

    def fake_request(method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        return DummyResponse(body={"code": 200, "data": {"courseId": "course-1"}})

    client.session.request = fake_request

    client.report_learning_progress(
        course_id="course-1",
        chapter_id="chapter-1",
        progress_percent=80,
        study_duration_seconds=120,
        position_sec=77,
    )

    assert captured["method"] == "POST"
    assert captured["url"] == "https://code.xhyovo.cn/api/user/learning/progress/report"
    assert captured["json"]["courseId"] == "course-1"
    assert captured["json"]["chapterId"] == "chapter-1"
    assert captured["json"]["progressPercent"] == 80
    assert captured["json"]["positionSec"] == 77
    assert captured["json"]["timeSpentDeltaSec"] == 120
    assert captured["json"]["studyDurationSeconds"] == 120


def test_activate_cdk_uses_expected_payload(tmp_path):
    client = _make_client(tmp_path)
    captured = {}

    def fake_request(method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        return DummyResponse(body={"code": 200, "data": None})

    client.session.request = fake_request

    client.activate_cdk("CDK-123")

    assert captured["method"] == "POST"
    assert captured["url"] == "https://code.xhyovo.cn/api/user/subscription/activate-cdk"
    assert captured["json"] == {"cdkCode": "CDK-123"}


def test_public_courses_list_uses_public_endpoint_without_auth(tmp_path):
    client = _make_client(tmp_path)
    captured = {}

    def fake_request(method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        captured["headers"] = kwargs.get("headers", {})
        return DummyResponse(body={"code": 200, "data": {"records": []}})

    client.session.request = fake_request

    client.list_public_courses(page=2, size=5)

    assert captured["method"] == "POST"
    assert captured["url"] == "https://code.xhyovo.cn/api/public/courses/queries"
    assert captured["json"] == {"pageNum": 2, "pageSize": 5}
    assert "Authorization" not in captured["headers"]


def test_send_chat_message_uses_room_message_endpoint(tmp_path):
    client = _make_client(tmp_path)
    captured = {}

    def fake_request(method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        return DummyResponse(body={"code": 200, "data": {"id": "msg-1"}})

    client.session.request = fake_request

    client.send_chat_message("room-1", "你好", message_type="TEXT")

    assert captured["method"] == "POST"
    assert captured["url"] == "https://code.xhyovo.cn/api/app/chat-rooms/room-1/messages"
    assert captured["json"] == {"content": "你好", "messageType": "TEXT"}


def test_unread_visit_uses_expected_channel_param(tmp_path):
    client = _make_client(tmp_path)
    captured = {}

    def fake_request(method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["params"] = kwargs.get("params")
        return DummyResponse(body={"code": 200, "data": None})

    client.session.request = fake_request

    client.visit_unread_channel("POSTS")

    assert captured["method"] == "PUT"
    assert captured["url"] == "https://code.xhyovo.cn/api/user/unread/visit"
    assert captured["params"] == {"channel": "POSTS"}


def test_resource_access_url_uses_public_redirect_endpoint(tmp_path):
    client = _make_client(tmp_path)

    assert client.get_resource_access_url("res-1") == "https://code.xhyovo.cn/api/public/resource/res-1/access"


def test_change_password_uses_expected_payload(tmp_path):
    client = _make_client(tmp_path)
    captured = {}

    def fake_request(method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        return DummyResponse(body={"code": 200, "data": {"id": "user-1"}})

    client.session.request = fake_request

    client.change_password("old-secret", "new-secret")

    assert captured["method"] == "PUT"
    assert captured["url"] == "https://code.xhyovo.cn/api/user/password"
    assert captured["json"] == {"oldPassword": "old-secret", "newPassword": "new-secret"}


def test_api_error_exposes_message_code_and_status():
    err = APIError("boom", code=123, status_code=500)
    assert str(err) == "boom"
    assert err.message == "boom"
    assert err.code == 123
    assert err.status_code == 500


def test_qiaoya_cli_import_does_not_depend_on_adjacent_formatter_source_file(tmp_path):
    source_path = Path(__file__).resolve().parents[1] / "qiaoya_cli.py"
    source = source_path.read_text(encoding="utf-8")
    fake_cli_path = tmp_path / "bundle" / "qiaoya_cli.py"

    module_globals = {
        "__name__": "cli_anything.qiaoya.qiaoya_cli_binary_probe",
        "__file__": str(fake_cli_path),
        "__package__": "cli_anything.qiaoya",
        "__builtins__": __builtins__,
    }

    exec(compile(source, str(fake_cli_path), "exec"), module_globals)

    assert module_globals["_FORMATTERS"].short_id("abcdefghi") == "abcdefgh…"


def test_qiaoya_cli_help_survives_non_utf8_stdout_encoding():
    harness_root = Path(__file__).resolve().parents[3]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(harness_root)
    env["PYTHONIOENCODING"] = "cp1252"

    result = subprocess.run(
        [sys.executable, "-m", "cli_anything.qiaoya.qiaoya_cli", "--help"],
        cwd=harness_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    output = result.stdout.decode("utf-8", errors="replace")
    assert "Usage:" in output
