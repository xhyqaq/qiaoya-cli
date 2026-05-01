# 排障

## 找不到 qiaoya

先检查：

```bash
~/.qiaoya/bin/qiaoya --help
```

如果不存在，提示用户重新安装：

```bash
curl -fsSL https://code.xhyovo.cn/install | sh
```

## Agent 没有识别敲鸭能力

运行：

```bash
qiaoya --json doctor
```

根据输出检查：

- Codex skill 是否安装到 `~/.codex/skills/qiaoya`
- Claude Code skill 是否安装到 `~/.claude/skills/qiaoya`
- OpenClaw skill 是否安装到 `~/.openclaw/skills/qiaoya`
- Cursor/Windsurf 是否在项目目录写入规则文件

安装后可能需要重启 Agent 或重新加载项目。

## Cursor 或 Windsurf 没生效

Cursor/Windsurf 通常依赖项目规则文件。请在项目根目录执行：

```bash
qiaoya install --agents cursor,windsurf --project-dir <project-path>
```

或者在项目根目录重新执行官网安装命令。

## 更新日志提示需要登录

先检查：

```bash
qiaoya --json auth status
```

如果未登录，Agent 直接执行：

```bash
qiaoya auth login
```

不要让用户自己复制命令；用户只需要在浏览器里完成授权。

## 接口失败或网络失败

处理方式：

- 明确告诉用户当前无法获取实时数据
- 不要编造接口结果
- 可以建议稍后重试
- 如果是测试环境，可使用 `--base-url <url>` 指定 API 地址

## 安装下载慢

当前官网安装入口从 `https://code.xhyovo.cn` 下载二进制。正常情况下不依赖 GitHub。如果下载仍然慢，可能是服务器网络、CDN 或本地网络问题。

## 版本过旧

运行：

```bash
qiaoya version
qiaoya update
```

`update` 会提示重新执行一行安装命令。
