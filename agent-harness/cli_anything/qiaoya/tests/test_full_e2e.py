from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest
from click.testing import CliRunner

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cli_anything.qiaoya import qiaoya_cli


class FakeClient:
    responses: dict[tuple[str, str], object] = {}
    instances: list["FakeClient"] = []
    session_user = {"username": "tester", "email": "tester@example.com"}

    def __init__(self, base_url=None, token=None):
        session_payload = {}
        if token is None and qiaoya_cli.SESSION_FILE.exists():
            try:
                session_payload = json.loads(qiaoya_cli.SESSION_FILE.read_text())
            except Exception:
                session_payload = {}
        self.base_url = (base_url or session_payload.get("base_url") or "https://code.xhyovo.cn").rstrip("/")
        self.token = token or session_payload.get("token")
        self.session = SimpleNamespace(headers={})
        self.calls = []
        self.session_user = session_payload.get("user") or self.session_user
        FakeClient.instances.append(self)

    @classmethod
    def reset(cls):
        cls.responses = {}
        cls.instances = []
        cls.session_user = {"username": "tester", "email": "tester@example.com"}

    def _record(self, method, path, auth=True, **kwargs):
        self.calls.append(
            {
                "method": method.upper(),
                "path": path,
                "auth": auth,
                "kwargs": kwargs,
                "headers": dict(self.session.headers),
            }
        )

    def _dispatch(self, method, path, auth=True, **kwargs):
        self._record(method, path, auth=auth, **kwargs)
        key = (method.upper(), path)
        if key not in self.responses:
            raise AssertionError(f"unexpected request: {key}")
        value = self.responses[key]
        if callable(value):
            return value(self, kwargs)
        return value

    def _request(self, method, path, auth=True, **kwargs):
        return self._dispatch(method, path, auth=auth, **kwargs)

    def get(self, path, auth=True, **kwargs):
        return self._request("GET", path, auth=auth, **kwargs)

    def post(self, path, auth=True, json_data=None, **kwargs):
        if json_data is not None:
            kwargs["json"] = json_data
        return self._request("POST", path, auth=auth, **kwargs)

    def put(self, path, auth=True, json_data=None, **kwargs):
        if json_data is not None:
            kwargs["json"] = json_data
        return self._request("PUT", path, auth=auth, **kwargs)

    def delete(self, path, auth=True, **kwargs):
        return self._request("DELETE", path, auth=auth, **kwargs)

    def login(self, email, password):
        self.calls.append({"method": "LOGIN", "email": email, "password": password})
        payload = {
            "token": "token-123",
            "userInfo": {
                "id": "u-1",
                "username": "tester",
                "email": email,
            },
        }
        self.token = payload["token"]
        return payload

    def logout(self):
        self.calls.append({"method": "LOGOUT"})
        self.token = None

    def load_session_user(self):
        return self.session_user

    def save_session(self, token, user):
        self.token = token
        self.calls.append({"method": "SAVE_SESSION", "token": token, "user": user})

    def clear_session(self):
        self.token = None
        self.calls.append({"method": "CLEAR_SESSION"})

    def list_posts(self, page=1, size=10, category_type=None):
        payload = {"pageNum": page, "pageSize": size}
        if category_type:
            payload["categoryType"] = category_type
        return self.post("/api/app/posts/queries", auth=False, json_data=payload)

    def get_post(self, post_id):
        return self.get(f"/api/app/posts/{post_id}", auth=False)

    def list_my_posts(self, page=1, size=10, status=None):
        params = {"pageNum": page, "pageSize": size}
        if status:
            params["status"] = status
        return self.get("/api/user/posts", params=params)

    def create_post(self, title, content, category_id, summary=None, cover_image=None, post_type="ARTICLE"):
        payload = {
            "title": title,
            "content": content,
            "categoryId": category_id,
            "type": post_type,
        }
        if summary:
            payload["summary"] = summary
        if cover_image:
            payload["coverImage"] = cover_image
        return self.post("/api/user/posts", json_data=payload)

    def update_post(self, post_id, **kwargs):
        return self.put(f"/api/user/posts/{post_id}", json_data=kwargs)

    def delete_post(self, post_id):
        return self.delete(f"/api/user/posts/{post_id}")

    def list_active_sessions(self):
        return self.get("/api/user/sessions/active")

    def list_comments(self, business_id, business_type="POST", page=1, size=10):
        return self.get(
            "/api/app/comments",
            params={
                "businessId": business_id,
                "businessType": business_type,
                "pageNum": page,
                "pageSize": size,
            },
        )

    def create_comment(self, business_id, content, business_type="POST", parent_id=None):
        payload = {"businessId": business_id, "content": content, "businessType": business_type}
        if parent_id:
            payload["parentId"] = parent_id
        return self.post("/api/user/comments", json_data=payload)

    def delete_comment(self, comment_id):
        return self.delete(f"/api/user/comments/{comment_id}")

    def toggle_like(self, target_id, target_type="POST"):
        return self.post("/api/likes/toggle", json_data={"targetId": target_id, "targetType": target_type})

    def get_like_status(self, target_id, target_type="POST"):
        return self.get(f"/api/likes/status/{target_type}/{target_id}")

    def toggle_favorite(self, target_id, target_type="POST"):
        return self.post("/api/favorites/toggle", json_data={"targetId": target_id, "targetType": target_type})

    def list_my_favorites(self, page=1, size=10):
        return self.get("/api/favorites/my", params={"pageNum": page, "pageSize": size})

    def list_notifications(self, page=1, size=20):
        return self.get("/api/user/notifications", params={"pageNum": page, "pageSize": size})

    def get_unread_count(self):
        return self.get("/api/user/notifications/unread-count")

    def mark_all_read(self):
        return self.put("/api/user/notifications/read-all")

    def get_categories(self, category_type=None):
        params = {}
        if category_type:
            params["type"] = category_type
        return self.get("/api/app/categories/tree", params=params)

    def list_courses(self, page=1, size=10):
        return self.post("/api/app/courses/queries", json_data={"pageNum": page, "pageSize": size})

    def get_course(self, course_id):
        return self.get(f"/api/app/courses/{course_id}")

    def get_me(self):
        return self.get("/api/user")

    def get_user(self, user_id):
        return self.get(f"/api/user/{user_id}")

    def list_public_courses(self, page=1, size=10):
        return self.post("/api/public/courses/queries", auth=False, json_data={"pageNum": page, "pageSize": size})

    def get_public_course(self, course_id):
        return self.get(f"/api/public/courses/{course_id}", auth=False)

    def get_public_subscription_plans(self):
        return self.get("/api/public/subscription-plans", auth=False)

    def get_public_stats(self):
        return self.get("/api/public/stats/users", auth=False)

    def get_about_page(self):
        return self.get("/api/public/site/about", auth=False)

    def list_public_testimonials(self):
        return self.get("/api/public/testimonials", auth=False)

    def list_public_update_logs(self):
        return self.get("/api/app/update-logs", auth=False)

    def get_public_update_log(self, log_id):
        return self.get(f"/api/app/update-logs/{log_id}", auth=False)

    def get_ai_news_today(self):
        return self.get("/api/app/ai-news/today", auth=False)

    def list_ai_news_history(self, page=1, size=10):
        return self.get("/api/app/ai-news/history", auth=False, params={"pageNum": page, "pageSize": size})

    def list_ai_news_daily(self, date, page=1, size=10):
        return self.get("/api/app/ai-news/daily", auth=False, params={"date": date, "pageNum": page, "pageSize": size})

    def get_ai_news_detail(self, news_id):
        return self.get(f"/api/app/ai-news/detail/{news_id}", auth=False)

    def get_unread_summary(self):
        return self.get("/api/user/unread/summary")

    def visit_unread_channel(self, channel):
        return self.put("/api/user/unread/visit", params={"channel": channel})

    def list_chat_rooms(self, page=1, size=20, name_like=None):
        params = {"pageNum": page, "pageSize": size}
        if name_like:
            params["nameLike"] = name_like
        return self.get("/api/app/chat-rooms", params=params)

    def join_chat_room(self, room_id):
        return self.post(f"/api/app/chat-rooms/{room_id}/join")

    def list_chat_room_members(self, room_id):
        return self.get(f"/api/app/chat-rooms/{room_id}/members")

    def get_chat_room_unread_info(self, room_id):
        return self.get(f"/api/app/chat-rooms/{room_id}/unread-info")

    def visit_chat_room(self, room_id, anchor_id=None, anchor_time=None):
        params = {}
        if anchor_id:
            params["anchorId"] = anchor_id
        if anchor_time:
            params["anchorTime"] = anchor_time
        return self.put(f"/api/app/chat-rooms/{room_id}/visit", params=params)

    def list_chat_messages(self, room_id, page=1, size=20):
        return self.get(f"/api/app/chat-rooms/{room_id}/messages", params={"pageNum": page, "pageSize": size})

    def send_chat_message(self, room_id, content, message_type="TEXT"):
        return self.post(f"/api/app/chat-rooms/{room_id}/messages", json_data={"content": content, "messageType": message_type})

    def change_password(self, old_password, new_password):
        return self.put("/api/user/password", json_data={"oldPassword": old_password, "newPassword": new_password})

    def toggle_email_notification(self):
        return self.put("/api/user/email-notification")

    def get_menu_codes(self):
        return self.get("/api/user/menu-codes")

    def heartbeat(self):
        return self.get("/api/user/heartbeat")


