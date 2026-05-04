# qiaoya-cli

敲鸭社区 Go 版 agent skill 安装器与公开信息 runtime。

目标体验：

```bash
# macOS / Linux
curl -fsSL https://code.xhyovo.cn/install | sh
```

```powershell
# Windows PowerShell
irm https://code.xhyovo.cn/install.ps1 | iex
```

用户执行一行命令后，安装器会把敲鸭社区能力写入常用 AI agent 的 skill/rules 目录。之后用户直接在 Codex、Claude Code、Cursor、Windsurf、OpenClaw 里对话即可了解社区。

## 主链路

`qiaoya` 是一个单文件 Go binary，同时负责：

- 安装 skill/rules：`qiaoya install`
- 自检：`qiaoya doctor`
- 卸载：`qiaoya uninstall`
- 提示更新：`qiaoya update`
- 浏览器授权登录：`qiaoya auth login`
- 查询公开信息：`qiaoya --json public overview`
- 查询课程：`qiaoya --json public courses`
- 查询 AI 日报：`qiaoya --json ai-news today`

普通用户不需要 Node、Python、pipx、npm 或 npx。安装脚本只依赖系统自带 shell、curl 和 SHA256 校验命令。

## 支持的 Agent

默认安装：

```bash
qiaoya install --agents auto
```

写入位置：

```text
Codex        ~/.codex/skills/qiaoya/SKILL.md
Claude Code  ~/.claude/skills/qiaoya/SKILL.md
OpenClaw     ~/.openclaw/skills/qiaoya/SKILL.md
Cursor       <project>/.cursor/rules/qiaoya.mdc
Windsurf     ~/.codeium/windsurf/memories/global_rules.md
Windsurf     <project>/.windsurf/rules/qiaoya.md
```

Cursor 是项目级 rules。Windsurf 会写入全局规则；如果检测到项目目录，也会同时写入工作区规则。若要显式安装项目规则：

```bash
qiaoya install --agents cursor,windsurf --project-dir /path/to/project
```

## 安装脚本

macOS / Linux：

```bash
curl -fsSL https://code.xhyovo.cn/install | sh
```

Windows PowerShell：

```powershell
irm https://code.xhyovo.cn/install.ps1 | iex
```

脚本会：

1. 识别系统和 CPU 架构
2. 下载对应 `qiaoya-*` 单文件 binary
3. 下载并校验 `checksums.txt`
4. 运行 `qiaoya install --agents auto`
5. 把 runtime 固定安装到 `~/.qiaoya/bin/qiaoya`

可选环境变量：

```bash
QIAOYA_RELEASE_BASE_URL=https://github.com/xhyqaq/qiaoya-cli/releases/latest/download
QIAOYA_AGENTS=codex,claude,cursor,windsurf,openclaw
QIAOYA_PROJECT_DIR=/path/to/project
```

## 登录设计

登录态能力走浏览器授权，不让 AI 或 CLI 直接接触用户密码。

1. CLI 执行 `qiaoya auth login`
2. CLI 在本机随机打开一个临时 callback 端口，例如 `http://127.0.0.1:<port>/callback`
3. CLI 生成 `state`、PKCE `code_verifier/code_challenge`
4. CLI 打开敲鸭现有授权链接，例如 `https://code.xhyovo.cn/api/public/oauth2/authorize?...`
5. 用户在浏览器里使用已有敲鸭账号登录；如果已经登录，直接进入授权确认页
6. 用户确认授权后，网站把一次性授权码重定向回本机 callback
7. CLI 校验 `state`，再用授权码和 `code_verifier` 换取短期、低权限 token，并存到本机安全位置

常用命令：

```bash
qiaoya auth login
qiaoya auth status
qiaoya auth logout
```

Access Token 默认短期有效，Refresh Token 默认长期有效。CLI 会在登录态命令执行前自动刷新 Access Token；只有 Refresh Token 也失效或被撤销时，用户才需要重新执行 `qiaoya auth login`。

无论哪种方案，skill 都不应该要求邮箱、密码、token 或 Cookie。登录态能力默认按 scope 授权，并对写操作继续要求用户确认。

社区项目已经有 `/oauth2/authorize` 授权页和 `/api/public/oauth2/token` 令牌端点。`qiaoya-cli` 注册为 public OAuth2 client，使用 `client_authentication_method=none + PKCE`，CLI 不内置 `client_secret`。CLI 本机 callback 使用随机端口，因此后端 redirect URI 校验只允许 `127.0.0.1` 或 `localhost` 加固定 path，端口允许变化。

## 开发

```bash
go test ./...
go vet ./...
go build -o /tmp/qiaoya ./cmd/qiaoya
/tmp/qiaoya --help
/tmp/qiaoya install --dry-run --agents all --project-dir "$PWD"
```

## Release

推送 `v*` tag 或手动触发 `.github/workflows/release-binaries.yml` 会构建：

```text
qiaoya-darwin-arm64
qiaoya-darwin-amd64
qiaoya-linux-amd64
qiaoya-linux-arm64
qiaoya-windows-amd64.exe
qiaoya-windows-arm64.exe
checksums.txt
```

安装脚本默认从 GitHub Release `latest/download` 下载这些资产。后续如果要使用自有域名或 CDN，只需要让 `https://code.xhyovo.cn/install` 返回 `scripts/install.sh`，并把 release asset 反代或同步到稳定地址。
