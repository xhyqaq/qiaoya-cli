---
name: qiaoya
description: Use when the user asks about qiaoya community courses, welcome-page course recommendations, AI news digests, or when Codex should query qiaoya APIs through the local qiaoya runtime.
---

# Qiaoya

## Overview

这个 skill 让 Codex 通过本地 `qiaoya` runtime 查询敲鸭社区的公开课程、AI 日报和用户态能力。优先使用结构化 JSON 输出，再基于结果做总结。

## When to Use

- 用户让你总结欢迎页课程或欢迎页有哪些课程
- 用户问哪些课程适合 AI 深度使用者
- 用户让你看今天 AI 日报或往期 AI 日报
- 用户明确要求用 `qiaoya` runtime 查询敲鸭社区数据

## Commands

公开课程：

```bash
qiaoya public course-list --json
qiaoya public course-get <course-id> --json
```

AI 日报：

```bash
qiaoya ai-news today --json
qiaoya ai-news history --json
qiaoya ai-news daily --date 2026-04-20 --json
```

用户态命令仅在确有必要时使用，并先确认本地已经登录：

```bash
qiaoya auth status
qiaoya notification unread --json
```

## Guidance

- 先用 `--json` 拉取结构化结果，再总结给用户
- 做课程推荐时，优先对比标题、标签、描述、适用人群
- 做 AI 日报总结时，优先提炼主题、趋势和与用户目标相关的内容
- 如果 `qiaoya` 命令不存在，提示需要先运行 `npx qiaoya`
