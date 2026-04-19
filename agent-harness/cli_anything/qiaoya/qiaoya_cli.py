"""
敲鸭社区 CLI (cli-anything-qiaoya)

与 https://code.xhyovo.cn/ API 交互的命令行工具。
"""
import importlib.util
import json
import shlex
import sys
import uuid
from pathlib import Path
from typing import Any, Optional

import click

from cli_anything.qiaoya.utils.api_client import APIError, QiaoyaClient, SESSION_FILE
from cli_anything.qiaoya.utils import output as out

_FORMATTERS_PATH = Path(__file__).with_name("core") / "formatters.py"
_FORMATTERS_SPEC = importlib.util.spec_from_file_location(
    "cli_anything.qiaoya._formatters",
    _FORMATTERS_PATH,
)
assert _FORMATTERS_SPEC is not None and _FORMATTERS_SPEC.loader is not None
_FORMATTERS = importlib.util.module_from_spec(_FORMATTERS_SPEC)
_FORMATTERS_SPEC.loader.exec_module(_FORMATTERS)

DEVICE_HEADER = "X-Device-ID"

pass_client = click.make_pass_decorator(QiaoyaClient, ensure=True)


def _json_mode(ctx: click.Context) -> bool:
    root = ctx.find_root()
    if root is not None:
        return bool(root.meta.get("json_mode"))
    return False


def _client(ctx: click.Context) -> QiaoyaClient:
    client = ctx.find_object(QiaoyaClient)
    if client is None:
        raise RuntimeError("QiaoyaClient 未初始化")
    return client


def _fail(ctx: click.Context, message: str, code: int = 1):
    out.error(message, _json_mode(ctx))
    raise SystemExit(code)


def _load_session_payload() -> dict[str, Any]:
    if not SESSION_FILE.exists():
        return {}
    try:
        data = json.loads(SESSION_FILE.read_text())
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_session_payload(payload: dict[str, Any]):
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    SESSION_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def _sync_client_session(client: QiaoyaClient):
    if client.token:
        client.session.headers["Authorization"] = f"Bearer {client.token}"

    payload = _load_session_payload()
    device_id = payload.get("device_id")

    if device_id:
        client.session.headers[DEVICE_HEADER] = device_id
        return

    if SESSION_FILE.exists():
        device_id = uuid.uuid4().hex
        payload["device_id"] = device_id
        payload["base_url"] = payload.get("base_url") or client.base_url
        if client.token and not payload.get("token"):
            payload["token"] = client.token
        _write_session_payload(payload)
        client.session.headers[DEVICE_HEADER] = device_id
        return

    if client.token:
        client.session.headers[DEVICE_HEADER] = uuid.uuid4().hex


def _persist_login_session(client: QiaoyaClient, data: dict[str, Any]):
    user = data.get("userInfo") or data.get("user") or {}
    payload = {
        "base_url": client.base_url,
        "token": data.get("token"),
        "user": user,
        "device_id": _load_session_payload().get("device_id") or uuid.uuid4().hex,
    }
    _write_session_payload(payload)
    client.token = payload["token"]
    client.session.headers["Authorization"] = f"Bearer {payload['token']}"
    client.session.headers[DEVICE_HEADER] = payload["device_id"]


def _require_login(ctx: click.Context):
    client = _client(ctx)
    if not client.token:
        _fail(ctx, "未登录，请使用 auth login 登录")


def _call_if_exists(client: Any, names: list[str], *args, **kwargs):
    for name in names:
        fn = getattr(client, name, None)
        if callable(fn):
            return fn(*args, **kwargs)
    raise AttributeError(f"客户端缺少方法：{', '.join(names)}")


def _request_patch(client: Any, path: str, json_data: Optional[dict[str, Any]] = None):
    if hasattr(client, "_request"):
        kwargs: dict[str, Any] = {}
        if json_data is not None:
            kwargs["json"] = json_data
        return client._request("PATCH", path, **kwargs)
    headers = {}
    if getattr(client, "token", None):
        headers["Authorization"] = f"Bearer {client.token}"
    return client.session.request("PATCH", f"{client.base_url}{path}", headers=headers, json=json_data, timeout=30)


def _unwrap_page_data(data: Any):
    if isinstance(data, dict) and "records" in data:
        return data.get("records") or [], data
    if isinstance(data, list):
        return data, None
    return [], None


def _print_page_info(page_data: Any):
    if isinstance(page_data, dict):
        print(out.page_info(page_data))


def _print_session_rows(sessions: list[dict[str, Any]]):
    rows = []
    for item in sessions:
        rows.append([
            _FORMATTERS.short_id(item.get("ip"), 18),
            _FORMATTERS.format_time(item.get("lastSeenTime")),
            "当前" if item.get("isCurrent") else "",
        ])
    out.print_table(["IP", "最后活跃", "标记"], rows)


def _print_notification_rows(items: list[dict[str, Any]]):
    rows = []
    for item in items:
        rows.append([
            _FORMATTERS.short_id(item.get("id")),
            _FORMATTERS.text_or_dash(item.get("type")),
            _FORMATTERS.text_or_dash(item.get("status")),
            _FORMATTERS.compact_text(item.get("title") or item.get("content"), 32),
            _FORMATTERS.format_time(item.get("createTime")),
        ])
    out.print_table(["ID", "类型", "状态", "标题/内容", "时间"], rows)