@pytest.fixture
def cli_env(monkeypatch, tmp_path):
    FakeClient.reset()
    monkeypatch.setattr(qiaoya_cli, "QiaoyaClient", FakeClient)
    monkeypatch.setattr(qiaoya_cli, "SESSION_FILE", tmp_path / "session.json")
    return tmp_path


def _invoke(args, input_text=None):
    runner = CliRunner()
    return runner.invoke(qiaoya_cli.cli, args, input=input_text)


def test_help_and_repl_quit(cli_env, monkeypatch):
    class DummySkin:
        def __init__(self, *args, **kwargs):
            self.lines = ["quit"]

        def print_banner(self):
            print("BANNER")

        def create_prompt_session(self):
            return object()

        def get_input(self, _session, project_name=""):
            return self.lines.pop(0)

        def print_goodbye(self):
            print("BYE")

        def error(self, message):
            print(f"ERR:{message}")

    monkeypatch.setattr("cli_anything.qiaoya.utils.repl_skin.ReplSkin", DummySkin)

    help_result = _invoke(["--help"])
    assert help_result.exit_code == 0
    assert "auth" in help_result.output
    assert "post" in help_result.output
    assert "course" in help_result.output
    assert "learning" in help_result.output
    assert "public" in help_result.output
    assert "ai-news" in help_result.output
    assert "chat" in help_result.output

    repl_result = _invoke([])
    assert repl_result.exit_code == 0
    assert "BANNER" in repl_result.output
    assert "BYE" in repl_result.output


