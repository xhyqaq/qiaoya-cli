# FAQ

## 用户需要安装 Node、Python 或 Go 吗？

不需要。普通用户通过一行安装命令下载单文件 `qiaoya` runtime，并安装对应 AI 工具的 skill/rules。

macOS / Linux：

```bash
curl -fsSL https://code.xhyovo.cn/install | sh
```

Windows PowerShell：

```powershell
irm https://code.xhyovo.cn/install.ps1 | iex
```

## 为什么不用 npx 或 pip？

用户目标是“下载友好”和“使用友好”。`npx` 需要 Node 环境，`pip` 需要 Python 环境。当前方案使用 Go 原生二进制，用户不需要准备语言运行时。

## 支持哪些 Agent 工具？

第一版支持常用工具：

- Codex
- Claude Code
- Cursor
- Windsurf
- OpenClaw

Codex、Claude Code、OpenClaw 安装 skill 目录；Cursor、Windsurf 安装规则文件。

## 支持登录吗？

支持浏览器授权登录。需要登录时，由 Agent 执行：

```bash
qiaoya auth login
```

CLI 会打开敲鸭授权页，用户在浏览器里使用已有敲鸭账号登录并确认授权。Agent 不应该接触邮箱、密码、token 或 Cookie。

## Access Token 过期后要重新登录吗？

通常不用。CLI 会使用本地保存的 Refresh Token 自动刷新 Access Token。只有 Refresh Token 失效、被撤销或用户执行 `qiaoya auth logout` 后，才需要重新 `qiaoya auth login`。

## 为什么有些命令需要登录？

公开介绍、课程、服务、AI 日报等可以匿名读取。更新日志、个人相关数据、未来的发布/评论等能力可能需要登录态。遇到权限错误时，先运行：

```bash
qiaoya --json auth status
```

如果未登录，Agent 直接执行：

```bash
qiaoya auth login
```

不要让用户自己复制这条命令；用户只负责在浏览器里完成授权。

## 可以让 Agent 自动发文章或评论吗？

未来可以支持，但必须有明确安全边界：

- 用户明确要求
- 先检查登录态
- 支持 dry-run 或预览
- 让用户确认最终内容
- 再执行写入