def _print_post_rows(items: list[dict[str, Any]]):
    rows = []
    for item in items:
        rows.append([
            _FORMATTERS.short_id(item.get("id")),
            _FORMATTERS.compact_text(item.get("title"), 28),
            _FORMATTERS.text_or_dash(item.get("authorName") or item.get("author", {}).get("username")),
            _FORMATTERS.text_or_dash(item.get("status")),
            item.get("likeCount", 0),
            item.get("commentCount", 0),
            _FORMATTERS.format_time(item.get("createTime")),
        ])
    out.print_table(["ID", "标题", "作者", "状态", "点赞", "评论", "时间"], rows)


def _print_comment_rows(items: list[dict[str, Any]]):
    rows = []
    for item in items:
        rows.append([
            _FORMATTERS.short_id(item.get("id")),
            _FORMATTERS.text_or_dash(item.get("commentUserName") or item.get("authorName")),
            _FORMATTERS.text_or_dash(item.get("businessTypeName") or item.get("businessType")),
            _FORMATTERS.compact_text(item.get("content"), 30),
            _FORMATTERS.format_time(item.get("createTime")),
        ])
    out.print_table(["ID", "用户", "类型", "内容", "时间"], rows)


def _print_favorite_rows(items: list[dict[str, Any]]):
    rows = []
    for item in items:
        rows.append([
            _FORMATTERS.short_id(item.get("targetId") or item.get("id")),
            _FORMATTERS.text_or_dash(item.get("targetType")),
            _FORMATTERS.compact_text(item.get("title"), 28),
            _FORMATTERS.format_time(item.get("createTime")),
        ])
    out.print_table(["ID", "类型", "标题", "时间"], rows)


def _print_follow_rows(items: list[dict[str, Any]]):
    rows = []
    for item in items:
        rows.append([
            _FORMATTERS.short_id(item.get("targetId") or item.get("id")),
            _FORMATTERS.text_or_dash(item.get("targetType")),
            _FORMATTERS.compact_text(item.get("targetName") or item.get("title"), 28),
            _FORMATTERS.format_time(item.get("createTime")),
        ])
    out.print_table(["ID", "类型", "目标", "时间"], rows)


def _print_course_rows(items: list[dict[str, Any]]):
    rows = []
    for item in items:
        rows.append([
            _FORMATTERS.short_id(item.get("id")),
            _FORMATTERS.compact_text(item.get("title"), 28),
            _FORMATTERS.text_or_dash(item.get("authorName") or item.get("teacherName")),
            item.get("chapterCount", len(item.get("chapters", []) or [])),
            _FORMATTERS.format_time(item.get("createTime")),
        ])
    out.print_table(["ID", "标题", "讲师", "章节", "时间"], rows)


def _print_chapter_rows(items: list[dict[str, Any]]):
    rows = []
    for item in items:
        rows.append([
            _FORMATTERS.short_id(item.get("id")),
            _FORMATTERS.compact_text(item.get("title"), 28),
            _FORMATTERS.compact_text(item.get("courseName"), 24),
            item.get("sortOrder", "-"),
            item.get("readingTime", "-"),
            _FORMATTERS.format_time(item.get("createTime")),
        ])
    out.print_table(["ID", "标题", "课程", "排序", "时长", "时间"], rows)


def _print_learning_rows(items: list[dict[str, Any]]):
    rows = []
    for item in items:
        rows.append([
            _FORMATTERS.short_id(item.get("courseId")),
            _FORMATTERS.compact_text(item.get("courseTitle") or item.get("title"), 28),
            f"{item.get('progressPercent', 0)}%",
            f"{item.get('completedChapters', 0)}/{item.get('totalChapters', 0)}",
            _FORMATTERS.compact_text(item.get("lastAccessChapterTitle") or item.get("lastAccessChapterId"), 24),
            _FORMATTERS.format_time(item.get("lastAccessTime")),
        ])
    out.print_table(["课程ID", "课程", "进度", "完成", "最后章节", "最后访问"], rows)


def _print_category_tree(nodes: list[dict[str, Any]], indent: int = 0):
    for node in nodes:
        prefix = "  " * indent + ("└─ " if indent else "")
        print(f"{prefix}[{_FORMATTERS.short_id(node.get('id'))}] {_FORMATTERS.text_or_dash(node.get('name'))}")
        children = node.get("children") or []
        if children:
            _print_category_tree(children, indent + 1)


def _print_user_card(user: dict[str, Any]):
    out.print_kv([
        ("用户名", _FORMATTERS.text_or_dash(user.get("username") or user.get("name"))),
        ("邮箱", _FORMATTERS.text_or_dash(user.get("email"))),
        ("ID", _FORMATTERS.text_or_dash(user.get("id"))),
        ("简介", _FORMATTERS.text_or_dash(user.get("bio"))),
    ])


