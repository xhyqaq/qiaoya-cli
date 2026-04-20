# Qiaoya Agent Bootstrap Design

**Date:** 2026-04-20
**Status:** Approved

## Context

当前仓库只有 Python runtime：`agent-harness/` 下的 `qiaoya` CLI。它适合直接调用 API，但不适合 agent-first 分发场景。目标体验不是让人手动执行 `pipx install`，而是让 agent 宿主通过一条命令：

```bash
npx qiaoya
```

完成 skill 安装和 runtime 接入。

首版只面向 Codex，不扩展到 Claude Code、Cursor、OpenCode。欢迎页课程与 AI 日报保留，因为它们是 agent 做语义总结的高价值入口。当前实现已经具备 binary-ready 闭环：平台识别、命名规则、bundle 内 `scripts/` 安装路径、release 构建工作流都已固定；默认 `auto` 模式会先尝试二进制下载，失败再回退到 Python runtime。

## Scope

纳入范围：

- 根目录新增 npm bootstrap 包
- `npx qiaoya` 默认执行安装流程
- 安装 Codex skill 到 `~/.codex/skills/qiaoya`
- 使用现有 Python runtime，并通过 bundle 内部 `pipx` 安装到 `scripts/`
- 提供 `--help`、`install`、`doctor` 等最小命令面
- 预留二进制安装模式与 GitHub Release 资产命名规则
- 增加 release 二进制构建与上传工作流
- 增加 Node 测试与 CI 校验

排除范围：

- 多 agent 安装器适配
- Python runtime 改写为 Node
- 多平台独立二进制发布
- 远程 release 下载的校验和/验签

## Architecture

系统拆成三层：

1. **runtime**
   现有 `agent-harness/` 下的 Python `qiaoya` CLI，继续负责 API 调用和 JSON 输出。

2. **skill**
   新增仓库内 `skills/qiaoya/SKILL.md`，描述何时调用 `~/.codex/skills/qiaoya/scripts/qiaoya ...`。

3. **bootstrap**
   新增 npm 包，入口命令为 `qiaoya`。默认行为等同于 `qiaoya install`，负责：
   - 检测 Codex home
   - 安装/覆盖 skill 文件
   - 在 `auto` 模式下优先按平台下载 release 二进制
   - 若二进制不可用则检测 `python3` 与 `pipx`
   - 通过 bundle 内 `.runtime/` + `scripts/` 安装 Python runtime
   - 执行 `scripts/qiaoya --help` 自检
   - 写入 `VERSION` 与 `install-meta.json`

## CLI Design

根 npm 包命令面：

- `qiaoya` / `qiaoya install`
  默认安装 Codex skill 与 runtime
- `qiaoya doctor`
  打印 Python、pipx、Codex 目录和 runtime 检查结果
- `qiaoya help`
  打印 bootstrap 使用说明

参数：

- `--agent codex`
- `--codex-home <path>`
- `--runtime-source <path-or-spec>`
- `--binary-source <path-or-url>`
- `--runtime-kind auto|python|binary`
- `--force`

其中：

- `--runtime-source` 主要用于本地开发与 CI，允许从本地 `agent-harness` 安装 Python runtime
- `--binary-source` 用于本地假二进制或后续 release 下载入口
- `--runtime-kind` 当前默认 `auto`，会先尝试最新 release 二进制；显式指定 `binary` 时强制走 bundle 内二进制安装

## Skill Design

`skills/qiaoya/SKILL.md` 只描述触发条件和操作约定，不重复 runtime 实现细节。重点包括：

- 当用户询问欢迎页课程、课程推荐、课程总结时使用 `qiaoya public course-list`
- 当用户询问 AI 日报、今日 AI 资讯、往期 AI 日报时使用 `qiaoya ai-news ...`
- 优先使用 `--json` 获取结构化结果，再总结给用户
- 登录态能力只在确有需要时使用

## Testing

新增 Node 侧测试，覆盖：

- skill bundle 安装路径与文件复制
- runtime 安装到 `scripts/` 的命令拼接
- 二进制平台识别、命名规则与本地二进制安装
- `auto` 模式下二进制失败回退 Python runtime
- `VERSION` 与 `install-meta.json` 写入
- `doctor` 输出
- CLI 帮助输出

CI 扩展为同时运行：

- 现有 Python pytest
- Node 测试
- `node bin/qiaoya.js --help`
- 使用本地 `agent-harness` 作为 runtime source 的安装 dry-run 或真实安装校验
- 使用假二进制文件验证 `binary` 模式安装路径
- 使用 tag workflow 构建并上传 release 资产

## Risks

- 在 release 资产存在时，agent 宿主可以不依赖 Python；但当 release 缺失或下载失败时仍会回退到 Python runtime
- `npx qiaoya` 解决的是 bootstrap 体验，并通过回退逻辑保证当前仓库仍可用
- 后续若要进一步增强发布安全，需要加入校验和或签名验证
