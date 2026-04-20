# Qiaoya Agent Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. It will decide whether each batch should run in parallel or serial subagent mode and will pass only task-local context to each subagent. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `qiaoya-cli` 增加 agent-first 的 npm bootstrap 层，使 `npx qiaoya` 能安装 Codex skill 并接入现有 Python runtime。

**Architecture:** 保留 `agent-harness/` 作为 runtime，不重写业务 CLI；根目录新增 Node bootstrap，负责 skill 安装、runtime 安装和环境检查；技能说明单独放在仓库 `skills/qiaoya/` 目录中，由 bootstrap 复制到 Codex home。

**Tech Stack:** Node.js, npm/npx, Python runtime, pipx, pytest, node:test, GitHub Actions

---

### Task 1: 新增 bootstrap 文档与 npm 包骨架

**Files:**
- Create: `package.json`
- Create: `bin/qiaoya.js`
- Create: `src/bootstrap.js`
- Create: `src/installers/codex.js`
- Create: `src/runtime.js`

- [ ] 写最小可运行的 `--help` 与 install 骨架
- [ ] 先用 Node 测试锁定帮助输出和参数解析

### Task 2: 增加 Codex skill 模板与安装逻辑

**Files:**
- Create: `skills/qiaoya/SKILL.md`
- Modify: `src/installers/codex.js`

- [ ] 实现 skill 复制到 Codex home
- [ ] 测试 skill 路径、覆盖行为和文件内容

### Task 3: 接入 Python runtime 安装逻辑

**Files:**
- Modify: `src/runtime.js`
- Modify: `src/bootstrap.js`

- [ ] 检测 `python3` 与 `pipx`
- [ ] 支持从默认 GitHub spec 和本地 `--runtime-source` 安装 runtime
- [ ] 增加 `doctor` 输出

### Task 4: 更新文档与 CI

**Files:**
- Modify: `README.md`
- Modify: `.github/workflows/ci.yml`
- Create: `tests/bootstrap.test.js`

- [ ] 写 agent-first README
- [ ] 在 CI 中增加 Node 测试与 bootstrap help 校验

### Task 5: 完整验证

**Files:**
- Modify: root bootstrap files
- Modify: `agent-harness/*` if needed

- [ ] 运行 Python pytest
- [ ] 运行 Node 测试
- [ ] 运行 `node bin/qiaoya.js --help`
- [ ] 用本地 runtime source 跑一次 bootstrap 安装验证
