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
from typing import Any, Callable, Optional

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


def _value_from_path(item: Any, path: str):
    current = item
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _render_cell(item: dict[str, Any], getter: str | Callable[[dict[str, Any]], Any]):
    if callable(getter):
        return getter(item)
    return _value_from_path(item, getter)


def _print_simple_rows(items: list[dict[str, Any]], columns: list[tuple[str, str | Callable[[dict[str, Any]], Any]]]):
    rows = []
    for item in items:
        rows.append([_FORMATTERS.text_or_dash(_render_cell(item, getter)) for _, getter in columns])
    out.print_table([header for header, _ in columns], rows)


def _print_simple_detail(data: dict[str, Any], fields: list[tuple[str, str | Callable[[dict[str, Any]], Any]]]):
    out.print_kv([
        (label, _FORMATTERS.text_or_dash(_render_cell(data, getter)))
        for label, getter in fields
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


@auth.command("send-register-code")
@click.option("-e", "--email", required=True, prompt=True, help="邮箱地址")
@click.pass_context
def auth_send_register_code(ctx: click.Context, email: str):
    client = _client(ctx)
    try:
        client.send_register_code(email)
        if _json_mode(ctx):
            out.print_json({"success": True, "email": email})
        else:
            out.success(f"注册验证码已发送到 {email}")
    except APIError as exc:
        _fail(ctx, str(exc))


@auth.command("send-reset-code")
@click.option("-e", "--email", required=True, prompt=True, help="邮箱地址")
@click.pass_context
def auth_send_reset_code(ctx: click.Context, email: str):
    client = _client(ctx)
    try:
        client.send_password_reset_code(email)
        if _json_mode(ctx):
            out.print_json({"success": True, "email": email})
        else:
            out.success(f"重置密码验证码已发送到 {email}")
    except APIError as exc:
        _fail(ctx, str(exc))


@auth.command("reset-password")
@click.option("-e", "--email", required=True, prompt=True, help="邮箱地址")
@click.option("--code", required=True, prompt=True, help="验证码")
@click.option("--new-password", required=True, prompt=True, hide_input=True, help="新密码")
@click.pass_context
def auth_reset_password(ctx: click.Context, email: str, code: str, new_password: str):
    client = _client(ctx)
    try:
        client.reset_password(email, code, new_password)
        if _json_mode(ctx):
            out.print_json({"success": True, "email": email})
        else:
            out.success("密码重置成功")
    except APIError as exc:
        _fail(ctx, str(exc))


@auth.command("heartbeat")
@click.pass_context
def auth_heartbeat(ctx: click.Context):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.heartbeat()
        if _json_mode(ctx):
            out.print_json(data if data is not None else {"success": True})
        else:
            out.success("心跳成功")
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


@user.command("update")
@click.option("--name", default=None, help="昵称")
@click.option("--bio", default=None, help="简介")
@click.option("--avatar", default=None, help="头像资源 ID 或 URL")
@click.pass_context
def user_update(ctx: click.Context, name: Optional[str], bio: Optional[str], avatar: Optional[str]):
    _require_login(ctx)
    client = _client(ctx)
    payload = {k: v for k, v in {"name": name, "bio": bio, "avatar": avatar}.items() if v is not None}
    if not payload:
        _fail(ctx, "至少提供一个更新字段")
    try:
        data = client.update_profile(**payload)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            out.success("用户资料已更新")
    except APIError as exc:
        _fail(ctx, str(exc))


@user.command("change-password")
@click.option("--old-password", required=True, prompt=True, hide_input=True, help="旧密码")
@click.option("--new-password", required=True, prompt=True, hide_input=True, help="新密码")
@click.pass_context
def user_change_password(ctx: click.Context, old_password: str, new_password: str):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.change_password(old_password, new_password)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            out.success("密码修改成功")
    except APIError as exc:
        _fail(ctx, str(exc))


@user.command("toggle-email-notification")
@click.pass_context
def user_toggle_email_notification(ctx: click.Context):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.toggle_email_notification()
        if _json_mode(ctx):
            out.print_json(data)
        else:
            enabled = data.get("emailNotificationEnabled")
            if enabled is None:
                out.success("邮箱通知设置已切换")
            else:
                out.success(f"邮箱通知已切换为：{'开启' if enabled else '关闭'}")
    except APIError as exc:
        _fail(ctx, str(exc))


@user.command("menu-codes")
@click.pass_context
def user_menu_codes(ctx: click.Context):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.get_menu_codes()
        if _json_mode(ctx):
            out.print_json(data)
        else:
            out.print_table(["菜单码"], [[code] for code in data])
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


@cli.group()
def public():
    """公开前台能力"""


@public.command("about")
@click.pass_context
def public_about(ctx: click.Context):
    client = _client(ctx)
    try:
        data = client.get_about_page()
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_simple_detail(data, [("标题", "title"), ("内容", "content")])
    except APIError as exc:
        _fail(ctx, str(exc))


@public.command("stats")
@click.pass_context
def public_stats(ctx: click.Context):
    client = _client(ctx)
    try:
        data = client.get_public_stats()
        if _json_mode(ctx):
            out.print_json(data)
        else:
            total = data.get("totalCount", data.get("count", 0))
            print(f"用户总数：{total}")
    except APIError as exc:
        _fail(ctx, str(exc))


@public.command("course-list")
@click.option("--page", default=1, show_default=True)
@click.option("--size", default=10, show_default=True)
@click.pass_context
def public_course_list(ctx: click.Context, page: int, size: int):
    client = _client(ctx)
    try:
        data = client.list_public_courses(page=page, size=size)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_page_info(data)
            _print_course_rows((data or {}).get("records", []))
    except APIError as exc:
        _fail(ctx, str(exc))


@public.command("course-get")
@click.argument("course_id")
@click.pass_context
def public_course_get(ctx: click.Context, course_id: str):
    client = _client(ctx)
    try:
        data = client.get_public_course(course_id)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_course_detail(data)
    except APIError as exc:
        _fail(ctx, str(exc))


@public.command("plans")
@click.pass_context
def public_plans(ctx: click.Context):
    client = _client(ctx)
    try:
        data = client.get_public_subscription_plans()
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_simple_rows(data, [("ID", "id"), ("名称", "name"), ("级别", "level"), ("价格", "price")])
    except APIError as exc:
        _fail(ctx, str(exc))


@public.command("app-plans")
@click.pass_context
def public_app_plans(ctx: click.Context):
    client = _client(ctx)
    try:
        data = client.get_app_subscription_plans()
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_simple_rows(data, [("ID", "id"), ("名称", "name"), ("级别", "level"), ("价格", "price")])
    except APIError as exc:
        _fail(ctx, str(exc))


@public.command("testimonials")
@click.pass_context
def public_testimonials(ctx: click.Context):
    client = _client(ctx)
    try:
        data = client.list_public_testimonials()
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_simple_rows(data, [("ID", "id"), ("作者", "authorName"), ("评分", "rating"), ("内容", "content")])
    except APIError as exc:
        _fail(ctx, str(exc))


@public.command("update-logs")
@click.pass_context
def public_update_logs(ctx: click.Context):
    client = _client(ctx)
    try:
        data = client.list_public_update_logs()
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_simple_rows(data, [("ID", "id"), ("标题", "title"), ("时间", "createTime")])
    except APIError as exc:
        _fail(ctx, str(exc))


@public.command("update-log")
@click.argument("log_id")
@click.pass_context
def public_update_log(ctx: click.Context, log_id: str):
    client = _client(ctx)
    try:
        data = client.get_public_update_log(log_id)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_simple_detail(data, [("标题", "title"), ("摘要", "summary"), ("时间", "createTime")])
    except APIError as exc:
        _fail(ctx, str(exc))


@public.command("services")
@click.pass_context
def public_services(ctx: click.Context):
    client = _client(ctx)
    try:
        data = client.list_public_services()
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_simple_rows(data, [("编码", "serviceCode"), ("标题", "title"), ("价格", "price"), ("摘要", "summary")])
    except APIError as exc:
        _fail(ctx, str(exc))


@public.command("service")
@click.argument("service_code")
@click.pass_context
def public_service(ctx: click.Context, service_code: str):
    client = _client(ctx)
    try:
        data = client.get_public_service(service_code)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_simple_detail(data, [("编码", "serviceCode"), ("标题", "title"), ("价格", "price"), ("描述", "description")])
    except APIError as exc:
        _fail(ctx, str(exc))


@cli.group("ai-news")
def ai_news():
    """AI 日报"""


@ai_news.command("today")
@click.pass_context
def ai_news_today(ctx: click.Context):
    client = _client(ctx)
    try:
        data = client.get_ai_news_today()
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_simple_detail(data, [("日期", "date"), ("标题", lambda item: " / ".join(item.get("titles", []) or []))])
    except APIError as exc:
        _fail(ctx, str(exc))


@ai_news.command("history")
@click.option("--page", default=1, show_default=True)
@click.option("--size", default=10, show_default=True)
@click.pass_context
def ai_news_history(ctx: click.Context, page: int, size: int):
    client = _client(ctx)
    try:
        data = client.list_ai_news_history(page=page, size=size)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_page_info(data)
            _print_simple_rows((data or {}).get("records", []), [("日期", "date"), ("标题", "title"), ("数量", "count")])
    except APIError as exc:
        _fail(ctx, str(exc))


@ai_news.command("daily")
@click.option("--date", required=True, help="日期，例如 2026-04-20")
@click.option("--page", default=1, show_default=True)
@click.option("--size", default=10, show_default=True)
@click.pass_context
def ai_news_daily(ctx: click.Context, date: str, page: int, size: int):
    client = _client(ctx)
    try:
        data = client.list_ai_news_daily(date=date, page=page, size=size)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_page_info(data)
            _print_simple_rows((data or {}).get("records", []), [("ID", "id"), ("标题", "title"), ("日期", "date")])
    except APIError as exc:
        _fail(ctx, str(exc))


@ai_news.command("get")
@click.argument("news_id")
@click.pass_context
def ai_news_get(ctx: click.Context, news_id: str):
    client = _client(ctx)
    try:
        data = client.get_ai_news_detail(news_id)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_simple_detail(data, [("ID", "id"), ("标题", "title"), ("日期", "date"), ("内容", "content")])
    except APIError as exc:
        _fail(ctx, str(exc))


@cli.group("ai-tool")
def ai_tool():
    """AI 工具摘要"""


@ai_tool.command("summary")
@click.pass_context
def ai_tool_summary(ctx: click.Context):
    client = _client(ctx)
    try:
        data = client.get_ai_tool_summary()
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_simple_detail(data, [("API Key", "apiKey"), ("今日使用", "todayUsed"), ("今日预算", "todayBudget"), ("本周使用", "weekUsed"), ("本周预算", "weekBudget")])
    except APIError as exc:
        _fail(ctx, str(exc))


@cli.group()
def codex():
    """Codex 公共信息"""


@codex.command("info")
@click.pass_context
def codex_info(ctx: click.Context):
    client = _client(ctx)
    try:
        data = client.get_codex_info()
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_simple_detail(data, [("API Key", "apiKey"), ("今日使用", "todayUsed"), ("今日预算", "todayBudget"), ("本周使用", "weekUsed"), ("本周预算", "weekBudget")])
    except APIError as exc:
        _fail(ctx, str(exc))


@cli.group("codex-p")
def codex_p():
    """Codex 多实例公共信息"""


@codex_p.command("info")
@click.pass_context
def codex_p_info(ctx: click.Context):
    client = _client(ctx)
    try:
        data = client.get_codex_p_info()
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_simple_detail(data, [("API Key", "apiKey"), ("今日使用", "todayUsed"), ("今日预算", "todayBudget"), ("本周使用", "weekUsed"), ("本周预算", "weekBudget")])
    except APIError as exc:
        _fail(ctx, str(exc))


@codex_p.command("infos")
@click.pass_context
def codex_p_infos(ctx: click.Context):
    client = _client(ctx)
    try:
        data = client.list_codex_p_infos()
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_simple_rows(data, [("ID", "id"), ("名称", "name"), ("今日使用", "todayUsed"), ("本周使用", "weekUsed")])
    except APIError as exc:
        _fail(ctx, str(exc))


@cli.group("expression")
def expression():
    """表情资源"""


@expression.command("list")
@click.pass_context
def expression_list(ctx: click.Context):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.list_expressions()
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_simple_rows(data, [("Code", "code"), ("名称", "name"), ("图片", "imageUrl")])
    except APIError as exc:
        _fail(ctx, str(exc))


@expression.command("alias-map")
@click.pass_context
def expression_alias_map(ctx: click.Context):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.get_expression_alias_map()
        if _json_mode(ctx):
            out.print_json(data)
        else:
            out.print_table(["Alias", "URL"], [[k, v] for k, v in data.items()])
    except APIError as exc:
        _fail(ctx, str(exc))


@cli.group()
def testimonial():
    """用户评价"""


@testimonial.command("public-list")
@click.pass_context
def testimonial_public_list(ctx: click.Context):
    client = _client(ctx)
    try:
        data = client.list_public_testimonials()
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_simple_rows(data, [("ID", "id"), ("作者", "authorName"), ("评分", "rating"), ("内容", "content")])
    except APIError as exc:
        _fail(ctx, str(exc))


@testimonial.command("my")
@click.pass_context
def testimonial_my(ctx: click.Context):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.get_my_testimonial()
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_simple_detail(data, [("ID", "id"), ("评分", "rating"), ("状态", "status"), ("内容", "content")])
    except APIError as exc:
        _fail(ctx, str(exc))


@testimonial.command("create")
@click.option("--content", required=True, prompt=True, help="评价内容")
@click.option("--rating", required=True, type=int, help="评分 1-5")
@click.option("--title", default=None, help="标题")
@click.pass_context
def testimonial_create(ctx: click.Context, content: str, rating: int, title: Optional[str]):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.create_testimonial(content=content, rating=rating, title=title)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            out.success(f"评价已提交，ID：{data.get('id')}")
    except APIError as exc:
        _fail(ctx, str(exc))


@testimonial.command("update")
@click.argument("testimonial_id")
@click.option("--content", required=True, prompt=True, help="评价内容")
@click.option("--rating", required=True, type=int, help="评分 1-5")
@click.option("--title", default=None, help="标题")
@click.pass_context
def testimonial_update(ctx: click.Context, testimonial_id: str, content: str, rating: int, title: Optional[str]):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.update_testimonial(testimonial_id=testimonial_id, content=content, rating=rating, title=title)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            out.success(f"评价 {testimonial_id} 已更新")
    except APIError as exc:
        _fail(ctx, str(exc))


@cli.group()
def interview():
    """面试题库"""


@interview.command("list")
@click.option("--page", default=1, show_default=True)
@click.option("--size", default=10, show_default=True)
@click.pass_context
def interview_list(ctx: click.Context, page: int, size: int):
    client = _client(ctx)
    try:
        data = client.list_interview_questions(page=page, size=size)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_page_info(data)
            _print_simple_rows((data or {}).get("records", []), [("ID", "id"), ("标题", "title"), ("状态", "status"), ("时间", "createTime")])
    except APIError as exc:
        _fail(ctx, str(exc))


@interview.command("my")
@click.option("--page", default=1, show_default=True)
@click.option("--size", default=10, show_default=True)
@click.pass_context
def interview_my(ctx: click.Context, page: int, size: int):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.list_interview_questions(page=page, size=size, mine=True)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_page_info(data)
            _print_simple_rows((data or {}).get("records", []), [("ID", "id"), ("标题", "title"), ("状态", "status"), ("时间", "createTime")])
    except APIError as exc:
        _fail(ctx, str(exc))


@interview.command("get")
@click.argument("question_id")
@click.pass_context
def interview_get(ctx: click.Context, question_id: str):
    client = _client(ctx)
    try:
        data = client.get_interview_question(question_id)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_simple_detail(data, [("ID", "id"), ("标题", "title"), ("状态", "status"), ("内容", "content"), ("答案", "answer")])
    except APIError as exc:
        _fail(ctx, str(exc))


@interview.command("create")
@click.option("--title", required=True, prompt=True)
@click.option("--content", required=True, prompt=True)
@click.option("--answer", default=None)
@click.option("--status", default=None)
@click.pass_context
def interview_create(ctx: click.Context, title: str, content: str, answer: Optional[str], status: Optional[str]):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.create_interview_question(title=title, content=content, answer=answer, status=status)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            out.success(f"题目已创建，ID：{data.get('id')}")
    except APIError as exc:
        _fail(ctx, str(exc))


@interview.command("update")
@click.argument("question_id")
@click.option("--title", default=None)
@click.option("--content", default=None)
@click.option("--answer", default=None)
@click.pass_context
def interview_update(ctx: click.Context, question_id: str, title: Optional[str], content: Optional[str], answer: Optional[str]):
    _require_login(ctx)
    client = _client(ctx)
    payload = {k: v for k, v in {"title": title, "content": content, "answer": answer}.items() if v is not None}
    if not payload:
        _fail(ctx, "至少提供一个更新字段")
    try:
        data = client.update_interview_question(question_id, **payload)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            out.success(f"题目 {question_id} 已更新")
    except APIError as exc:
        _fail(ctx, str(exc))


@interview.command("status")
@click.argument("question_id")
@click.option("--value", "status_value", required=True, help="状态值")
@click.pass_context
def interview_status(ctx: click.Context, question_id: str, status_value: str):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.change_interview_question_status(question_id, status_value)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            out.success(f"题目 {question_id} 状态已更新为 {status_value}")
    except APIError as exc:
        _fail(ctx, str(exc))


@interview.command("delete")
@click.argument("question_id")
@click.option("--yes", "-y", is_flag=True, help="跳过确认")
@click.pass_context
def interview_delete(ctx: click.Context, question_id: str, yes: bool):
    _require_login(ctx)
    client = _client(ctx)
    if not yes and not _json_mode(ctx):
        click.confirm(f"确认删除题目 {question_id}？", abort=True)
    try:
        client.delete_interview_question(question_id)
        if _json_mode(ctx):
            out.print_json({"success": True, "questionId": question_id})
        else:
            out.success(f"题目 {question_id} 已删除")
    except APIError as exc:
        _fail(ctx, str(exc))


@cli.group()
def unread():
    """列表级未读"""


@unread.command("summary")
@click.pass_context
def unread_summary(ctx: click.Context):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.get_unread_summary()
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_simple_detail(data, [("帖子未读", "postsUnread"), ("题目未读", "questionsUnread"), ("章节未读", "chaptersUnread"), ("聊天未读", "chatsUnread")])
    except APIError as exc:
        _fail(ctx, str(exc))


@unread.command("visit")
@click.argument("channel")
@click.pass_context
def unread_visit(ctx: click.Context, channel: str):
    _require_login(ctx)
    client = _client(ctx)
    try:
        client.visit_unread_channel(channel)
        if _json_mode(ctx):
            out.print_json({"success": True, "channel": channel})
        else:
            out.success(f"频道 {channel} 已 visit")
    except APIError as exc:
        _fail(ctx, str(exc))


@cli.group()
def resource():
    """资源访问"""


@resource.command("list")
@click.option("--page", default=1, show_default=True)
@click.option("--size", default=10, show_default=True)
@click.option("--type", "resource_type", default=None, help="资源类型")
@click.pass_context
def resource_list(ctx: click.Context, page: int, size: int, resource_type: Optional[str]):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.list_user_resources(page=page, size=size, resource_type=resource_type)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            records = data.get("records") or data.get("items") or []
            if isinstance(records, list):
                _print_simple_rows(records, [("ID", "id"), ("名称", "filename"), ("类型", "resourceType"), ("时间", "createTime")])
            else:
                out.print_json(data)
    except APIError as exc:
        _fail(ctx, str(exc))


@resource.command("access-url")
@click.argument("resource_id")
@click.pass_context
def resource_access_url(ctx: click.Context, resource_id: str):
    client = _client(ctx)
    url = client.get_resource_access_url(resource_id)
    if _json_mode(ctx):
        out.print_json({"resourceId": resource_id, "url": url})
    else:
        print(url)


@cli.group()
def chat():
    """聊天室"""


@chat.command("rooms")
@click.option("--page", default=1, show_default=True)
@click.option("--size", default=20, show_default=True)
@click.option("--name-like", default=None, help="名称过滤")
@click.pass_context
def chat_rooms(ctx: click.Context, page: int, size: int, name_like: Optional[str]):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.list_chat_rooms(page=page, size=size, name_like=name_like)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_page_info(data)
            _print_simple_rows((data or {}).get("records", []), [("ID", "id"), ("名称", "name"), ("描述", "description")])
    except APIError as exc:
        _fail(ctx, str(exc))


@chat.command("create")
@click.option("--name", required=True, prompt=True)
@click.option("--description", default=None)
@click.pass_context
def chat_create(ctx: click.Context, name: str, description: Optional[str]):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.create_chat_room(name=name, description=description)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            out.success(f"聊天室已创建，ID：{data.get('id')}")
    except APIError as exc:
        _fail(ctx, str(exc))


@chat.command("join")
@click.argument("room_id")
@click.pass_context
def chat_join(ctx: click.Context, room_id: str):
    _require_login(ctx)
    client = _client(ctx)
    try:
        client.join_chat_room(room_id)
        if _json_mode(ctx):
            out.print_json({"success": True, "roomId": room_id})
        else:
            out.success(f"已加入聊天室 {room_id}")
    except APIError as exc:
        _fail(ctx, str(exc))


@chat.command("members")
@click.argument("room_id")
@click.pass_context
def chat_members(ctx: click.Context, room_id: str):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.list_chat_room_members(room_id)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_simple_rows(data, [("ID", "id"), ("名称", lambda item: item.get("name") or item.get("username")), ("在线", "online")])
    except APIError as exc:
        _fail(ctx, str(exc))


@chat.command("unread")
@click.argument("room_id")
@click.pass_context
def chat_unread(ctx: click.Context, room_id: str):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.get_chat_room_unread_info(room_id)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_simple_detail(data, [("未读数", "count"), ("首条未读 ID", "firstUnreadId"), ("首条未读时间", "firstUnreadOccurredAt")])
    except APIError as exc:
        _fail(ctx, str(exc))


@chat.command("visit")
@click.argument("room_id")
@click.option("--anchor-id", default=None)
@click.option("--anchor-time", default=None)
@click.pass_context
def chat_visit(ctx: click.Context, room_id: str, anchor_id: Optional[str], anchor_time: Optional[str]):
    _require_login(ctx)
    client = _client(ctx)
    try:
        client.visit_chat_room(room_id, anchor_id=anchor_id, anchor_time=anchor_time)
        if _json_mode(ctx):
            out.print_json({"success": True, "roomId": room_id})
        else:
            out.success(f"聊天室 {room_id} 已 visit")
    except APIError as exc:
        _fail(ctx, str(exc))


@chat.command("leave")
@click.argument("room_id")
@click.pass_context
def chat_leave(ctx: click.Context, room_id: str):
    _require_login(ctx)
    client = _client(ctx)
    try:
        client.leave_chat_room(room_id)
        if _json_mode(ctx):
            out.print_json({"success": True, "roomId": room_id})
        else:
            out.success(f"已退出聊天室 {room_id}")
    except APIError as exc:
        _fail(ctx, str(exc))


@chat.command("delete")
@click.argument("room_id")
@click.option("--yes", "-y", is_flag=True, help="跳过确认")
@click.pass_context
def chat_delete(ctx: click.Context, room_id: str, yes: bool):
    _require_login(ctx)
    client = _client(ctx)
    if not yes and not _json_mode(ctx):
        click.confirm(f"确认删除聊天室 {room_id}？", abort=True)
    try:
        client.delete_chat_room(room_id)
        if _json_mode(ctx):
            out.print_json({"success": True, "roomId": room_id})
        else:
            out.success(f"聊天室 {room_id} 已删除")
    except APIError as exc:
        _fail(ctx, str(exc))


@chat.command("messages")
@click.argument("room_id")
@click.option("--page", default=1, show_default=True)
@click.option("--size", default=20, show_default=True)
@click.pass_context
def chat_messages(ctx: click.Context, room_id: str, page: int, size: int):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.list_chat_messages(room_id, page=page, size=size)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_page_info(data)
            _print_simple_rows((data or {}).get("records", []), [("ID", "id"), ("内容", "content"), ("时间", "createTime")])
    except APIError as exc:
        _fail(ctx, str(exc))


@chat.command("send")
@click.argument("room_id")
@click.option("--content", required=True, prompt=True)
@click.option("--type", "message_type", default="TEXT", show_default=True)
@click.pass_context
def chat_send(ctx: click.Context, room_id: str, content: str, message_type: str):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.send_chat_message(room_id, content=content, message_type=message_type)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            out.success(f"消息已发送，ID：{data.get('id')}")
    except APIError as exc:
        _fail(ctx, str(exc))


@cli.group()
def oauth():
    """OAuth / OAuth2"""


@oauth.command("github-url")
@click.pass_context
def oauth_github_url(ctx: click.Context):
    client = _client(ctx)
    try:
        data = client.get_github_authorize_url()
        if _json_mode(ctx):
            out.print_json(data)
        else:
            print(data.get("url", ""))
    except APIError as exc:
        _fail(ctx, str(exc))


@oauth.command("github-status")
@click.pass_context
def oauth_github_status(ctx: click.Context):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.get_github_bind_status()
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_simple_detail(data, [("已绑定", lambda item: _FORMATTERS.yes_no(item.get("bound"))), ("提供方", "provider")])
    except APIError as exc:
        _fail(ctx, str(exc))


@oauth.command("github-bind")
@click.option("--code", required=True)
@click.option("--state", required=True)
@click.pass_context
def oauth_github_bind(ctx: click.Context, code: str, state: str):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.bind_github(code, state)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            out.success("GitHub 绑定成功")
    except APIError as exc:
        _fail(ctx, str(exc))


@oauth.command("github-unbind")
@click.pass_context
def oauth_github_unbind(ctx: click.Context):
    _require_login(ctx)
    client = _client(ctx)
    try:
        client.unbind_github()
        if _json_mode(ctx):
            out.print_json({"success": True})
        else:
            out.success("GitHub 已解绑")
    except APIError as exc:
        _fail(ctx, str(exc))


@oauth.command("client")
@click.argument("client_id")
@click.pass_context
def oauth_client(ctx: click.Context, client_id: str):
    client = _client(ctx)
    try:
        data = client.oauth2_get_client_info(client_id)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_simple_detail(data, [("Client ID", lambda item: item.get("clientId") or item.get("client_id")), ("名称", lambda item: item.get("clientName") or item.get("client_name")), ("创建时间", lambda item: item.get("createTime") or item.get("create_time"))])
    except APIError as exc:
        _fail(ctx, str(exc))


@oauth.command("consent")
@click.argument("client_id")
@click.pass_context
def oauth_consent(ctx: click.Context, client_id: str):
    client = _client(ctx)
    try:
        data = client.oauth2_get_consent(client_id)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_simple_detail(data, [("已授权", lambda item: _FORMATTERS.yes_no(item.get("consented"))), ("Scopes", lambda item: " ".join(item.get("scopes", []) or []))])
    except APIError as exc:
        _fail(ctx, str(exc))


@oauth.command("authorize")
@click.option("--client-id", required=True)
@click.option("--redirect-uri", required=True)
@click.option("--response-type", default="code", show_default=True)
@click.option("--scope", default=None)
@click.option("--state", default=None)
@click.option("--code-challenge", default=None)
@click.option("--code-challenge-method", default=None)
@click.option("--approved/--denied", default=True, show_default=True)
@click.pass_context
def oauth_authorize(
    ctx: click.Context,
    client_id: str,
    redirect_uri: str,
    response_type: str,
    scope: Optional[str],
    state: Optional[str],
    code_challenge: Optional[str],
    code_challenge_method: Optional[str],
    approved: bool,
):
    client = _client(ctx)
    try:
        data = client.oauth2_authorize(
            client_id=client_id,
            redirect_uri=redirect_uri,
            response_type=response_type,
            scope=scope,
            state=state,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            approved=approved,
        )
        if _json_mode(ctx):
            out.print_json(data)
        else:
            print(data)
    except APIError as exc:
        _fail(ctx, str(exc))


@oauth.command("authorizations")
@click.option("--page", default=1, show_default=True)
@click.option("--size", default=10, show_default=True)
@click.pass_context
def oauth_authorizations(ctx: click.Context, page: int, size: int):
    _require_login(ctx)
    client = _client(ctx)
    try:
        data = client.list_oauth2_authorizations(page=page, size=size)
        if _json_mode(ctx):
            out.print_json(data)
        else:
            _print_page_info(data)
            _print_simple_rows((data or {}).get("records", []), [("Client ID", "clientId"), ("名称", "clientName"), ("时间", "createTime")])
    except APIError as exc:
        _fail(ctx, str(exc))


@oauth.command("revoke")
@click.argument("client_id")
@click.pass_context
def oauth_revoke(ctx: click.Context, client_id: str):
    _require_login(ctx)
    client = _client(ctx)
    try:
        client.revoke_oauth2_authorization(client_id)
        if _json_mode(ctx):
            out.print_json({"success": True, "clientId": client_id})
        else:
            out.success(f"已撤销应用 {client_id} 的授权")
    except APIError as exc:
        _fail(ctx, str(exc))


def main():
    cli(obj=None)


if __name__ == "__main__":
    main()
