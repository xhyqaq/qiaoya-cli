# Qiaoya Frontend API Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. It will decide whether each batch should run in parallel or serial subagent mode and will pass only task-local context to each subagent. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补齐用户端前台 API 的 CLI 暴露面，并加入安装链路可回归的 GitHub Actions。

**Architecture:** 继续沿用单文件 Click CLI + `QiaoyaClient` HTTP 封装。先用测试锁定新增 API 契约，再扩展 client、命令组、README 和 CI，避免命令名与真实前端 service 偏离。

**Tech Stack:** Python 3.10+, Click, requests, pytest, GitHub Actions, pipx

---

### Task 1: 补失败测试

**Files:**
- Modify: `agent-harness/cli_anything/qiaoya/tests/test_core.py`
- Modify: `agent-harness/cli_anything/qiaoya/tests/test_full_e2e.py`

- [ ] 新增前台公开 API、聊天室、OAuth、未读、资源访问等代表性测试
- [ ] 先运行对应 pytest 用例，确认因缺失方法或命令而失败

### Task 2: 扩展 QiaoyaClient

**Files:**
- Modify: `agent-harness/cli_anything/qiaoya/utils/api_client.py`

- [ ] 新增公开能力、AI 资讯、聊天室、OAuth、资源访问、题库、评价、未读等方法
- [ ] 保持 `auth=False` 与 `auth=True` 语义清晰
- [ ] 运行 `test_core.py`，确认新增方法全部通过

### Task 3: 扩展 CLI 命令组

**Files:**
- Modify: `agent-harness/cli_anything/qiaoya/qiaoya_cli.py`

- [ ] 新增命令组与文本输出辅助函数
- [ ] 为现有 `auth` / `user` 命令补齐设置与会话命令
- [ ] 运行 `test_full_e2e.py`，确认入口和代表性命令可用

### Task 4: 文档与发布校验

**Files:**
- Modify: `agent-harness/cli_anything/qiaoya/README.md`
- Create: `.github/workflows/ci.yml`

- [ ] 更新 README 的命令示例与安装说明
- [ ] 新增 GitHub Actions，校验测试、安装脚本、`pipx install` 和入口命令

### Task 5: 完整验证与提交

**Files:**
- Modify: `agent-harness/cli_anything/qiaoya/tests/*`
- Modify: `agent-harness/cli_anything/qiaoya/*`
- Modify: `.github/workflows/ci.yml`
- Modify: `agent-harness/cli_anything/qiaoya/README.md`

- [ ] 运行完整 pytest
- [ ] 运行 `bash -n agent-harness/install.sh`
- [ ] 在干净 pipx 目录里验证 `pipx install ./agent-harness` 和 `qiaoya --help`
- [ ] 提交并推送到 `origin/main`
