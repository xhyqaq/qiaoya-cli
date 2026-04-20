---
name: qiaoya
description: Use when the user asks about qiaoya community information, welcome-page courses, AI news, public services, or personal qiaoya data that can be queried through the local qiaoya runtime.
---

# Qiaoya

## Overview

这个 skill 让 Codex 通过当前 skill 目录下的 `scripts/qiaoya` runtime 查询敲鸭社区。目标是降低心智负担，而不是把命令写死：先按用户意图走最可能命中的默认路径，信息不足时再主动查看 `qiaoya --help` 或对应命令组 `--help` 扩展能力。

## When to Use

- 用户让你介绍敲鸭社区、课程、AI 日报、更新日志、服务或公开资源
- 用户让你推荐适合某类目标的课程
- 用户让你查看自己的通知、学习记录、收藏、关注、发帖、聊天室等个人能力
- 用户明确要求用 `qiaoya` runtime 查询敲鸭社区数据

常见自然语言触发包括：
- “介绍一下这个社区”
- “有哪些课程”
- “哪些课程适合 AI 深度使用者 / 初学者 / 想做 agent 的人”
- “看看今天 AI 日报 / 最近 AI 日报”
- “最近有什么更新”
- “这个社区有哪些服务 / 套餐”
- “看看我的通知 / 学习记录 / 收藏 / 聊天室”

## Runtime

优先使用当前 skill bundle 内的脚本：

```bash
~/.codex/skills/qiaoya/scripts/qiaoya --help
```

优先加 `--json`，先拿结构化结果，再组织回答。注意 `--json` 是全局参数，要写在子命令前面，例如：

```bash
~/.codex/skills/qiaoya/scripts/qiaoya --json public about
~/.codex/skills/qiaoya/scripts/qiaoya --json public stats
```

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

如果用户的问题明显是公开信息，不要主动检查登录态。

## External Context

介绍社区、主理人或项目生态时，可以把下面两个公开主页当成补充上下文一起使用：
- B 站：`https://space.bilibili.com/152686439`
- GitHub：`https://github.com/xhyqaq`

用途：
- 帮用户理解主理人 `xhyovo` 的公开输出渠道
- 佐证社区和作者个人的 AI 项目实践、开源项目、内容输出之间的关系
- 在介绍社区时补充“站外内容生态”，但不要把站外信息冒充成站内接口返回

## Preferred Playbooks

下面是默认首选路径，不是完整白名单。若默认路径信息不足，再用 `qiaoya --help` 或对应命令组 `--help` 扩展。

- 介绍社区：这是少数默认允许组合多个公开接口的任务。优先聚合 `public about`、`public stats`、`public course-list`、`public plans`、`public testimonials`，必要时再补 `public services`。默认要把社区用户数、课程数量、套餐/服务、公开评价一起组织出来
- 看课程列表或欢迎页课程：先 `public course-list`
- 推荐课程：先 `public course-list`，只在需要展开某门课时再用 `public course-get`
- 今天 AI 日报：先 `ai-news today`
- 指定日期日报：用 `ai-news daily --date <date>`
- 最近更新：先 `public update-logs`
- 服务说明：先 `public services`，涉及套餐再补 `public plans`
- 个人任务：先 `auth status`，已登录后再进入 `notification`、`learning`、`post`、`chat` 等命令组

更细一点的默认路由：
- “介绍社区 / 这个社区是干嘛的”：`public about` -> `public stats` -> `public course-list` -> `public plans` -> `public testimonials` -> 必要时 `public services`
- “欢迎页有哪些课程 / 给我列课程”：`public course-list`
- “推荐几门课给我”：`public course-list` -> 必要时 `public course-get`
- “今天 AI 日报”：`ai-news today`
- “某天的 AI 日报”：`ai-news daily --date <date>`
- “最近 AI 日报 / 往期 AI 日报”：`ai-news history`
- “最近有什么更新”：`public update-logs`
- “有哪些服务 / 这个社区卖什么”：`public services`
- “我的通知 / 我的学习记录 / 我的收藏”：`auth status` -> 对应用户态命令组

## Discovery Rule

不要把这里列出的命令当成完整集合。

如果默认路径不够，按这个顺序扩展：
1. 先看根帮助：`~/.codex/skills/qiaoya/scripts/qiaoya --help`
2. 再看目标命令组帮助：`~/.codex/skills/qiaoya/scripts/qiaoya <group> --help`
3. 只有在帮助确认有更合适命令时，才追加调用

也就是说，这个 skill 提供的是“首选入口”和“减少盲试”的策略，不是白名单。

## Login Guidance

当任务明显需要登录态时，先检查：

```bash
~/.codex/skills/qiaoya/scripts/qiaoya auth status
```

若未登录，不要继续盲试用户态接口。直接向用户要登录信息：

> 这个请求需要先登录敲鸭社区。请提供你的邮箱和密码，我登录后继续处理。

如果用户不想登录，再退回公开能力，并明确说明当前仍可做课程、AI 日报、社区介绍、服务和更新日志。

登录态任务一般包括：
- 我的通知
- 我的学习记录 / 学习进度
- 我的收藏 / 关注 / 点赞状态
- 发帖 / 评论 / 删除
- 聊天室
- 当前用户资料
- 订阅激活

公开任务一般不需要登录：
- 社区介绍
- 欢迎页课程
- AI 日报
- 服务与方案
- 更新日志
- 公开评价
- 公开资源访问链接

## Working Style

- 优先少量、命中率高的请求，不要为一个简单问题连续试很多相似接口
- 先返回结论，再给依据
- 课程类问题优先总结适合谁、为什么、建议从哪门开始
- 对“介绍社区”这类 broad query，可以一次性组合少量高价值公开接口，不要过早停在单个 `about`
- 若当前命令组不够用，主动查看 `~/.codex/skills/qiaoya/scripts/qiaoya <group> --help`
- 如果 `scripts/qiaoya` 不存在，提示先运行 `npx qiaoya install`

## Response Patterns

社区介绍类：
- 默认使用公开接口做一个完整概览，而不是只复述 `about`
- 优先覆盖：主理人/社区定位、用户规模、课程供给、套餐/服务、公开评价
- `public stats` 当前代表的是用户总数，不要把 `totalCount` 解释成内容总量或站内总量
- 若接口已提供用户数、课程列表、套餐、评价，就默认直接汇总这些事实，不要把它们留到用户追问
- 介绍主理人或项目生态时，可以顺带补充 `xhyovo` 的 B 站和 GitHub，帮助用户理解社区外部内容和开源实践
- 组织顺序建议：
  1. 社区是什么、主理人是谁
  2. 当前用户规模和课程数量
  3. 课程/主题方向
  4. 套餐、服务或商业化能力
  5. 用户评价或公开口碑
  6. 必要时补充主理人的站外内容与开源入口
- 如果接口有数据，就直接写进介绍；不要只说“如果你想我可以继续查”
- 只有在这些公开接口都不足时，才追问用户想看课程、更新还是 AI 日报

课程推荐类：
- 先给推荐结论
- 再按“适合谁 / 为什么 / 建议先看哪门”组织
- 不要把原始字段逐条复述给用户

AI 日报类：
- 先提炼今天的重点
- 再说趋势或值得关注的方向
- 最后补和用户目标的关系

个人任务类：
- 先确认是否已登录
- 再直接给结果或下一步动作
- 不要把 401/认证失败 这类底层接口语言暴露给用户
