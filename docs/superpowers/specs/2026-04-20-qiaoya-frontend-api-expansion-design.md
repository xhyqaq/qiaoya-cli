# Qiaoya Frontend API Expansion Design

**Date:** 2026-04-20
**Status:** Approved

## Context

现有 `qiaoya` CLI 已覆盖登录、帖子、评论、课程、学习进度、通知等主链路，但前端真实使用的多个用户态服务尚未进入 CLI，包括公开首页接口、AI 资讯、聊天室、OAuth、未读汇总、资源访问、用户设置、题库与用户评价等。

目标是把“前台可见、用户可直接操作、适合脚本化”的 API 面补进 CLI，同时新增 GitHub Actions，自动验证测试、安装脚本、`pipx` 安装和命令入口，避免发布回归。

## Scope

纳入范围：

- `/api/public/*` 中与前台直接相关的公开能力
- `/api/app/*` 中用户端展示或交互能力
- `/api/user/*` 中用户设置、未读、资源、授权管理等能力
- 非 `/api/user/*` 但前台直接调用的用户态能力，如评价、题库、表情
- GitHub Actions 中的测试、安装、入口命令校验

排除范围：

- 任意 `/api/admin/*` 能力
- 仅用于前端本地缓存、UI 衍生计算或浏览器跳转的辅助逻辑
- 与当前 CLI 无关的仓库级重构

## Command Design

扩展后的 CLI 保持“资源主干 + 高频快捷命令”模式，新增下列命令组：

- `public`：公开首页能力，覆盖关于页、公开课程、套餐、统计、独立服务、公开评价、更新日志
- `ai-news`：AI 日报的今日摘要、往期列表、按日期列表、详情
- `ai-tool`：AI 工具额度摘要
- `codex` / `codex-p`：Codex 公共信息与多实例列表
- `expression`：表情列表与 alias 映射
- `testimonial`：我的评价、创建、更新、公开评价列表
- `interview`：题库列表、我的题目、详情、创建、更新、批量创建、状态切换、删除
- `unread`：未读汇总与频道 visit
- `resource`：资源列表、按类型过滤、资源访问 URL
- `chat`：聊天室列表、创建、加入、成员、未读、visit、退出、删除、消息列表、发消息
- `oauth`：GitHub OAuth URL / 绑定状态 / 绑定解绑，OAuth2 客户端信息、同意状态、授权码、我的授权列表、撤销授权

同时在现有命令组中补齐用户设置类命令：

- `user update`
- `user change-password`
- `user toggle-email-notification`
- `user menu-codes`
- `auth heartbeat`
- `auth send-register-code`
- `auth send-reset-code`
- `auth reset-password`

## Client Design

`QiaoyaClient` 继续作为唯一 HTTP 封装层，新增方法时遵循以下规则：

- 公开接口默认 `auth=False`
- 用户态接口保留鉴权头与 `X-Device-ID`
- 分页接口统一返回带 `records` 的字典或原始分页对象
- 只在 client 中做必要字段归一化，不搬运前端组件层逻辑
- 资源访问 URL 作为纯字符串拼接能力暴露，不依赖浏览器环境

## Testing

先补失败测试，再实现：

- `test_core.py`：验证新增 client 方法的路径、HTTP method、payload、鉴权策略
- `test_full_e2e.py`：验证新增命令组的入口、代表性命令和 JSON/文本输出
- GitHub Actions：在干净环境中运行 pytest、`bash -n install.sh`、`pipx install`、`qiaoya --help`、`curl | bash` 安装脚本校验

## Risks

- 部分线上公开接口可能返回 401/500，CI 不访问线上服务，只验证本地包安装和本地测试
- 某些前端 service 带有 UI 兼容处理，CLI 只保留与 HTTP 契约直接相关的部分
- 命令面会明显变大，因此 README 只展示高频命令，并保留 `--help` 作为完整索引
