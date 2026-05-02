# 使用方式

优先阅读 `cli-command-reference.md` 获取完整命令。这个文件保留最常用入口，方便快速调用。

## 常用公开查询

先检查版本：

```bash
~/.qiaoya/bin/qiaoya --json version
```

如果 `updateAvailable` 为 `true`，提示用户执行返回的 `installCommand` 更新。

```bash
~/.qiaoya/bin/qiaoya --json public overview
~/.qiaoya/bin/qiaoya --json public courses
~/.qiaoya/bin/qiaoya --json public course --id <courseId>
~/.qiaoya/bin/qiaoya --json public chapters --course-id <courseId>
~/.qiaoya/bin/qiaoya --json public services
~/.qiaoya/bin/qiaoya --json public plans
~/.qiaoya/bin/qiaoya --json ai-news today
```

## 通用前台 API 调用

所有前台暴露接口都可以通过 `api` 命令调用：

```bash
~/.qiaoya/bin/qiaoya --json api GET /api/app/chapters/latest
~/.qiaoya/bin/qiaoya --json api POST /api/app/posts/queries --body '{"pageNum":1,"pageSize":10}'
~/.qiaoya/bin/qiaoya --json api POST /api/user/comments --body '{"businessType":"POST","businessId":"...","content":"..."}'
~/.qiaoya/bin/qiaoya --json api GET /api/expressions/alias-map
```

`api` 命令只允许前台白名单路径，禁止 `/api/admin`、账号密码登录、OAuth token/callback、OSS/CDN 回调等流程型端点。访问非 `/api/public/` 路径且本地未登录时，CLI 会直接打开浏览器授权登录，用户只需要在浏览器里确认。

## 需要登录态的查询

```bash
~/.qiaoya/bin/qiaoya --json auth status
~/.qiaoya/bin/qiaoya auth login
~/.qiaoya/bin/qiaoya auth logout
```

当用户请求的任务需要登录且 `auth status` 显示未登录时，Agent 应直接执行 `auth login`，不要把命令丢给用户执行。用户只需要在打开的浏览器页面完成登录和授权。不要要求用户提供密码、token 或 Cookie。

## 安装或修复

```bash
curl -fsSL https://code.xhyovo.cn/install | sh
```

安装完成后，必要时提醒用户重启 Codex / Claude Code，或在 Cursor / Windsurf 项目里重新加载规则。
