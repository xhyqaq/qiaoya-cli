"""
敲鸭社区 API 客户端
统一处理会话持久化、请求头注入与 HTTP 错误转换。
"""

from __future__ import annotations

import os
import sys
from typing import Any, Optional

try:
    import requests
except ImportError:
    print("缺少依赖：requests\n请运行：pip install requests", file=sys.stderr)
    sys.exit(1)

from cli_anything.qiaoya.core.session_store import (
    DEFAULT_BASE_URL,
    DEFAULT_SESSION_FILE,
    SessionData,
    SessionStore,
    generate_device_id,
    normalize_base_url,
)

SESSION_FILE = DEFAULT_SESSION_FILE


class APIError(Exception):
    def __init__(self, message: str, code: int = 0, status_code: int = 0):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code

    def __str__(self) -> str:
        return self.message


class QiaoyaClient:
    """敲鸭社区 HTTP API 客户端"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        session_store: Optional[SessionStore] = None,
    ):
        self.session_store = session_store or SessionStore()
        env_base_url = os.environ.get("QIAOYA_BASE_URL")
        explicit_base_url = base_url if base_url is not None else env_base_url
        loaded = self.session_store.load(default_base_url=normalize_base_url(explicit_base_url or DEFAULT_BASE_URL))

        if explicit_base_url:
            loaded.base_url = normalize_base_url(explicit_base_url)
            self.session_store.save(loaded)

        self.session_data = loaded
        self.base_url = normalize_base_url(loaded.base_url)
        self.token = token if token is not None else loaded.token
        self.user = loaded.user
        self.device_id = loaded.device_id or generate_device_id()
        if not loaded.device_id:
            self.session_data.device_id = self.device_id
            self.session_store.save(self.session_data)

        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

        if token is not None:
            self.session_data.token = token

    # ──────────────────────────── 会话 ────────────────────────────

    def _refresh_session_state(self, session: SessionData) -> None:
        self.session_data = session
        self.base_url = normalize_base_url(session.base_url)
        self.token = session.token
        self.user = session.user
        self.device_id = session.device_id or generate_device_id()
        self.session_data.device_id = self.device_id

    def save_session(self, token: str, user: dict[str, Any], base_url: Optional[str] = None) -> SessionData:
        session = SessionData(
            base_url=normalize_base_url(base_url or self.base_url),
            token=token,
            user=user,
            device_id=self.device_id or generate_device_id(),
        )
        self._refresh_session_state(session)
        return self.session_store.save(session)

    def clear_session(self) -> None:
        self.session_store.clear()
        self.token = None
        self.user = None
        self.session_data.token = None
        self.session_data.user = None

    def load_session_user(self) -> Optional[dict[str, Any]]:
        return self.user if isinstance(self.user, dict) else None

    def _auth_headers(self, auth: bool = True) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Device-ID": self.device_id or generate_device_id(),
        }
        if auth:
            if not self.token:
                raise APIError("未登录，请使用 auth login 登录", 401, 401)
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    # ──────────────────────────── HTTP ────────────────────────────

    def _request(self, method: str, path: str, auth: bool = True, **kwargs) -> Any:
        url = f"{self.base_url}{path if path.startswith('/') else '/' + path}"
        headers = kwargs.pop("headers", None) or {}
        headers.update(self._auth_headers(auth=auth))

        try:
            resp = self.session.request(method, url, headers=headers, timeout=30, **kwargs)
        except requests.ConnectionError as exc:
            raise APIError(f"连接失败：{self.base_url}\n{exc}", 0, 0) from exc
        except requests.Timeout as exc:
            raise APIError("请求超时，请检查网络", 0, 0) from exc
        except requests.RequestException as exc:
            raise APIError(f"请求失败：{exc}", 0, 0) from exc

        try:
            body = resp.json()
        except Exception:
            body = None

        if not resp.ok:
            if isinstance(body, dict):
                message = body.get("message") or body.get("msg") or f"HTTP {resp.status_code}"
                code = int(body.get("code") or resp.status_code)
            else:
                message = resp.text.strip() or f"HTTP {resp.status_code}"
                code = resp.status_code
            raise APIError(message, code, resp.status_code)

        if isinstance(body, dict):
            code = body.get("code", 200)
            if code not in (0, 200, None):
                raise APIError(body.get("message") or body.get("msg") or "业务错误", int(code), resp.status_code)
            if "data" in body:
                return body.get("data")
            return body

        return body

    def get(self, path: str, auth: bool = True, **kwargs):
        return self._request("GET", path, auth=auth, **kwargs)

    def post(self, path: str, auth: bool = True, json_data=None, **kwargs):
        if json_data is not None:
            kwargs["json"] = json_data
        return self._request("POST", path, auth=auth, **kwargs)

    def put(self, path: str, auth: bool = True, json_data=None, **kwargs):
        if json_data is not None:
            kwargs["json"] = json_data
        return self._request("PUT", path, auth=auth, **kwargs)

    def patch(self, path: str, auth: bool = True, json_data=None, **kwargs):
        if json_data is not None:
            kwargs["json"] = json_data
        return self._request("PATCH", path, auth=auth, **kwargs)

    def delete(self, path: str, auth: bool = True, **kwargs):
        return self._request("DELETE", path, auth=auth, **kwargs)

    # ──────────────────────────── Auth ────────────────────────────

    def login(self, email: str, password: str) -> dict[str, Any]:
        data = self.post("/api/auth/login", auth=False, json_data={"email": email, "password": password}) or {}
        token = data.get("token")
        user = data.get("userInfo") or data.get("user") or {}
        if token:
            self.save_session(token, user)
        return data

    def register(self, email: str, code: str, password: str) -> dict[str, Any]:
        data = self.post(
            "/api/auth/register",
            auth=False,
            json_data={"email": email, "emailVerificationCode": code, "password": password},
        ) or {}
        token = data.get("token")
        user = data.get("userInfo") or data.get("user") or {}
        if token:
            self.save_session(token, user)
        return data

    def send_register_code(self, email: str) -> None:
        self.post("/api/auth/register/email-code", auth=False, json_data={"email": email})

    def logout(self) -> None:
        if self.token:
            try:
                self.post("/api/auth/logout")
            except APIError:
                pass
            except Exception:
                pass
        self.clear_session()

    # ──────────────────────────── User ────────────────────────────

    def get_me(self) -> dict[str, Any]:
        return self.get("/api/user")

    def get_user(self, user_id: str) -> dict[str, Any]:
        return self.get(f"/api/user/{user_id}")

    def update_profile(self, **kwargs) -> dict[str, Any]:
        return self.put("/api/user/profile", json_data=kwargs)

    # ──────────────────────────── Session ────────────────────────────

    def list_active_sessions(self) -> list[dict[str, Any]]:
        data = self.get("/api/user/sessions/active")
        return data if isinstance(data, list) else []

    def remove_active_session(self, ip: str) -> Any:
        return self.delete(f"/api/user/sessions/active/{ip}")

    def remove_other_sessions(self) -> list[str]:
        sessions = self.list_active_sessions()
        removed: list[str] = []
        for session in sessions:
            is_current = bool(session.get("current") or session.get("isCurrent"))
            if not is_current:
                ip = session.get("ip")
                if ip:
                    self.remove_active_session(ip)
                    removed.append(ip)
        return removed

    # ──────────────────────────── Notifications ────────────────────────────

    def list_notifications(self, page: int = 1, size: int = 20) -> dict[str, Any]:
        data = self.get("/api/user/notifications", params={"pageNum": page, "pageSize": size})
        return data if isinstance(data, dict) else {"records": data or []}

    def get_unread_count(self) -> dict[str, Any]:
        data = self.get("/api/user/notifications/unread-count")
        return data if isinstance(data, dict) else {"unreadCount": data}

    def mark_notification_read(self, notification_id: str) -> Any:
        return self.put(f"/api/user/notifications/{notification_id}/read")

    def mark_all_notifications_read(self) -> Any:
        return self.put("/api/user/notifications/read-all")

    def mark_all_read(self) -> Any:
        return self.mark_all_notifications_read()

    # ──────────────────────────── Posts ────────────────────────────

    def list_posts(
        self,
        page: int = 1,
        size: int = 10,
        category_type: Optional[str] = None,
        **kwargs,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"pageNum": page, "pageSize": size}
        if category_type:
            body["categoryType"] = category_type
        body.update(kwargs)
        data = self.post("/api/app/posts/queries", json_data=body)
        return data if isinstance(data, dict) else {"records": data or []}

    def get_post(self, post_id: str) -> dict[str, Any]:
        return self.get(f"/api/app/posts/{post_id}")

    def list_my_posts(self, page: int = 1, size: int = 10, status: Optional[str] = None) -> dict[str, Any]:
        params: dict[str, Any] = {"pageNum": page, "pageSize": size}
        if status:
            params["status"] = status
        data = self.get("/api/user/posts", params=params)
        return data if isinstance(data, dict) else {"records": data or []}

    def create_post(
        self,
        title: str,
        content: str,
        category_id: str,
        summary: Optional[str] = None,
        cover_image: Optional[str] = None,
        tags: Optional[list[str]] = None,
        post_type: str = "ARTICLE",
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "title": title,
            "content": content,
            "categoryId": category_id,
        }
        if summary is not None:
            payload["summary"] = summary
        if cover_image is not None:
            payload["coverImage"] = cover_image
        if tags is not None:
            payload["tags"] = tags
        data = self.post("/api/user/posts", json_data=payload)
        return data if isinstance(data, dict) else {}

    def update_post(self, post_id: str, **kwargs) -> dict[str, Any]:
        payload = dict(kwargs)
        if "cover_image" in payload and "coverImage" not in payload:
            payload["coverImage"] = payload.pop("cover_image")
        if "category_id" in payload and "categoryId" not in payload:
            payload["categoryId"] = payload.pop("category_id")
        if "tags" in payload and payload["tags"] is None:
            payload.pop("tags")
        data = self.put(f"/api/user/posts/{post_id}", json_data=payload)
        return data if isinstance(data, dict) else {}

    def update_post_status(self, post_id: str, status: str) -> dict[str, Any]:
        data = self.patch(f"/api/user/posts/{post_id}/status", json_data={"status": status})
        return data if isinstance(data, dict) else {}

    def publish_post(self, post_id: str) -> dict[str, Any]:
        return self.update_post_status(post_id, "PUBLISHED")

    def draft_post(self, post_id: str) -> dict[str, Any]:
        return self.update_post_status(post_id, "DRAFT")

    def delete_post(self, post_id: str) -> Any:
        return self.delete(f"/api/user/posts/{post_id}")

    def list_user_posts(self, user_id: str, page: int = 1, size: int = 10) -> dict[str, Any]:
        data = self.post(
            f"/api/app/posts/user/{user_id}/queries",
            json_data={"pageNum": page, "pageSize": size},
        )
        return data if isinstance(data, dict) else {"records": data or []}

    # ──────────────────────────── Comments ────────────────────────────

    def list_comments(self, business_id: str, business_type: str = "POST", page: int = 1, size: int = 10) -> dict[str, Any]:
        data = self.get(
            "/api/app/comments",
            params={
                "businessId": business_id,
                "businessType": business_type,
                "pageNum": page,
                "pageSize": size,
            },
        )
        return data if isinstance(data, dict) else {"records": data or []}

    def create_comment(
        self,
        business_id: str,
        content: str,
        business_type: str = "POST",
        parent_comment_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        reply_user_id: Optional[str] = None,
    ) -> dict[str, Any]:
        parent_comment_id = parent_comment_id or parent_id
        if parent_comment_id:
            return self.reply_comment(
                parent_comment_id,
                business_id=business_id,
                business_type=business_type,
                content=content,
                reply_user_id=reply_user_id,
            )
        data = self.post(
            "/api/user/comments",
            json_data={
                "businessId": business_id,
                "content": content,
                "businessType": business_type,
            },
        )
        return data if isinstance(data, dict) else {}

    def reply_comment(
        self,
        comment_id: str,
        business_id: str,
        business_type: str,
        content: str,
        reply_user_id: Optional[str] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "parentCommentId": comment_id,
            "businessId": business_id,
            "businessType": business_type,
            "content": content,
        }
        if reply_user_id is not None:
            payload["replyUserId"] = reply_user_id
        data = self.post(f"/api/user/comments/{comment_id}/reply", json_data=payload)
        return data if isinstance(data, dict) else {}

    def delete_comment(self, comment_id: str) -> Any:
        return self.delete(f"/api/user/comments/{comment_id}")

    def get_related_comments(self, page: int = 1, size: int = 10) -> dict[str, Any]:
        data = self.get("/api/user/comments/related", params={"pageNum": page, "pageSize": size})
        return data if isinstance(data, dict) else {"records": data or []}

    def get_latest_comments(self, size: Optional[int] = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if size is not None:
            params["size"] = size
        data = self.get("/api/user/comments/latest", params=params)
        return data if isinstance(data, list) else []

    # ──────────────────────────── Reactions ────────────────────────────

    def toggle_like(self, target_id: str, target_type: str = "POST") -> dict[str, Any]:
        data = self.post(
            "/api/likes/toggle",
            json_data={
                "targetId": target_id,
                "targetType": target_type,
            },
        )
        if isinstance(data, dict):
            result = dict(data)
        else:
            result = {}
        is_liked = bool(result.get("isLiked"))
        result.setdefault("liked", is_liked)
        result.setdefault("status", is_liked)
        return result

    def get_like_status(self, target_id: str, target_type: str = "POST") -> dict[str, Any]:
        status = self.get(f"/api/likes/status/{target_type}/{target_id}")
        count = self.get(f"/api/likes/count/{target_type}/{target_id}")
        status_data = dict(status) if isinstance(status, dict) else {}
        count_data = dict(count) if isinstance(count, dict) else {}
        liked = bool(status_data.get("isLiked"))
        like_count = int(count_data.get("count") or status_data.get("likeCount") or 0)
        return {
            "liked": liked,
            "isLiked": liked,
            "count": like_count,
            "likeCount": like_count,
        }

    # ──────────────────────────── Favorites ────────────────────────────

    def toggle_favorite(self, target_id: str, target_type: str = "POST") -> dict[str, Any]:
        data = self.post(
            "/api/favorites/toggle",
            json_data={"targetId": target_id, "targetType": target_type},
        )
        result = dict(data) if isinstance(data, dict) else {}
        is_favorited = bool(result.get("isFavorited"))
        result.setdefault("favorited", is_favorited)
        result.setdefault("status", is_favorited)
        return result

    def get_favorite_status(self, target_id: str, target_type: str = "POST") -> dict[str, Any]:
        data = self.get(f"/api/favorites/status/{target_type}/{target_id}")
        result = dict(data) if isinstance(data, dict) else {}
        result.setdefault("favorited", bool(result.get("isFavorited")))
        result.setdefault("count", result.get("favoriteCount", 0))
        return result

    def list_my_favorites(self, page: int = 1, size: int = 10, target_type: Optional[str] = None) -> dict[str, Any]:
        params: dict[str, Any] = {"pageNum": page, "pageSize": size}
        if target_type:
            params["targetType"] = target_type
        data = self.get("/api/favorites/my", params=params)
        return data if isinstance(data, dict) else {"records": data or []}

    # ──────────────────────────── Follows ────────────────────────────

    def toggle_follow(self, target_id: str, target_type: str = "USER") -> dict[str, Any]:
        data = self.post(
            "/api/app/follows/toggle",
            json_data={"targetId": target_id, "targetType": target_type},
        )
        result = dict(data) if isinstance(data, dict) else {}
        is_following = bool(result.get("isFollowing"))
        result.setdefault("followed", is_following)
        result.setdefault("status", is_following)
        return result

    def check_follow_status(self, target_id: str, target_type: str = "USER") -> dict[str, Any]:
        data = self.get(f"/api/app/follows/check/{target_type}/{target_id}")
        return dict(data) if isinstance(data, dict) else {"isFollowing": bool(data)}

    def check_follow(self, target_id: str, target_type: str = "USER") -> dict[str, Any]:
        return self.check_follow_status(target_id, target_type)

    def list_my_follows(
        self,
        page: int = 1,
        size: int = 10,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"pageNum": page, "pageSize": size}
        if target_type:
            params["targetType"] = target_type
        if target_id:
            params["targetId"] = target_id
        data = self.get("/api/user/follows", params=params)
        return data if isinstance(data, dict) else {"records": data or []}

    # ──────────────────────────── Categories ────────────────────────────

    def get_categories(self, category_type: Optional[str] = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if category_type:
            params["type"] = category_type
        data = self.get("/api/app/categories/tree", params=params)
        return data if isinstance(data, list) else []

    # ──────────────────────────── Courses ────────────────────────────

    def list_courses(
        self,
        page: int = 1,
        size: int = 10,
        keyword: Optional[str] = None,
        tech_stack: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"pageNum": page, "pageSize": size}
        if keyword:
            body["keyword"] = keyword
        if tech_stack:
            body["techStack"] = tech_stack
        if tags is not None:
            body["tags"] = tags
        data = self.post("/api/app/courses/queries", json_data=body)
        return data if isinstance(data, dict) else {"records": data or []}

    def get_course(self, course_id: str) -> dict[str, Any]:
        data = self.get(f"/api/app/courses/{course_id}")
        return data if isinstance(data, dict) else {}

    def get_chapter(self, chapter_id: str) -> dict[str, Any]:
        data = self.get(f"/api/app/chapters/{chapter_id}")
        return data if isinstance(data, dict) else {}

    def list_latest_chapters(self) -> list[dict[str, Any]]:
        data = self.get("/api/app/chapters/latest")
        return data if isinstance(data, list) else []

    # ──────────────────────────── Learning ────────────────────────────

    def get_learning_progress(self, course_id: str) -> dict[str, Any]:
        data = self.get(f"/api/user/learning/progress/{course_id}")
        return data if isinstance(data, dict) else {}

    def list_learning_records(self, page: int = 1, size: int = 10) -> dict[str, Any]:
        data = self.get("/api/user/learning/records", params={"pageNum": page, "pageSize": size})
        return data if isinstance(data, dict) else {"records": data or []}

    def report_learning_progress(
        self,
        course_id: str,
        chapter_id: str,
        progress_percent: int,
        position_sec: Optional[int] = None,
        time_spent_delta_sec: Optional[int] = None,
        study_duration_seconds: Optional[int] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "courseId": course_id,
            "chapterId": chapter_id,
            "progressPercent": progress_percent,
        }
        if position_sec is not None:
            payload["positionSec"] = position_sec

        effective_duration = time_spent_delta_sec if time_spent_delta_sec is not None else study_duration_seconds
        if effective_duration is not None:
            payload["timeSpentDeltaSec"] = effective_duration
        if study_duration_seconds is not None:
            payload["studyDurationSeconds"] = study_duration_seconds

        data = self.post("/api/user/learning/progress/report", json_data=payload)
        return data if isinstance(data, dict) else {}

    # ──────────────────────────── Subscription ────────────────────────────

    def activate_cdk(self, cdk_code: str) -> Any:
        return self.post("/api/user/subscription/activate-cdk", json_data={"cdkCode": cdk_code})

    # ──────────────────────────── Compatibility aliases ────────────────────────────

    def mark_all_notifications_read_alias(self) -> Any:
        return self.mark_all_notifications_read()