def _print_post_detail(post: dict[str, Any]):
    out.print_kv([
        ("标题", _FORMATTERS.text_or_dash(post.get("title"))),
        ("作者", _FORMATTERS.text_or_dash(post.get("authorName"))),
        ("分类", _FORMATTERS.text_or_dash(post.get("categoryName"))),
        ("状态", _FORMATTERS.text_or_dash(post.get("status"))),
        ("点赞", post.get("likeCount", 0)),
        ("评论", post.get("commentCount", 0)),
        ("发布时间", _FORMATTERS.format_time(post.get("createTime"))),
        ("更新时间", _FORMATTERS.format_time(post.get("updateTime"))),
        ("摘要", _FORMATTERS.compact_text(post.get("summary"), 100)),
    ])
    content = _FORMATTERS.text_or_dash(post.get("content"))
    print()
    print(content[:500])


def _print_course_detail(course: dict[str, Any]):
    out.print_kv([
        ("标题", _FORMATTERS.text_or_dash(course.get("title"))),
        ("讲师", _FORMATTERS.text_or_dash(course.get("authorName"))),
        ("评分", course.get("rating", "-")),
        ("状态", _FORMATTERS.text_or_dash(course.get("status"))),
        ("章节数", len(course.get("chapters", []) or [])),
        ("总阅读时长", course.get("totalReadingTime", "-")),
        ("是否解锁", _FORMATTERS.yes_no(course.get("unlocked"))),
        ("发布时间", _FORMATTERS.format_time(course.get("createTime"))),
    ])
    print()
    print(_FORMATTERS.compact_text(course.get("description"), 300))


def _print_chapter_detail(chapter: dict[str, Any]):
    out.print_kv([
        ("标题", _FORMATTERS.text_or_dash(chapter.get("title"))),
        ("课程", _FORMATTERS.text_or_dash(chapter.get("courseName"))),
        ("排序", chapter.get("sortOrder", "-")),
        ("阅读时长", chapter.get("readingTime", "-")),
        ("点赞", chapter.get("likeCount", "-")),
        ("内容类型", _FORMATTERS.text_or_dash(chapter.get("contentType"))),
        ("发布时间", _FORMATTERS.format_time(chapter.get("createTime"))),
    ])
    print()
    print(_FORMATTERS.compact_text(chapter.get("content"), 300))


def _print_learning_progress(progress: dict[str, Any]):
    out.print_kv([
        ("课程ID", _FORMATTERS.text_or_dash(progress.get("courseId"))),
        ("总章节", progress.get("totalChapters", 0)),
        ("已完成", progress.get("completedChapters", 0)),
        ("进度", f"{progress.get('progressPercent', 0)}%"),
        ("最后章节", _FORMATTERS.text_or_dash(progress.get("lastAccessChapterId"))),
        ("最后访问", _FORMATTERS.format_time(progress.get("lastAccessTime"))),
        ("完成状态", _FORMATTERS.yes_no(progress.get("completed"))),
        ("完成时间", _FORMATTERS.format_time(progress.get("completedAt"))),
    ])


def _maybe_json(ctx: click.Context, data: Any, rows_printer=None, headers=None):
    jm = _json_mode(ctx)
    if jm:
        out.print_json(data)
        return
    if rows_printer is not None:
        rows_printer(data)
        return
    if headers is not None and isinstance(data, list):
        out.print_table(headers, data)


@click.group(invoke_without_command=True)
@click.option("--base-url", envvar="QIAOYA_BASE_URL", default=None, help="API 地址，默认 https://code.xhyovo.cn")
@click.option("--token", envvar="QIAOYA_TOKEN", default=None, help="Bearer Token（可选）")
@click.option("--json", "json_mode", is_flag=True, help="以 JSON 格式输出结果")
@click.pass_context
def cli(ctx: click.Context, base_url: Optional[str], token: Optional[str], json_mode: bool):
    """敲鸭社区 CLI — 与 https://code.xhyovo.cn/ 交互"""
    inherited_json = json_mode
    if ctx.parent is not None:
        inherited_json = bool(ctx.parent.meta.get("json_mode", json_mode))

    ctx.meta["json_mode"] = inherited_json
    client = ctx.find_object(QiaoyaClient)
    if client is None:
        client = QiaoyaClient(base_url=base_url, token=token)
    ctx.obj = client
    _sync_client_session(client)

    if ctx.invoked_subcommand is None:
        from cli_anything.qiaoya.utils.repl_skin import ReplSkin

        skin = ReplSkin("qiaoya", version="1.0.0")
        skin.print_banner()
        _run_repl(ctx, client, skin)


def _run_repl(ctx: click.Context, client: QiaoyaClient, skin):
    pt_session = skin.create_prompt_session()

    while True:
        try:
            session_user = client.load_session_user()
            prompt_name = (session_user or {}).get("username") or (session_user or {}).get("email", "") or "guest"
            line = skin.get_input(pt_session, project_name=prompt_name)
        except (EOFError, KeyboardInterrupt):
            skin.print_goodbye()
            break

        line = line.strip()
        if not line:
            continue
        if line.lower() in ("exit", "quit", "q"):
            skin.print_goodbye()
            break

        try:
            args = shlex.split(line)
        except ValueError as exc:
            skin.error(str(exc))
            continue

        try:
            line_ctx = cli.make_context("cli-anything-qiaoya", args, parent=ctx, resilient_parsing=False)
            with line_ctx:
                cli.invoke(line_ctx)
        except click.exceptions.UsageError as exc:
            skin.error(str(exc))
        except SystemExit:
            pass
        except Exception as exc:
            skin.error(str(exc))


@cli.group()
def auth():
    """用户认证：登录、退出、状态"""


