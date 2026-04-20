# Qiaoya Agent Bootstrap Design

**Date:** 2026-04-20
**Status:** Approved

## Context

当前仓库只有 Python runtime：`agent-harness/` 下的 `qiaoya` CLI。它适合直接调用 API，但不适合 agent-first 分发场景。目标体验不是让人手动执行 `pipx install`，而是让 agent 宿主通过一条命令：

```bash
npx qiaoya
```

完成 skill 安装和 runtime 接入。

首版只面向 Codex，不扩展到 Claude Code、Cursor、OpenCode。欢迎页课程与 AI 日报保留，因为它们是 agent 做语义总结的高价值入口。

## Scope

纳入范围：

- 根目录新增 npm bootstrap 包
- `npx qiaoya` 默认执行安装流程
- 安装 Codex skill 到 `~/.codex/skills/qiaoya`
- 使用现有 Python runtime，并通过 `pipx` 安装或升级
- 提供 `--help`、`install`、`doctor` 等最小命令面
- 增加 Node 测试与 CI 校验

排除范围：

- 多 agent 安装器适配
- Python runtime 改写为 Node
- 多平台独立二进制发布
- 远程下载预编译 runtime

## Architecture

系统拆成三层：

1. **runtime**
   现有 `agent-harness/` 下的 Python `qiaoya` CLI，继续负责 API 调用和 JSON 输出。

2. **skill**
   新增仓库内 `skills/qiaoya/SKILL.md`，描述何时调用 `qiaoya public course-list`、`qiaoya ai-news today` 等命令。

3. **bootstrap**
   新增 npm 包，入口命令为 `qiaoya`。默认行为等同于 `qiaoya install`，负责：
   - 检测 Codex home
   - 安装/覆盖 skill 文件
   - 检测 `python3` 与 `pipx`
   - 通过 `pipx install` 或 `pipx upgrade` 接入 runtime
   - 执行 `qiaoya --help` 自检

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
- `--force`

其中 `--runtime-source` 主要用于本地开发与 CI，允许从本地 `agent-harness` 安装，而不是强依赖 GitHub。

## Skill Design

`skills/qiaoya/SKILL.md` 只描述触发条件和操作约定，不重复 runtime 实现细节。重点包括：

- 当用户询问欢迎页课程、课程推荐、课程总结时使用 `qiaoya public course-list`
- 当用户询问 AI 日报、今日 AI 资讯、往期 AI 日报时使用 `qiaoya ai-news ...`
- 优先使用 `--json` 获取结构化结果，再总结给用户
- 登录态能力只在确有需要时使用

## Testing

新增 Node 侧测试，覆盖：

- skill 安装路径与文件复制
- runtime 安装命令拼接
- `doctor` 输出
- CLI 帮助输出

CI 扩展为同时运行：

- 现有 Python pytest
- Node 测试
- `node bin/qiaoya.js --help`
- 使用本地 `agent-harness` 作为 runtime source 的安装 dry-run 或真实安装校验

## Risks

- 首版仍依赖 Python runtime，因此 agent 宿主没有 `python3 + pipx` 时安装会失败
- `npx qiaoya` 解决的是 bootstrap 体验，不等于消除 Python 运行时依赖
- 未来若要进一步接近截图中的“零依赖感”，需要独立二进制或 Node runtime
