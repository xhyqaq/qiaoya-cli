# 使用方式

优先阅读 `cli-command-reference.md` 获取完整命令。这个文件保留最常用入口，方便快速调用。

## 常用公开查询

```bash
~/.qiaoya/bin/qiaoya --json public overview
~/.qiaoya/bin/qiaoya --json public courses
~/.qiaoya/bin/qiaoya --json public services
~/.qiaoya/bin/qiaoya --json public plans
~/.qiaoya/bin/qiaoya --json ai-news today
```

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