@auth.command("login")
@click.option("-e", "--email", required=True, prompt=True, help="邮箱地址")
@click.option("-p", "--password", required=True, prompt=True, hide_input=True, help="密码")
@click.pass_context
def auth_login(ctx: click.Context, email: str, password: str):
    client = _client(ctx)
    try:
        data = client.login(email, password)
        _persist_login_session(client, data)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            user = data.get("userInfo") or data.get("user") or {}
            out.success(f"登录成功，欢迎 {_FORMATTERS.text_or_dash(user.get('username') or email)}")
    except APIError as exc:
        _fail(ctx, str(exc))


@auth.command("logout")
@click.pass_context
def auth_logout(ctx: click.Context):
    client = _client(ctx)
    try:
        client.logout()
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()
        client.token = None
        client.session.headers.pop("Authorization", None)
        client.session.headers.pop(DEVICE_HEADER, None)
        if _json_mode(ctx):
            out.print_json({"success": True, "message": "已退出登录"})
        else:
            out.success("已退出登录")
    except Exception as exc:
        _fail(ctx, str(exc))


@auth.command("status")
@click.pass_context
def auth_status(ctx: click.Context):
    client = _client(ctx)
    if not client.token:
        _fail(ctx, "未登录，请使用 auth login 登录")
    try:
        me = client.get_me()
        if _json_mode(ctx):
            out.print_json(me)
        else:
            _print_user_card(me)
    except APIError as exc:
        _fail(ctx, str(exc))


@cli.group()
def user():
    """用户信息"""


@user.command("me")
@click.pass_context
def user_me(ctx: click.Context):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.get_me()
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_user_card(data)
    except APIError as exc:
        _fail(ctx, str(exc))


@user.command("get")
@click.argument("user_id")
@click.pass_context
def user_get(ctx: click.Context, user_id: str):
    client = _client(ctx)
    try:
        data = client.get_user(user_id)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_user_card(data)
    except APIError as exc:
        _fail(ctx, str(exc))


@cli.group()
def session():
    """会话管理"""


@session.command("list")
@click.pass_context
def session_list(ctx: click.Context):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = _call_if_exists(client, ["list_active_sessions"],)  # type: ignore[arg-type]
    except AttributeError:
        try:
            data = client.get("/api/user/sessions/active")
        except APIError as exc:
            _fail(ctx, str(exc))
            return
    except APIError as exc:
        _fail(ctx, str(exc))
        return

    if _json_mode(ctx):
        out.print_json(data)
    else:
        _print_session_rows(data or [])


@session.command("remove")
@click.argument("ip")
@click.option("--yes", "-y", is_flag=True, help="跳过确认")
@click.pass_context
def session_remove(ctx: click.Context, ip: str, yes: bool):
    _require_login(ctx)
    client = _client(ctx)
    if not yes and not _json_mode(ctx):
        click.confirm(f"确认下线会话 {ip}？", abort=True)
    try:
        try:
            _call_if_exists(client, ["remove_active_session"], ip)
        except AttributeError:
            client.delete(f"/api/user/sessions/active/{ip}")
        if _json_mode(ctx):
            out.print_json({"success": True, "removedIp": ip})
        else:
            out.success(f"会话 {ip} 已下线")
    except APIError as exc:
        _fail(ctx, str(exc))


@session.command("remove-others")
@click.option("--yes", "-y", is_flag=True, help="跳过确认")
@click.pass_context
def session_remove_others(ctx: click.Context, yes: bool):
    _require_login(ctx)
    client = _client(ctx)
    if not yes and not _json_mode(ctx):
        click.confirm("确认下线所有非当前设备会话？", abort=True)
    try:
        try:
            result = _call_if_exists(client, ["remove_other_sessions"])
        except AttributeError:
            try:
                sessions = _call_if_exists(client, ["list_active_sessions"])
            except AttributeError:
                sessions = client.get("/api/user/sessions/active")
            if sessions is None:
                sessions = client.get("/api/user/sessions/active")
            removed = []
            for item in sessions or []:
                if not item.get("isCurrent"):
                    try:
                        _call_if_exists(client, ["remove_active_session"], item.get("ip"))
                    except AttributeError:
                        client.delete(f"/api/user/sessions/active/{item.get('ip')}")
                    removed.append(item.get("ip"))
            result = {"removedIps": removed, "count": len(removed)}
        if isinstance(result, list):
            result = {"removedIps": result, "count": len(result)}
        if _json_mode(ctx):
            if isinstance(result, dict):
                out.print_json(result)
            else:
                out.print_json({"success": True})
        else:
            count = len(result.get("removedIps", [])) if isinstance(result, dict) else 0
            out.success(f"已下线 {count} 个其他会话")
    except APIError as exc:
        _fail(ctx, str(exc))


@cli.group()
def notification():
    """消息通知"""


@notification.command("list")
@click.option("--page", default=1, show_default=True)
@click.option("--size", default=20, show_default=True)
@click.pass_context
def notification_list(ctx: click.Context, page: int, size: int):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.list_notifications(page, size)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            records = (data or {}).get("records", [])
            _print_page_info(data)
            _print_notification_rows(records)
    except APIError as exc:
        _fail(ctx, str(exc))


