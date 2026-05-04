# Agent 工作流

这个文件把常见用户意图映射到 `qiaoya` 命令。Agent 应先调用 CLI，再组织答案。

## 使用前检查版本

每次开始处理敲鸭相关任务时，先运行：

```bash
qiaoya --json version
```

如果返回的 `updateAvailable` 为 `true`，先提示用户执行 `installCommand` 更新。不要在旧 runtime 上强行使用新命令。

## 用户问“敲鸭是什么？”

运行：

```bash
qiaoya --json public overview
```

回答结构：

- 一句话定位
- 适合人群
- 主要课程或服务
- 最近更新或亮点
- 用户下一步可以做什么

## 用户问“有哪些课程？”

运行：

```bash
qiaoya --json public courses
```

回答结构：

- 按难度或目标分组
- 每组说明适合谁
- 给出建议学习顺序
- 如果用户目标不清楚，先给通用建议，再问一个澄清问题

## 用户问某门课程最近更新了什么

如果已知课程 ID，直接运行：

```bash
qiaoya --json public chapters --course-id <courseId>
```

如果只知道课程名，先查课程列表，找到最匹配课程 ID：

```bash
qiaoya --json public courses
```

然后再查章节列表。回答时按章节的创建时间或排序组织，不要说 CLI 未提供章节接口。

## 用户问某个视频章节讲了什么

先确认用户已登录：

```bash
qiaoya --json auth status
```

如果未登录，直接运行：

```bash
qiaoya auth login
```

然后读取章节详情和文字稿：

```bash
qiaoya --json api GET /api/app/chapters/<chapterId>
qiaoya --json api GET /api/app/chapters/<chapterId>/transcript
```

回答规则：

- `SUCCEEDED`：优先用 `summary` 和 `keyPoints` 回答。
- 用户需要学习笔记、时间线或细节时，再使用 `segments`。
- 用户问“视频里什么时候讲到某点”时，引用 `segments[].startMs` 对应的时间点。
- `NOT_GENERATED`：说明当前章节还没有生成文字稿。
- `PENDING`、`SUBMITTED`、`RUNNING`：说明文字稿正在生成中。
- `FAILED`、`CANCELLED`：说明文字稿暂不可用。
- Agent 不触发后台转写、重试或重新生成。

## 用户要把视频章节整理成学习笔记

读取文字稿：

```bash
qiaoya --json api GET /api/app/chapters/<chapterId>/transcript
```

组织输出：

- 先给 1 段总览。
- 再列知识点。
- 最后按时间轴分段整理学习笔记。
- 不要把完整文字稿原样倾倒给用户，除非用户明确要求。

## 用户问“我适合学哪门？”

先判断用户目标。如果信息不足，可以问一句：

```text
你现在更想补基础、做项目、学习 AI 工具，还是做 Agent/自动化？
```

然后运行：

```bash
qiaoya --json public courses
```

回答结构：

- 推荐 1 到 3 门
- 每门说明为什么适合
- 给出先后顺序
- 明确哪些暂时不建议先学

## 用户问会员、服务或套餐

运行：

```bash
qiaoya --json public services
qiaoya --json public plans
```

回答结构：

- 先说明可选项
- 再按用户目标推荐
- 涉及价格、权益、有效期时必须以 CLI 返回为准

## 用户问最近更新

先运行：

```bash
qiaoya --json auth status
```

如果已登录：

```bash
qiaoya --json public update-logs
```

如果未登录：

```bash
qiaoya auth login
```

Agent 应直接运行登录命令。用户只需要在打开的浏览器授权页完成登录和确认，不要让用户自己复制命令。

## 用户问 AI 日报

今日日报：

```bash
qiaoya --json ai-news today
```

历史日报：

```bash
qiaoya --json ai-news history
```

指定日期：

```bash
qiaoya --json ai-news daily --date YYYY-MM-DD
```

回答结构：

- 先列 3 到 5 个重点
- 再总结趋势
- 最后说明对开发者、学习者或用户目标的影响

## 用户要求登录

先解释登录方式：

```text
登录会打开敲鸭授权页，你在浏览器里使用已有账号确认授权；我不会接触你的密码或 token。
```

然后由 Agent 运行：

```bash
qiaoya auth login
```

登录后检查：

```bash
qiaoya --json auth status
```

## 用户要发文章或评论

使用通用前台 API 命令。先整理内容，给用户确认最终文本，再提交。

评论示例：

```bash
qiaoya --json api POST /api/user/comments --body '{"businessType":"POST","businessId":"<postId>","content":"评论内容"}'
```

文章示例：

```bash
qiaoya --json api POST /api/user/posts --body '{"title":"标题","content":"正文","summary":"概要","categoryId":"<categoryId>","tags":["AI"]}'
qiaoya --json api PATCH /api/user/posts/<postId>/status --body '{"status":"PUBLISHED"}'
```

禁止在没有用户确认时发布、评论、删除或修改内容。
