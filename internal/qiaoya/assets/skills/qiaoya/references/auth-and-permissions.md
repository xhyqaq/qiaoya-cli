# 登录与权限

敲鸭 CLI 使用浏览器授权登录。Agent 不能接触用户密码、token、Cookie 或浏览器会话。

## 登录状态

查询登录状态：

```bash
qiaoya --json auth status
```

可能结果：

- 已登录：可以调用需要登录态的只读接口
- 未登录：只能调用公开接口；如果当前任务确实需要登录态，Agent 直接执行浏览器授权登录
- Access Token 已过期：CLI 通常会尝试用 Refresh Token 自动刷新
- Refresh Token 失效：需要用户重新授权

## 登录流程

当前任务需要登录且尚未登录时，由 Agent 执行：

```bash
qiaoya auth login
```

CLI 会：

1. 启动本地随机端口回调服务
2. 打开敲鸭授权页
3. 用户在浏览器中使用已有账号登录
4. 授权成功后保存凭据到本地

不要让用户自己复制登录命令。用户只负责在打开的浏览器页面完成登录和授权。不要让用户把授权链接、code、token 粘贴给 Agent，除非 CLI 明确要求且不会暴露敏感值。

## Token 行为

- Access Token 有较短有效期
- Refresh Token 用于自动刷新 Access Token
- 用户通常不需要频繁重新登录
- 用户执行 `qiaoya auth logout` 后，本地凭据会被移除

## 权限边界

公开命令：

```bash
qiaoya --json public overview
qiaoya --json public courses
qiaoya --json public services
qiaoya --json ai-news today
```

可能需要登录的命令：

```bash
qiaoya --json public update-logs
```

未来写操作，例如发文章、评论、修改资料，必须满足：

- 用户明确要求
- 已登录
- OAuth scope 包含 `write`
- 用户确认最终内容
- 使用 `qiaoya --json api METHOD /api/...` 调用前台白名单接口

## 安全禁止项

- 不要索要密码
- 不要索要 token
- 不要索要 Cookie
- 不要读取浏览器本地存储
- 不要绕过授权流程
- 不要在用户未确认时执行写入操作