@notification.command("unread")
@click.pass_context
def notification_unread(ctx: click.Context):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.get_unread_count()
        if _json_mode(ctx):
            out.print_json(data)
        else:
            count = data.get("unreadCount", data.get("count", 0))
            print(f"未读消息：{count}")
    except APIError as exc:
        _fail(ctx, str(exc))


@notification.command("read")
@click.argument("notification_id")
@click.pass_context
def notification_read(ctx: click.Context, notification_id: str):
    _require_login(ctx)
    client = _client(ctx)
    try:
        try:
            _call_if_exists(client, ["mark_notification_read"], notification_id)
        except AttributeError:
            client.put(f"/api/user/notifications/{notification_id}/read")
        if _json_mode(ctx):
            out.print_json({"success": True, "notificationId": notification_id})
        else:
            out.success(f"消息 {notification_id} 已标记为已读")
    except APIError as exc:
        _fail(ctx, str(exc))


@notification.command("read-all")
@click.pass_context
def notification_read_all(ctx: click.Context):
    _require_login(ctx)
    client = _client(ctx)
    try:
        try:
            _call_if_exists(client, ["mark_all_notifications_read", "mark_all_read"])
        except AttributeError:
            client.put("/api/user/notifications/read-all")
        if _json_mode(ctx):
            out.print_json({"success": True, "message": "所有消息已标记为已读"})
        else:
            out.success("所有消息已标记为已读")
    except APIError as exc:
        _fail(ctx, str(exc))


@cli.group()
def category():
    """分类树"""


@category.command("list")
@click.option("--type", "category_type", default=None, type=click.Choice(["ARTICLE", "QA"], case_sensitive=False))
@click.pass_context
def category_list(ctx: click.Context, category_type: Optional[str]):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.get_categories(category_type)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_category_tree(data or [])
    except APIError as exc:
        _fail(ctx, str(exc))


@cli.group()
def post():
    """帖子管理"""


@post.command("list")
@click.option("--page", default=1, show_default=True)
@click.option("--size", default=10, show_default=True)
@click.option("--type", "category_type", default=None, type=click.Choice(["ARTICLE", "QA"], case_sensitive=False), help="分类类型过滤")
@click.pass_context
def post_list(ctx: click.Context, page: int, size: int, category_type: Optional[str]):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.list_posts(page, size, category_type)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            records = (data or {}).get("records", [])
            _print_page_info(data)
            _print_post_rows(records)
    except APIError as exc:
        _fail(ctx, str(exc))


@post.command("get")
@click.argument("post_id")
@click.pass_context
def post_get(ctx: click.Context, post_id: str):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.get_post(post_id)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_post_detail(data)
    except APIError as exc:
        _fail(ctx, str(exc))


@post.command("my")
@click.option("--page", default=1, show_default=True)
@click.option("--size", default=10, show_default=True)
@click.option("--status", default=None, help="草稿/已发布状态过滤")
@click.pass_context
def post_my(ctx: click.Context, page: int, size: int, status: Optional[str]):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.list_my_posts(page, size, status)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            records = (data or {}).get("records", [])
            _print_page_info(data)
            _print_post_rows(records)
    except APIError as exc:
        _fail(ctx, str(exc))


@post.command("create")
@click.option("-t", "--title", required=True, prompt=True, help="帖子标题")
@click.option("-c", "--content", required=True, prompt=True, help="帖子内容")
@click.option("--category-id", required=True, prompt=True, help="分类 ID")
@click.option("--summary", default=None, help="摘要")
@click.option("--cover-image", default=None, help="封面图片")
@click.option("--type", "post_type", default="ARTICLE", type=click.Choice(["ARTICLE", "QA"], case_sensitive=False), show_default=True)
@click.pass_context
def post_create(ctx: click.Context, title: str, content: str, category_id: str, summary: Optional[str], cover_image: Optional[str], post_type: str):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.create_post(title, content, category_id, summary, cover_image=cover_image, post_type=post_type)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            out.success(f"发布成功，帖子 ID：{data.get('id')}")
    except APIError as exc:
        _fail(ctx, str(exc))


@post.command("update")
@click.argument("post_id")
@click.option("--title", default=None)
@click.option("--content", default=None)
@click.option("--category-id", default=None)
@click.option("--summary", default=None)
@click.option("--cover-image", default=None)
@click.pass_context
def post_update(ctx: click.Context, post_id: str, title: Optional[str], content: Optional[str], category_id: Optional[str], summary: Optional[str], cover_image: Optional[str]):
    _require_login(ctx)
    client = _client(ctx)
    payload = {k: v for k, v in {
        "title": title,
        "content": content,
        "categoryId": category_id,
        "summary": summary,
        "coverImage": cover_image,
    }.items() if v is not None}
    if not payload:
        _fail(ctx, "至少提供一个更新字段")
    try:
        data = client.update_post(post_id, **payload)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            out.success(f"帖子 {post_id} 已更新")
    except APIError as exc:
        _fail(ctx, str(exc))


@post.command("publish")
@click.argument("post_id")
@click.pass_context
def post_publish(ctx: click.Context, post_id: str):
    _require_login(ctx)
    client = _client(ctx)
    try:
        try:
            data = _call_if_exists(client, ["update_post_status"], post_id, "PUBLISHED")
        except AttributeError:
            data = _request_patch(client, f"/api/user/posts/{post_id}/status", {"status": "PUBLISHED"})
        if _json_mode(ctx):
            out.print_json(data if data is not None else {"status": "PUBLISHED", "postId": post_id})
        else:
            out.success(f"帖子 {post_id} 已发布")
    except APIError as exc:
        _fail(ctx, str(exc))