def test_login_logout_and_session_headers(cli_env):
    FakeClient.responses = {
        ("GET", "/api/user"): {"id": "u-1", "username": "tester", "email": "tester@example.com"},
    }

    login_result = _invoke(["auth", "login", "-e", "tester@example.com", "-p", "secret"])
    assert login_result.exit_code == 0
    session_path = qiaoya_cli.SESSION_FILE
    assert session_path.exists()
    payload = json.loads(session_path.read_text())
    assert payload["token"] == "token-123"
    assert payload["device_id"]
    assert payload["user"]["username"] == "tester"

    me_result = _invoke(["user", "me"])
    assert me_result.exit_code == 0
    client = FakeClient.instances[-1]
    assert client.calls[-1]["path"] == "/api/user"
    assert client.calls[-1]["headers"]["Authorization"] == "Bearer token-123"
    assert client.calls[-1]["headers"]["X-Device-ID"] == payload["device_id"]

    logout_result = _invoke(["auth", "logout"])
    assert logout_result.exit_code == 0
    assert not session_path.exists()


def test_session_notification_and_post_commands(cli_env):
    login_result = _invoke(["auth", "login", "-e", "tester@example.com", "-p", "secret"])
    assert login_result.exit_code == 0

    FakeClient.responses = {
        ("GET", "/api/user/sessions/active"): [
            {"ip": "10.0.0.1", "lastSeenTime": "2026-04-16T10:00:00", "isCurrent": True},
            {"ip": "10.0.0.2", "lastSeenTime": "2026-04-16T09:00:00", "isCurrent": False},
        ],
        ("DELETE", "/api/user/sessions/active/10.0.0.2"): {},
        ("GET", "/api/user/notifications/unread-count"): {"unreadCount": 3},
        ("PUT", "/api/user/notifications/notice-1/read"): {},
        ("PUT", "/api/user/notifications/read-all"): {},
        ("POST", "/api/app/posts/queries"): {
            "records": [{"id": "post-1", "title": "hello world", "authorName": "alice", "status": "PUBLISHED", "likeCount": 2, "commentCount": 1, "createTime": "2026-04-16T10:00:00"}],
            "total": 1,
            "current": 1,
            "pages": 1,
        },
        ("PATCH", "/api/user/posts/post-1/status"): {"id": "post-1", "status": "PUBLISHED"},
        ("POST", "/api/user/comments/cmt-1/reply"): {"id": "reply-1"},
    }

    session_result = _invoke(["session", "list"])
    assert session_result.exit_code == 0
    assert "10.0.0.1" in session_result.output
    assert "当前" in session_result.output

    remove_result = _invoke(["session", "remove-others", "--yes"])
    assert remove_result.exit_code == 0
    assert any(call["path"] == "/api/user/sessions/active/10.0.0.2" for call in FakeClient.instances[-1].calls)

    unread_result = _invoke(["notification", "unread"])
    assert unread_result.exit_code == 0
    assert "3" in unread_result.output

    read_result = _invoke(["notification", "read", "notice-1"])
    assert read_result.exit_code == 0
    assert any(call["path"] == "/api/user/notifications/notice-1/read" for call in FakeClient.instances[-1].calls)

    read_all_result = _invoke(["notification", "read-all"])
    assert read_all_result.exit_code == 0
    assert any(call["path"] == "/api/user/notifications/read-all" for call in FakeClient.instances[-1].calls)

    posts_result = _invoke(["--json", "post", "list"])
    assert posts_result.exit_code == 0
    assert json.loads(posts_result.output)["records"][0]["id"] == "post-1"

    publish_result = _invoke(["post", "publish", "post-1"])
    assert publish_result.exit_code == 0
    assert any(call["method"] == "PATCH" and call["path"] == "/api/user/posts/post-1/status" for call in FakeClient.instances[-1].calls)

    reply_result = _invoke(["comment", "reply", "cmt-1", "--business-id", "post-1", "--content", "thanks"])
    assert reply_result.exit_code == 0
    assert any(call["path"] == "/api/user/comments/cmt-1/reply" for call in FakeClient.instances[-1].calls)


