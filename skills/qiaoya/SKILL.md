---
name: qiaoya
description: Use when the user asks about qiaoya community information, welcome-page courses, AI news, public services, or personal qiaoya data that can be queried through the local qiaoya runtime.
---

# Qiaoya

## Overview

这个 skill 让 Codex 通过当前 skill 目录下的 `scripts/qiaoya` runtime 查询敲鸭社区。目标是减少盲试：先按用户意图选择最可能命中的命令，再基于结构化结果做总结。

## When to Use

- 用户让你介绍敲鸭社区、课程、AI 日报、更新日志、服务或公开资源
- 用户让你推荐适合某类目标的课程
- 用户让你查看自己的通知、学习记录、收藏、关注、发帖、聊天室等个人能力
- 用户明确要求用 `qiaoya` runtime 查询敲鸭社区数据

## Runtime

优先使用当前 skill bundle 内的脚本：

```bash
~/.codex/skills/qiaoya/scripts/qiaoya --help
```

优先加 `--json`，先拿结构化结果，再组织回答。

## Capability Modes

公开能力默认可直接使用：
- 社区介绍：`public about`、`public stats`
- 欢迎页课程：`public course-list`、`public course-get`
- AI 日报：`ai-news today`、`ai-news history`、`ai-news daily`
- 服务与方案：`public services`、`public plans`、`public app-plans`
- 更新日志：`public update-logs`、`public update-log`
- 公开评价与资源：`public testimonials`、`resource access-url`

登录后能力通常包括：
- 用户信息、通知、会话、学习记录、课程进度
- 收藏、关注、点赞、帖子、评论
- 聊天室、订阅激活、我的评价、我的面试题等

## Preferred Playbooks

下面是默认首选路径，不是完整白名单。若默认路径信息不足，再用 `qiaoya --help` 或对应命令组 `--help` 扩展。

- 介绍社区：先 `public about`，再按需补 `public stats`
- 看课程列表或欢迎页课程：先 `public course-list`
- 推荐课程：先 `public course-list`，只在需要展开某门课时再用 `public course-get`
- 今天 AI 日报：先 `ai-news today`
- 指定日期日报：用 `ai-news daily --date <date>`
- 最近更新：先 `public update-logs`
- 服务说明：先 `public services`，涉及套餐再补 `public plans`
- 个人任务：先 `auth status`，已登录后再进入 `notification`、`learning`、`post`、`chat` 等命令组

## Login Guidance

当任务明显需要登录态时，先检查：

```bash
~/.codex/skills/qiaoya/scripts/qiaoya auth status
```

若未登录，不要继续盲试用户态接口。直接向用户要登录信息：

> 这个请求需要先登录敲鸭社区。请提供你的邮箱和密码，我登录后继续处理。

如果用户不想登录，再退回公开能力。

## Working Style

- 优先少量、命中率高的请求，不要为一个简单问题连续试很多相似接口
- 先返回结论，再给依据
- 课程类问题优先总结适合谁、为什么、建议从哪门开始
- 若当前命令组不够用，主动查看 `~/.codex/skills/qiaoya/scripts/qiaoya <group> --help`
- 如果 `scripts/qiaoya` 不存在，提示先运行 `npx qiaoya install`