@post.command("draft")
@click.argument("post_id")
@click.pass_context
def post_draft(ctx: click.Context, post_id: str):
    _require_login(ctx)
    client = _client(ctx)
    try:
        try:
            data = _call_if_exists(client, ["update_post_status"], post_id, "DRAFT")
        except AttributeError:
            data = _request_patch(client, f"/api/user/posts/{post_id}/status", {"status": "DRAFT"})
        if _json_mode(ctx):
            out.print_json(data if data is not None else {"status": "DRAFT", "postId": post_id})
        else:
            out.success(f"帖子 {post_id} 已设为草稿")
    except APIError as exc:
        _fail(ctx, str(exc))


@post.command("delete")
@click.argument("post_id")
@click.option("--yes", "-y", is_flag=True, help="跳过确认")
@click.pass_context
def post_delete(ctx: click.Context, post_id: str, yes: bool):
    _require_login(ctx)
    client = _client(ctx)
    if not yes and not _json_mode(ctx):
        click.confirm(f"确认删除帖子 {post_id}？", abort=True)
    try:
        client.delete_post(post_id)
        if _json_mode(ctx):
            out.print_json({"success": True, "postId": post_id})
        else:
            out.success(f"帖子 {post_id} 已删除")
    except APIError as exc:
        _fail(ctx, str(exc))


@cli.group()
def comment():
    """评论管理"""


@comment.command("list")
@click.argument("business_id")
@click.option("--type", "business_type", default="POST", type=click.Choice(["POST", "COURSE", "CHAPTER", "COMMENT"], case_sensitive=False), show_default=True)
@click.option("--page", default=1, show_default=True)
@click.option("--size", default=20, show_default=True)
@click.pass_context
def comment_list(ctx: click.Context, business_id: str, business_type: str, page: int, size: int):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.list_comments(business_id, business_type, page, size)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            records = (data or {}).get("records", [])
            _print_page_info(data)
            _print_comment_rows(records)
    except APIError as exc:
        _fail(ctx, str(exc))


@comment.command("create")
@click.argument("business_id")
@click.option("-c", "--content", required=True, prompt=True, help="评论内容")
@click.option("--type", "business_type", default="POST", type=click.Choice(["POST", "COURSE", "CHAPTER", "COMMENT"], case_sensitive=False), show_default=True)
@click.pass_context
def comment_create(ctx: click.Context, business_id: str, content: str, business_type: str):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.create_comment(business_id, content, business_type=business_type)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            out.success(f"评论成功，ID：{data.get('id')}")
    except APIError as exc:
        _fail(ctx, str(exc))


@comment.command("reply")
@click.argument("comment_id")
@click.option("--business-id", required=True, help="业务 ID")
@click.option("--type", "business_type", default="POST", type=click.Choice(["POST", "COURSE", "CHAPTER", "COMMENT"], case_sensitive=False), show_default=True)
@click.option("-c", "--content", required=True, prompt=True, help="回复内容")
@click.pass_context
def comment_reply(ctx: click.Context, comment_id: str, business_id: str, business_type: str, content: str):
    _require_login(ctx)
    client = _client(ctx)
    payload = {
        "parentCommentId": comment_id,
        "businessId": business_id,
        "businessType": business_type,
        "content": content,
    }
    try:
        try:
            data = _call_if_exists(client, ["reply_comment"], comment_id, business_id=business_id, business_type=business_type, content=content)
        except AttributeError:
            data = client.post(f"/api/user/comments/{comment_id}/reply", json_data=payload)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            out.success(f"回复成功，ID：{data.get('id')}")
    except APIError as exc:
        _fail(ctx, str(exc))


@comment.command("delete")
@click.argument("comment_id")
@click.option("--yes", "-y", is_flag=True, help="跳过确认")
@click.pass_context
def comment_delete(ctx: click.Context, comment_id: str, yes: bool):
    _require_login(ctx)
    client = _client(ctx)
    if not yes and not _json_mode(ctx):
        click.confirm(f"确认删除评论 {comment_id}？", abort=True)
    try:
        client.delete_comment(comment_id)
        if _json_mode(ctx):
            out.print_json({"success": True, "commentId": comment_id})
        else:
            out.success(f"评论 {comment_id} 已删除")
    except APIError as exc:
        _fail(ctx, str(exc))


@comment.command("related")
@click.option("--page", default=1, show_default=True)
@click.option("--size", default=20, show_default=True)
@click.pass_context
def comment_related(ctx: click.Context, page: int, size: int):
    _require_login(ctx)
    client = _client(ctx)
    try:
        try:
            data = _call_if_exists(client, ["get_related_comments"], page=page, size=size)
        except AttributeError:
            data = client.get("/api/user/comments/related", params={"pageNum": page, "pageSize": size})
        if _json_mode(ctx):
            out.print_json(data)
        else:
            records = (data or {}).get("records", [])
            _print_page_info(data)
            _print_comment_rows(records)
    except APIError as exc:
        _fail(ctx, str(exc))


