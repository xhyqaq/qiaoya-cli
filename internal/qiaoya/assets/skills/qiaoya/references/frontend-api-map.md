# 前台 API 速查

所有命令优先加 `--json`。通用格式：

```bash
qiaoya --json api METHOD /api/path --body '{...}'
```

`api` 命令只用于前台接口。不要调用 `/api/admin/**`、`/api/auth/**`、OAuth token/callback、OSS/CDN 回调端点。

## 公开信息

```bash
qiaoya --json api GET /api/public/site/about
qiaoya --json api GET /api/public/site/plus-guide-config
qiaoya --json api GET /api/public/stats/users
qiaoya --json api POST /api/public/courses/queries --body '{"pageNum":1,"pageSize":20}'
qiaoya --json api GET /api/public/courses/<courseId>
qiaoya --json api GET /api/public/subscription-plans
qiaoya --json api GET /api/public/independent-services
qiaoya --json api GET /api/public/independent-services/<serviceCode>
qiaoya --json api GET /api/public/testimonials
```

课程详情推荐优先用友好命令：

```bash
qiaoya --json public course --id <courseId>
qiaoya --json public chapters --course-id <courseId>
```

## 课程与章节

```bash
qiaoya --json api POST /api/app/courses/queries --body '{"pageNum":1,"pageSize":20}'
qiaoya --json api GET /api/app/courses/<courseId>
qiaoya --json api GET /api/app/chapters/latest
qiaoya --json api GET /api/app/chapters/<chapterId>
qiaoya --json api POST /api/user/learning/progress/report --body '{"courseId":"<courseId>","chapterId":"<chapterId>","progress":100}'
qiaoya --json api GET /api/user/learning/progress/<courseId>
qiaoya --json api GET '/api/user/learning/records?pageNum=1&pageSize=10'
```

## 文章、分类、评论

```bash
qiaoya --json api GET '/api/app/categories/tree?type=ARTICLE'
qiaoya --json api POST /api/app/posts/queries --body '{"pageNum":1,"pageSize":20}'
qiaoya --json api POST /api/app/posts/user/<userId>/queries --body '{"pageNum":1,"pageSize":20}'
qiaoya --json api GET /api/app/posts/<postId>
qiaoya --json api GET '/api/app/comments?businessType=POST&businessId=<postId>&pageNum=1&pageSize=10'
qiaoya --json api GET '/api/app/comments/user/<userId>?pageNum=1&pageSize=10'
```

写操作必须来自用户明确要求，执行前确认最终内容：

```bash
qiaoya --json api POST /api/user/posts --body '{"title":"标题","content":"正文","summary":"概要","categoryId":"<categoryId>","tags":["AI"]}'
qiaoya --json api PUT /api/user/posts/<postId> --body '{"title":"标题","content":"正文","categoryId":"<categoryId>"}'
qiaoya --json api PATCH /api/user/posts/<postId>/status --body '{"status":"PUBLISHED"}'
qiaoya --json api DELETE /api/user/posts/<postId>
qiaoya --json api POST /api/user/comments --body '{"businessType":"POST","businessId":"<postId>","content":"评论内容"}'
qiaoya --json api POST /api/user/comments/<commentId>/reply --body '{"content":"回复内容"}'
qiaoya --json api DELETE /api/user/comments/<commentId>
```

## 互动

```bash
qiaoya --json api POST /api/likes/toggle --body '{"targetType":"POST","targetId":"<id>"}'
qiaoya --json api GET /api/likes/status/POST/<id>
qiaoya --json api GET /api/likes/count/POST/<id>
qiaoya --json api POST /api/favorites/toggle --body '{"targetType":"POST","targetId":"<id>"}'
qiaoya --json api GET /api/favorites/status/POST/<id>
qiaoya --json api GET '/api/favorites/my?pageNum=1&pageSize=10'
qiaoya --json api POST /api/app/follows/toggle --body '{"targetType":"USER","targetId":"<userId>"}'
qiaoya --json api GET /api/app/follows/check/USER/<userId>
qiaoya --json api POST /api/reactions/toggle --body '{"businessType":"POST","businessId":"<id>","reactionType":"like"}'
qiaoya --json api GET /api/reactions/POST/<id>
qiaoya --json api GET /api/expressions/alias-map
```

## AI 日报与更新日志

```bash
qiaoya --json api GET /api/app/ai-news/today
qiaoya --json api GET '/api/app/ai-news/history?pageNum=1&pageSize=10'
qiaoya --json api GET '/api/app/ai-news/daily?date=YYYY-MM-DD&pageNum=1&pageSize=10'
qiaoya --json api GET /api/app/update-logs
qiaoya --json api GET /api/app/update-logs/<updateLogId>
```

AI 日报推荐优先用友好命令：

```bash
qiaoya --json ai-news today
qiaoya --json ai-news history
qiaoya --json ai-news daily --date YYYY-MM-DD
```

## 用户、通知、订阅

```bash
qiaoya --json api GET /api/user
qiaoya --json api GET /api/user/<userId>
qiaoya --json api PUT /api/user/profile --body '{"name":"昵称","description":"简介","avatar":"<resourceId>"}'
qiaoya --json api PUT /api/user/email-notification
qiaoya --json api POST /api/user/plus-guide/complete
qiaoya --json api GET /api/user/permissions
qiaoya --json api GET /api/user/menu-codes
qiaoya --json api GET /api/user/unread/summary
qiaoya --json api PUT '/api/user/unread/visit?channel=POSTS'
qiaoya --json api GET '/api/user/notifications?pageNum=1&pageSize=20'
qiaoya --json api GET /api/user/notifications/unread-count
qiaoya --json api PUT /api/user/notifications/<notificationId>/read
qiaoya --json api PUT /api/user/notifications/read-all
qiaoya --json api GET /api/user/subscription/subscriptions
qiaoya --json api GET /api/user/subscription/<subscriptionId>
qiaoya --json api POST /api/user/subscription/activate-cdk --body '{"cdkCode":"<cdk>"}'
```

## 资源、证言、面试题、聊天室

```bash
qiaoya --json api POST /api/user/resource/upload-credentials --body '{"originalName":"a.png","contentType":"image/png"}'
qiaoya --json api GET '/api/user/resource/?pageNum=1&pageSize=10'
qiaoya --json api POST /api/testimonials --body '{"content":"内容","rating":5}'
qiaoya --json api GET /api/testimonials/my
qiaoya --json api PUT /api/testimonials/<testimonialId> --body '{"content":"内容"}'
qiaoya --json api POST /api/interview-questions --body '{"title":"标题","description":"题目描述","answer":"参考答案","rating":3,"categoryId":"<categoryId>","tags":["Java"]}'
qiaoya --json api GET /api/interview-questions/<id>
qiaoya --json api GET '/api/interview-questions/my?pageNum=1&pageSize=10'
qiaoya --json api PATCH /api/interview-questions/<id>/status --body '{"status":"PUBLISHED"}'
qiaoya --json api DELETE /api/interview-questions/<id>
qiaoya --json api GET /api/app/chat-rooms/<roomId>/messages
qiaoya --json api POST /api/app/chat-rooms/<roomId>/messages --body '{"content":"消息内容"}'
qiaoya --json api POST /api/app/chat-rooms/<roomId>/join
qiaoya --json api POST /api/app/chat-rooms/<roomId>/leave
```
