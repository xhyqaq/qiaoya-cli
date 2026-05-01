---
name: qiaoya
description: Use when the user asks about 敲鸭社区, qiaoya community, public courses, memberships, services, update logs, AI daily news, login status, or community content workflows.
---

# Qiaoya Community

## 目标

这个 skill 让 Agent 通过本机 `qiaoya` runtime 了解敲鸭社区，并在需要时安全调用敲鸭能力。默认只读取公开信息；涉及登录态、发布、评论等操作时，必须先确认用户意图和授权状态。

不要把社区知识写死在回答里。优先调用 CLI 获取实时数据，再结合 `references/` 中的规则和工作流组织答案。

## Runtime

优先使用统一安装位置：

```bash
~/.qiaoya/bin/qiaoya --help
```

如果 runtime 不存在，提示用户重新安装：

```bash
curl -fsSL https://code.xhyovo.cn/install | sh
```

Agent 调用 CLI 时优先使用 JSON：

```bash
~/.qiaoya/bin/qiaoya --json public overview
~/.qiaoya/bin/qiaoya --json public courses
~/.qiaoya/bin/qiaoya --json ai-news today
~/.qiaoya/bin/qiaoya --json auth status
```

## 任务路由

- 介绍社区、定位、适合人群：`qiaoya --json public overview`
- 查询课程：`qiaoya --json public courses`
- 推荐课程：先查 `public courses`，再按用户目标总结
- 查询服务、套餐：`qiaoya --json public services`、`qiaoya --json public plans`
- 查询最近更新：先 `qiaoya --json auth status`，已登录后 `qiaoya --json public update-logs`
- 查询 AI 日报：`qiaoya --json ai-news today`
- 查询往期 AI 日报：`qiaoya --json ai-news history`
- 查询指定日期日报：`qiaoya --json ai-news daily --date YYYY-MM-DD`
- 登录状态：`qiaoya --json auth status`
- 浏览器授权登录：当用户请求的任务需要登录且 `auth status` 显示未登录时，由 Agent 直接执行 `qiaoya auth login`；用户只需在打开的浏览器页面完成登录和授权

## 参考资料

需要更详细信息时读取这些文件：

- `references/cli-command-reference.md`：完整命令、参数和输出使用建议
- `references/agent-workflows.md`：常见用户意图到 CLI 命令的工作流
- `references/auth-and-permissions.md`：登录、token、权限和安全边界
- `references/about.md`：社区定位和回答原则
- `references/faq.md`：安装、环境、登录等常见问题
- `references/troubleshooting.md`：runtime 不存在、接口失败、登录失效等排障

## 安全边界

- 不要索要邮箱、密码、token、Cookie 或浏览器会话
- 不要替用户输入账号密码；登录只能由 Agent 执行 `qiaoya auth login` 打开浏览器授权，用户在浏览器里完成确认
- 不要把站外信息冒充成 CLI 或接口返回
- 不要执行写入、删除、发布、评论等操作，除非用户明确要求且 CLI 提供确认或 dry-run 机制
- 写操作出现之前，先检查 `qiaoya --json auth status`，并让用户确认最终内容

## 回答风格

- 先给结论，再给依据
- 不要原样倾倒 JSON
- 推荐课程时按“适合谁 / 为什么 / 建议先看哪门”组织
- AI 日报先提炼重点，再说明趋势和对用户目标的影响
- 如果 CLI 返回为空，明确说明当前没有查到对应公开数据
