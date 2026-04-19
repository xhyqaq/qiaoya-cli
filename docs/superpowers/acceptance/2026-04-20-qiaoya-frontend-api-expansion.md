# Acceptance Criteria: Qiaoya Frontend API Expansion

**Spec:** `docs/superpowers/specs/2026-04-20-qiaoya-frontend-api-expansion-design.md`
**Date:** 2026-04-20
**Status:** Approved

---

## Criteria

| ID | Description | Test Type | Preconditions | Expected Result |
|----|-------------|-----------|---------------|-----------------|
| AC-001 | `public` 命令组提供公开课程、套餐、统计、独立服务、评价、更新日志相关子命令 | API | 安装 CLI 包 | `qiaoya public --help` 输出中包含对应子命令 |
| AC-002 | `ai-news` 命令组支持今日摘要、历史分页、按日期分页、详情 | API | 安装 CLI 包 | 代表性命令能调用对应 `QiaoyaClient` 方法并输出结果 |
| AC-003 | `chat` 命令组支持房间列表、加入、成员、未读、visit、消息列表、发送消息 | API | 已登录会话或测试替身 client | 代表性命令命中正确 API 路径并返回成功输出 |
| AC-004 | `oauth` 命令组支持 GitHub OAuth URL、绑定状态、绑定解绑，以及 OAuth2 客户端/授权管理 | API | 安装 CLI 包 | 代表性命令能调用正确 client 方法并输出结果 |
| AC-005 | `user` 与 `auth` 命令组补齐密码修改、邮箱通知切换、菜单码、心跳、注册/重置密码相关能力 | API | 已登录会话或测试替身 client | 代表性命令命中正确路径与 payload |
| AC-006 | `QiaoyaClient` 为新增前台 API 提供明确方法，覆盖公开接口和用户接口的鉴权差异 | Logic | 运行单元测试 | 新增核心方法的单元测试全部通过 |
| AC-007 | README 说明新增高频命令与 GitHub 安装方式 | API | 打开 README | README 包含 `pipx install`、`curl | bash` 与新增命令示例 |
| AC-008 | GitHub Actions 在 push / pull_request 时执行测试与安装链路校验 | Logic | 工作流文件存在 | 工作流包含 pytest、`bash -n install.sh`、`pipx install`、`qiaoya --help` 和安装脚本校验步骤 |