@comment.command("latest")
@click.option("--size", default=10, show_default=True)
@click.pass_context
def comment_latest(ctx: click.Context, size: int):
    _require_login(ctx)
    client = _client(ctx)
    try:
        try:
            data = _call_if_exists(client, ["get_latest_comments"], size=size)
        except AttributeError:
            data = client.get("/api/user/comments/latest", params={"size": size})
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_comment_rows(data or [])
    except APIError as exc:
        _fail(ctx, str(exc))


@cli.group()
def like():
    """点赞"""


@like.command("toggle")
@click.argument("target_id")
@click.option("--type", "target_type", default="POST", type=click.Choice(["POST", "COMMENT", "CHAPTER", "COURSE"], case_sensitive=False), show_default=True)
@click.pass_context
def like_toggle(ctx: click.Context, target_id: str, target_type: str):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.toggle_like(target_id, target_type)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            liked = data.get("isLiked", data.get("liked", data.get("status")))
            out.success("已点赞" if liked else "已取消点赞")
    except APIError as exc:
        _fail(ctx, str(exc))


@like.command("status")
@click.argument("target_id")
@click.option("--type", "target_type", default="POST", type=click.Choice(["POST", "COMMENT", "CHAPTER", "COURSE"], case_sensitive=False), show_default=True)
@click.pass_context
def like_status(ctx: click.Context, target_id: str, target_type: str):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.get_like_status(target_id, target_type)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            count = data.get("count", data.get("likeCount", "-"))
            print(f"点赞状态：{_FORMATTERS.yes_no(data.get('liked', data.get('isLiked')))}  数量：{count}")
    except APIError as exc:
        _fail(ctx, str(exc))


@cli.group()
def favorite():
    """收藏"""


@favorite.command("toggle")
@click.argument("target_id")
@click.option("--type", "target_type", default="POST", type=click.Choice(["POST", "COMMENT", "CHAPTER", "INTERVIEW_QUESTION"], case_sensitive=False), show_default=True)
@click.pass_context
def favorite_toggle(ctx: click.Context, target_id: str, target_type: str):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.toggle_favorite(target_id, target_type)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            favorited = data.get("isFavorited", data.get("favorited", data.get("status")))
            out.success("已收藏" if favorited else "已取消收藏")
    except APIError as exc:
        _fail(ctx, str(exc))


@favorite.command("status")
@click.argument("target_id")
@click.option("--type", "target_type", default="POST", type=click.Choice(["POST", "COMMENT", "CHAPTER", "INTERVIEW_QUESTION"], case_sensitive=False), show_default=True)
@click.pass_context
def favorite_status(ctx: click.Context, target_id: str, target_type: str):
    _require_login(ctx)
    client = _client(ctx)
    try:
        try:
            data = _call_if_exists(client, ["get_favorite_status"], target_id, target_type)
        except AttributeError:
            data = client.get(f"/api/favorites/status/{target_type}/{target_id}")
        if _json_mode(ctx):
            out.print_json(data)
        else:
            favorited = data.get("isFavorited", data.get("favorited", False))
            count = data.get("favoritesCount", data.get("favoriteCount", data.get("count", 0)))
            print(f"收藏状态：{_FORMATTERS.yes_no(favorited)}  收藏数：{count}")
    except APIError as exc:
        _fail(ctx, str(exc))


@favorite.command("list")
@click.option("--page", default=1, show_default=True)
@click.option("--size", default=10, show_default=True)
@click.pass_context
def favorite_list(ctx: click.Context, page: int, size: int):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.list_my_favorites(page, size)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            records = (data or {}).get("records", [])
            _print_page_info(data)
            _print_favorite_rows(records)
    except APIError as exc:
        _fail(ctx, str(exc))


@cli.group()
def follow():
    """关注"""


@follow.command("toggle")
@click.argument("target_id")
@click.option("--type", "target_type", default="USER", type=click.Choice(["USER", "POST", "CHAPTER", "COURSE"], case_sensitive=False), show_default=True)
@click.pass_context
def follow_toggle(ctx: click.Context, target_id: str, target_type: str):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.toggle_follow(target_id, target_type)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            followed = data.get("isFollowing", data.get("followed", data.get("status")))
            out.success("已关注" if followed else "已取消关注")
    except APIError as exc:
        _fail(ctx, str(exc))


@follow.command("status")
@click.argument("target_id")
@click.option("--type", "target_type", default="USER", type=click.Choice(["USER", "POST", "CHAPTER", "COURSE"], case_sensitive=False), show_default=True)
@click.pass_context
def follow_status(ctx: click.Context, target_id: str, target_type: str):
    _require_login(ctx)
    client = _client(ctx)
    try:
        try:
            data = _call_if_exists(client, ["check_follow_status"], target_id, target_type)
        except AttributeError:
            data = client.get(f"/api/app/follows/check/{target_type}/{target_id}")
        if _json_mode(ctx):
            out.print_json(data)
        else:
            followed = data.get("isFollowing", False)
            print(f"关注状态：{_FORMATTERS.yes_no(followed)}")
    except APIError as exc:
        _fail(ctx, str(exc))


