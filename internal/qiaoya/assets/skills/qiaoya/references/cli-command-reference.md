# CLI 命令参考

Agent 调用 `qiaoya` 时优先使用 JSON，避免解析自然语言输出。

推荐路径：

```bash
~/.qiaoya/bin/qiaoya
```

如果用户环境已把 `qiaoya` 加入 PATH，也可以直接使用：

```bash
qiaoya
```

## 全局参数

```bash
qiaoya --json <command>
qiaoya --base-url <url> <command>
```

- `--json`：输出 JSON，Agent 默认使用
- `--base-url`：指定 API 地址，默认使用敲鸭线上 API

## 通用前台 API

```bash
qiaoya --json api GET /api/app/chapters/latest
qiaoya --json api GET '/api/app/comments?businessType=POST&businessId=<id>'
qiaoya --json api POST /api/app/posts/queries --body '{"pageNum":1,"pageSize":10}'
qiaoya --json api POST /api/user/comments --body '{"businessType":"POST","businessId":"<id>","content":"..."}'
qiaoya --json api PUT /api/user/profile --body '{"name":"...","description":"..."}'
qiaoya --json api GET /api/expressions/alias-map
qiaoya --json api DELETE /api/user/comments/<commentId>
```

允许的前台路径：

- `/api/public/**`
- `/api/app/**`
- `/api/user/**`
- `/api/expressions/**`
- `/api/likes/**`
- `/api/favorites/**`
- `/api/reactions/**`
- `/api/testimonials/**`
- `/api/interview-questions/**`

禁止调用 `/api/admin/**`、账号密码登录类接口、OAuth token/callback、OSS/CDN 回调这类流程型端点。登录统一使用 `qiaoya auth login`。非 public 路径需要登录态；如果本地未登录，CLI 会直接启动浏览器授权登录。写操作会请求 `write` scope，旧版只读 token 不满足时会重新授权。

## 安装和诊断

```bash
qiaoya install
qiaoya install --agents auto
qiaoya install --agents all
qiaoya install --agents codex,claude,cursor,windsurf,openclaw
qiaoya install --project-dir <path>
qiaoya --json doctor
qiaoya uninstall
qiaoya update
```

使用建议：

- 用户只想安装：提示一行命令 `curl -fsSL https://code.xhyovo.cn/install | sh`
- 用户说 Agent 没识别敲鸭：运行 `qiaoya --json doctor`
- 用户使用 Cursor 或 Windsurf：需要在项目根目录安装或传 `--project-dir`

## 登录

```bash
qiaoya --json auth status
qiaoya auth login
qiaoya auth login --no-browser
qiaoya auth logout
```

使用建议：

- 先用 `auth status` 判断是否已登录
- 当用户请求的任务需要登录且当前未登录时，Agent 直接执行 `auth login`，不要让用户自己执行命令
- 不要要求用户提供密码、token 或 Cookie
- `auth login --no-browser` 只打印授权链接，适合不能自动打开浏览器的环境

## 公开信息

```bash
qiaoya --json public overview
qiaoya --json public about
qiaoya --json public stats
qiaoya --json public courses
qiaoya --json public courses --page 1 --size 20
qiaoya --json public course --id <courseId>
qiaoya --json public chapters --course-id <courseId>
qiaoya --json public plans
qiaoya --json public app-plans
qiaoya --json public services
qiaoya --json public testimonials
qiaoya --json public update-logs
```

使用建议：

- `overview` 适合回答“敲鸭是什么”“适合谁”“整体介绍”
- `courses` 适合课程列表、课程推荐、学习路径
- `course --id` 适合获取某门课程的公开详情，包含章节列表
- `chapters --course-id` 适合只获取某门课程的章节标题、排序、阅读时长和创建时间
- `services` 和 `plans` 适合会员、服务、套餐相关问题
- `testimonials` 适合用户评价和案例
- `update-logs` 当前需要登录态，调用前先检查 `auth status`

## AI 日报

```bash
qiaoya --json ai-news today
qiaoya --json ai-news history
qiaoya --json ai-news history --page 1 --size 10
qiaoya --json ai-news daily --date YYYY-MM-DD
qiaoya --json ai-news daily --date YYYY-MM-DD --page 1 --size 10
```

使用建议：

- 用户问“今天 AI 有什么新闻”：用 `today`
- 用户问“最近 AI 动态”：用 `history`
- 用户给出明确日期：用 `daily --date YYYY-MM-DD`

## JSON 结果处理

Agent 不应该原样倾倒 JSON。建议流程：

1. 调用 CLI 获取结构化数据
2. 提取与用户问题相关的字段
3. 用自然语言总结
4. 标注数据为空、权限不足或接口失败

如果 CLI 返回错误，优先根据错误类型继续行动：

- 未登录：Agent 执行 `qiaoya auth login`，用户在浏览器里完成授权
- 网络/API 失败：说明暂时无法获取实时数据
- 命令不存在：提示升级 `qiaoya update` 或重新安装
