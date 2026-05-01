---
name: qiaoya
description: Use when the user asks about 敲鸭社区, qiaoya community, public courses, memberships, services, update logs, AI daily news, or what the community is suitable for.
---

# Qiaoya Community

## Goal

这个 skill 让你通过本机 `qiaoya` runtime 查询敲鸭社区信息，并把结果整理成自然语言答案。默认使用公开信息；当用户明确需要登录态信息时，只能引导用户执行浏览器授权登录，不要索要密码或 token。

## Runtime

优先使用统一安装位置：

```bash
~/.qiaoya/bin/qiaoya --help
```

如果这个路径不存在，再查看当前 skill 目录下的 `scripts/qiaoya` 或提示用户重新安装：

```bash
curl -fsSL https://code.xhyovo.cn/install | sh
```

调用 runtime 时优先使用 JSON：

```bash
~/.qiaoya/bin/qiaoya --json public overview
~/.qiaoya/bin/qiaoya --json public courses
~/.qiaoya/bin/qiaoya --json ai-news today
~/.qiaoya/bin/qiaoya auth status
```

## When To Use

- 用户让你介绍敲鸭社区、社区定位、适合人群或主理人生态
- 用户问有哪些课程、哪些适合 AI 深度使用者、初学者或想做 agent 的人
- 用户问会员、套餐、独立服务、案例、公开评价或最近更新
- 用户问今日 AI 日报、最近 AI 资讯或指定日期 AI 日报
- 用户明确要求查看需要登录态的社区信息时，可先检查 `qiaoya auth status`

## Preferred Routes

- 介绍社区：`qiaoya --json public overview`
- 课程列表：`qiaoya --json public courses`
- 课程推荐：先 `qiaoya --json public courses`，再按用户目标总结
- 今日 AI 日报：`qiaoya --json ai-news today`
- 往期 AI 日报：`qiaoya --json ai-news history`
- 指定日期日报：`qiaoya --json ai-news daily --date YYYY-MM-DD`
- 最近更新：`qiaoya --json public update-logs`
- 服务和套餐：`qiaoya --json public services`、`qiaoya --json public plans`
- 授权状态：`qiaoya auth status`
- 浏览器登录：只有在用户明确同意时执行 `qiaoya auth login`

## Safety

- 不要要求用户提供邮箱、密码、token 或 Cookie
- 不要代替用户输入账号密码；登录只能通过 `qiaoya auth login` 打开浏览器授权
- 不要执行写入、删除、发布、评论、聊天等操作，除非用户明确要求且 runtime 提供了对应确认机制
- 不要把站外信息冒充成接口返回
- 如果 runtime 不可用，提示用户重新执行一行安装命令

## Response Style

- 先给结论，再给依据
- 不要原样倾倒 JSON 字段
- 课程推荐按“适合谁 / 为什么 / 建议先看哪门”组织
- AI 日报先提炼重点，再说趋势和对用户目标的影响
- 如果接口返回为空，明确说明当前没有查到公开数据