def test_learning_social_and_course_commands(cli_env):
    login_result = _invoke(["auth", "login", "-e", "tester@example.com", "-p", "secret"])
    assert login_result.exit_code == 0

    FakeClient.responses = {
        ("GET", "/api/app/categories/tree"): [{"id": "cat-1", "name": "前端", "children": []}],
        ("GET", "/api/user/follows"): {"records": [{"targetId": "u-2", "targetType": "USER", "targetName": "bob", "createTime": "2026-04-16T10:00:00"}], "total": 1, "current": 1, "pages": 1},
        ("GET", "/api/app/follows/check/USER/u-2"): {"isFollowing": True},
        ("GET", "/api/favorites/status/POST/post-1"): {"isFavorited": True, "favoritesCount": 5},
        ("GET", "/api/favorites/my"): {"records": [{"targetId": "post-1", "targetType": "POST", "title": "hello", "createTime": "2026-04-16T10:00:00"}], "total": 1, "current": 1, "pages": 1},
        ("POST", "/api/app/courses/queries"): {"records": [{"id": "course-1", "title": "Vite 入门", "teacherName": "alice", "chapterCount": 3, "createTime": "2026-04-16T10:00:00"}], "total": 1, "current": 1, "pages": 1},
        ("GET", "/api/app/courses/course-1"): {"id": "course-1", "title": "Vite 入门", "authorName": "alice", "description": "简介", "chapters": [{"id": "ch-1"}]},
        ("GET", "/api/app/chapters/ch-1"): {"id": "ch-1", "title": "第一章", "courseName": "Vite 入门", "content": "chapter content", "readingTime": 10, "sortOrder": 1},
        ("GET", "/api/app/chapters/latest"): [{"id": "ch-1", "title": "第一章", "courseName": "Vite 入门", "createTime": "2026-04-16T10:00:00"}],
        ("GET", "/api/user/learning/progress/course-1"): {"courseId": "course-1", "totalChapters": 3, "completedChapters": 1, "progressPercent": 33},
        ("GET", "/api/user/learning/records"): {"records": [{"courseId": "course-1", "courseTitle": "Vite 入门", "progressPercent": 33, "completedChapters": 1, "totalChapters": 3, "lastAccessChapterTitle": "第一章", "lastAccessTime": "2026-04-16T10:00:00"}], "total": 1, "current": 1, "pages": 1},
        ("POST", "/api/user/learning/progress/report"): {"courseId": "course-1"},
        ("POST", "/api/user/subscription/activate-cdk"): {},
        ("POST", "/api/likes/toggle"): {"isLiked": True},
        ("GET", "/api/likes/status/POST/post-1"): {"liked": True, "count": 2},
        ("POST", "/api/favorites/toggle"): {"isFavorited": True},
        ("POST", "/api/app/follows/toggle"): {"isFollowing": True},
    }

    categories = _invoke(["category", "list"])
    assert categories.exit_code == 0
    assert "前端" in categories.output

    follows = _invoke(["follow", "list"])
    assert follows.exit_code == 0
    assert "bob" in follows.output

    follow_status = _invoke(["follow", "status", "u-2"])
    assert follow_status.exit_code == 0
    assert "是" in follow_status.output

    favorite_status = _invoke(["favorite", "status", "post-1"])
    assert favorite_status.exit_code == 0
    assert "5" in favorite_status.output

    courses = _invoke(["course", "list"])
    assert courses.exit_code == 0
    assert "Vite 入门" in courses.output

    course_detail = _invoke(["course", "get", "course-1"])
    assert course_detail.exit_code == 0
    assert "简介" in course_detail.output

    chapter_detail = _invoke(["chapter", "get", "ch-1"])
    assert chapter_detail.exit_code == 0
    assert "第一章" in chapter_detail.output

    chapter_latest = _invoke(["chapter", "latest"])
    assert chapter_latest.exit_code == 0
    assert "第一章" in chapter_latest.output

    learning_progress = _invoke(["learning", "progress", "course-1"])
    assert learning_progress.exit_code == 0
    assert "33%" in learning_progress.output

    learning_records = _invoke(["learning", "records"])
    assert learning_records.exit_code == 0
    assert "Vite 入门" in learning_records.output

    report = _invoke(["learning", "report", "--course-id", "course-1", "--chapter-id", "ch-1", "--study-duration", "90", "--progress-percent", "33"])
    assert report.exit_code == 0
    assert any(call["path"] == "/api/user/learning/progress/report" for call in FakeClient.instances[-1].calls)

    activate = _invoke(["subscription", "activate-cdk", "CDK-123"])
    assert activate.exit_code == 0
    assert any(call["path"] == "/api/user/subscription/activate-cdk" for call in FakeClient.instances[-1].calls)


