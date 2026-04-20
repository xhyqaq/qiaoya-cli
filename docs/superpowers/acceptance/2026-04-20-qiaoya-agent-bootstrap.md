# Acceptance Criteria: Qiaoya Agent Bootstrap

**Spec:** `docs/superpowers/specs/2026-04-20-qiaoya-agent-bootstrap-design.md`
**Date:** 2026-04-20
**Status:** Approved

---

## Criteria

| ID | Description | Test Type | Preconditions | Expected Result |
|----|-------------|-----------|---------------|-----------------|
| AC-001 | 根目录存在 npm bootstrap 包，并暴露 `qiaoya` 命令 | API | 仓库包含 `package.json` | `node bin/qiaoya.js --help` 返回 0 且输出安装说明 |
| AC-002 | `qiaoya install` 能把 skill 写入 Codex skills 目录 | Logic | 提供临时 Codex home | 安装后 `<codex-home>/skills/qiaoya/SKILL.md` 存在 |
| AC-003 | `qiaoya install` 能为 runtime 生成正确的 `pipx install/upgrade` 流程 | Logic | mock `pipx`、`python3` 和本地 source | 测试验证命令拼接与调用顺序正确 |
| AC-004 | `qiaoya doctor` 输出 Python、pipx、Codex home、skill、runtime 的检查结果 | API | 运行 bootstrap 命令 | 输出包含上述检查项并返回 0 |
| AC-005 | Skill 明确覆盖欢迎页课程与 AI 日报的触发条件 | Logic | 打开 skill 文件 | `SKILL.md` 中存在相应触发描述和命令示例 |
| AC-006 | README 说明 `npx qiaoya` 的 agent-first 用法 | API | 打开 README | README 包含 `npx qiaoya`、Codex skill、Python runtime 依赖说明 |
| AC-007 | CI 同时校验 Python runtime 与 Node bootstrap | Logic | 工作流文件存在 | CI 包含 pytest、Node 测试和 bootstrap help/安装校验步骤 |