@follow.command("list")
@click.option("--type", "target_type", default=None, type=click.Choice(["USER", "POST", "CHAPTER", "COURSE"], case_sensitive=False))
@click.option("--page", default=1, show_default=True)
@click.option("--size", default=10, show_default=True)
@click.pass_context
def follow_list(ctx: click.Context, target_type: Optional[str], page: int, size: int):
    _require_login(ctx)
    client = _client(ctx)
    try:
        try:
            data = _call_if_exists(client, ["list_my_follows"], target_type=target_type, page=page, size=size)
        except AttributeError:
            params = {"pageNum": page, "pageSize": size}
            if target_type:
                params["targetType"] = target_type
            data = client.get("/api/user/follows", params=params)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            records = (data or {}).get("records", [])
            _print_page_info(data)
            _print_follow_rows(records)
    except APIError as exc:
        _fail(ctx, str(exc))


@cli.group()
def course():
    """课程"""


@course.command("list")
@click.option("--page", default=1, show_default=True)
@click.option("--size", default=10, show_default=True)
@click.pass_context
def course_list(ctx: click.Context, page: int, size: int):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.list_courses(page, size)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            records = (data or {}).get("records", [])
            _print_page_info(data)
            _print_course_rows(records)
    except APIError as exc:
        _fail(ctx, str(exc))


@course.command("get")
@click.argument("course_id")
@click.pass_context
def course_get(ctx: click.Context, course_id: str):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.get_course(course_id)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_course_detail(data)
    except APIError as exc:
        _fail(ctx, str(exc))


@cli.group()
def chapter():
    """章节"""


@chapter.command("get")
@click.argument("chapter_id")
@click.pass_context
def chapter_get(ctx: click.Context, chapter_id: str):
    _require_login(ctx)
    client = _client(ctx)
    try:
        try:
            data = _call_if_exists(client, ["get_chapter"], chapter_id)
        except AttributeError:
            data = client.get(f"/api/app/chapters/{chapter_id}")
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_chapter_detail(data)
    except APIError as exc:
        _fail(ctx, str(exc))


@chapter.command("latest")
@click.pass_context
def chapter_latest(ctx: click.Context):
    _require_login(ctx)
    client = _client(ctx)
    try:
        try:
            data = _call_if_exists(client, ["list_latest_chapters"])
        except AttributeError:
            data = client.get("/api/app/chapters/latest")
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_chapter_rows(data or [])
    except APIError as exc:
        _fail(ctx, str(exc))


@cli.group()
def learning():
    """学习"""


@learning.command("progress")
@click.argument("course_id")
@click.pass_context
def learning_progress(ctx: click.Context, course_id: str):
    _require_login(ctx)
    client = _client(ctx)
    try:
        try:
            data = _call_if_exists(client, ["get_learning_progress"], course_id)
        except AttributeError:
            data = client.get(f"/api/user/learning/progress/{course_id}")
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_learning_progress(data)
    except APIError as exc:
        _fail(ctx, str(exc))


@learning.command("records")
@click.option("--page", default=1, show_default=True)
@click.option("--size", default=10, show_default=True)
@click.pass_context
def learning_records(ctx: click.Context, page: int, size: int):
    _require_login(ctx)
    client = _client(ctx)
    try:
        try:
            data = _call_if_exists(client, ["list_learning_records"], page=page, size=size)
        except AttributeError:
            data = client.get("/api/user/learning/records", params={"pageNum": page, "pageSize": size})
        if _json_mode(ctx):
            out.print_json(data)
        else:
            records = (data or {}).get("records", [])
            _print_page_info(data)
            _print_learning_rows(records)
    except APIError as exc:
        _fail(ctx, str(exc))


@learning.command("report")
@click.option("--course-id", required=True, help="课程 ID")
@click.option("--chapter-id", required=True, help="章节 ID")
@click.option("--study-duration", required=True, type=int, help="学习时长（秒）")
@click.option("--progress-percent", required=True, type=int, help="进度百分比")
@click.pass_context
def learning_report(ctx: click.Context, course_id: str, chapter_id: str, study_duration: int, progress_percent: int):
    _require_login(ctx)
    client = _client(ctx)
    payload = {
        "courseId": course_id,
        "chapterId": chapter_id,
        "studyDurationSeconds": study_duration,
        "progressPercent": progress_percent,
    }
    try:
        try:
            data = _call_if_exists(client, ["report_learning_progress"], **payload)
        except AttributeError:
            data = client.post("/api/user/learning/progress/report", json_data=payload)
        if _json_mode(ctx):
            out.print_json(data if data is not None else payload)
        else:
            out.success("学习进度已上报")
    except APIError as exc:
        _fail(ctx, str(exc))


@cli.group()
def subscription():
    """订阅"""


@subscription.command("activate-cdk")
@click.argument("cdk_code")
@click.pass_context
def subscription_activate_cdk(ctx: click.Context, cdk_code: str):
    _require_login(ctx)
    client = _client(ctx)
    try:
        try:
            data = _call_if_exists(client, ["activate_cdk"], cdk_code)
        except AttributeError:
            data = client.post("/api/user/subscription/activate-cdk", json_data={"cdkCode": cdk_code})
        if _json_mode(ctx):
            out.print_json(data if data is not None else {"success": True, "cdkCode": cdk_code})
        else:
            out.success("CDK 激活成功")
    except APIError as exc:
        _fail(ctx, str(exc))


def main():
    cli(obj=None)


if __name__ == "__main__":
    main()