def test_public_and_ai_news_commands(cli_env):
    FakeClient.responses = {
        ("GET", "/api/public/site/about"): {"title": "关于敲鸭", "content": "站点介绍"},
        ("GET", "/api/public/stats/users"): {"totalCount": 128},
        ("POST", "/api/public/courses/queries"): {
            "records": [{"id": "course-public-1", "title": "公开课", "teacherName": "alice"}],
            "total": 1,
            "current": 1,
            "pages": 1,
        },
        ("GET", "/api/public/subscription-plans"): [{"id": "plan-1", "name": "会员月卡"}],
        ("GET", "/api/public/testimonials"): [{"id": "test-1", "content": "很值", "authorName": "alice"}],
        ("GET", "/api/app/update-logs"): [{"id": "log-1", "title": "版本更新"}],
        ("GET", "/api/app/ai-news/today"): {"date": "2026-04-20", "titles": ["GPT-5.5"]},
        ("GET", "/api/app/ai-news/history"): {"records": [{"date": "2026-04-19", "title": "历史日报"}], "total": 1, "current": 1, "pages": 1},
    }

    about = _invoke(["public", "about"])
    assert about.exit_code == 0
    assert "关于敲鸭" in about.output

    stats = _invoke(["public", "stats"])
    assert stats.exit_code == 0
    assert "128" in stats.output

    public_courses = _invoke(["public", "course-list"])
    assert public_courses.exit_code == 0
    assert "公开课" in public_courses.output

    plans = _invoke(["--json", "public", "plans"])
    assert plans.exit_code == 0
    assert json.loads(plans.output)[0]["id"] == "plan-1"

    ai_today = _invoke(["ai-news", "today"])
    assert ai_today.exit_code == 0
    assert "GPT-5.5" in ai_today.output

    ai_history = _invoke(["ai-news", "history"])
    assert ai_history.exit_code == 0
    assert "历史日报" in ai_history.output


def test_unread_chat_and_user_setting_commands(cli_env):
    login_result = _invoke(["auth", "login", "-e", "tester@example.com", "-p", "secret"])
    assert login_result.exit_code == 0

    FakeClient.responses = {
        ("GET", "/api/user/unread/summary"): {"postsUnread": 2, "questionsUnread": 1, "chaptersUnread": 3, "chatsUnread": 4},
        ("PUT", "/api/user/unread/visit"): {},
        ("GET", "/api/app/chat-rooms"): {"records": [{"id": "room-1", "name": "敲鸭群"}], "total": 1, "current": 1, "pages": 1},
        ("POST", "/api/app/chat-rooms/room-1/join"): {},
        ("GET", "/api/app/chat-rooms/room-1/members"): [{"id": "u-1", "name": "alice"}],
        ("GET", "/api/app/chat-rooms/room-1/unread-info"): {"count": 5, "firstUnreadId": "msg-1"},
        ("PUT", "/api/app/chat-rooms/room-1/visit"): {},
        ("GET", "/api/app/chat-rooms/room-1/messages"): {"records": [{"id": "msg-1", "content": "hello"}], "total": 1, "current": 1, "pages": 1},
        ("POST", "/api/app/chat-rooms/room-1/messages"): {"id": "msg-2", "content": "你好"},
        ("PUT", "/api/user/password"): {"id": "u-1"},
        ("PUT", "/api/user/email-notification"): {"id": "u-1", "emailNotificationEnabled": True},
        ("GET", "/api/user/menu-codes"): ["POST_READ", "COURSE_READ"],
        ("GET", "/api/user/heartbeat"): {},
    }

    unread_summary = _invoke(["unread", "summary"])
    assert unread_summary.exit_code == 0
    assert "4" in unread_summary.output

    unread_visit = _invoke(["unread", "visit", "POSTS"])
    assert unread_visit.exit_code == 0
    assert any(call["path"] == "/api/user/unread/visit" for call in FakeClient.instances[-1].calls)

    chat_rooms = _invoke(["chat", "rooms"])
    assert chat_rooms.exit_code == 0
    assert "敲鸭群" in chat_rooms.output

    chat_join = _invoke(["chat", "join", "room-1"])
    assert chat_join.exit_code == 0

    chat_members = _invoke(["chat", "members", "room-1"])
    assert chat_members.exit_code == 0
    assert "alice" in chat_members.output

    chat_messages = _invoke(["chat", "messages", "room-1"])
    assert chat_messages.exit_code == 0
    assert "hello" in chat_messages.output

    chat_send = _invoke(["chat", "send", "room-1", "--content", "你好"])
    assert chat_send.exit_code == 0
    assert any(call["path"] == "/api/app/chat-rooms/room-1/messages" and call["method"] == "POST" for call in FakeClient.instances[-1].calls)

    change_password = _invoke(["user", "change-password", "--old-password", "old", "--new-password", "new"])
    assert change_password.exit_code == 0
    assert any(call["path"] == "/api/user/password" for call in FakeClient.instances[-1].calls)

    toggle_notification = _invoke(["user", "toggle-email-notification"])
    assert toggle_notification.exit_code == 0
    assert any(call["path"] == "/api/user/email-notification" for call in FakeClient.instances[-1].calls)

    menu_codes = _invoke(["user", "menu-codes"])
    assert menu_codes.exit_code == 0
    assert "POST_READ" in menu_codes.output

    heartbeat = _invoke(["auth", "heartbeat"])
    assert heartbeat.exit_code == 0
    assert any(call["path"] == "/api/user/heartbeat" for call in FakeClient.instances[-1].calls)


@pytest.mark.skipif(__import__("os").environ.get("QIAOYA_LIVE_SMOKE") != "1", reason="live smoke disabled")
def test_live_public_smoke():
    runner = CliRunner()
    result = runner.invoke(qiaoya_cli.cli, ["--json", "course", "list"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert "records" in payload
