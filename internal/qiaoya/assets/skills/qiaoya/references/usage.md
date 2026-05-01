# 使用方式

常用查询命令：

```bash
~/.qiaoya/bin/qiaoya --json public overview
~/.qiaoya/bin/qiaoya --json public courses
~/.qiaoya/bin/qiaoya --json public services
~/.qiaoya/bin/qiaoya --json public update-logs
~/.qiaoya/bin/qiaoya --json ai-news today
```

登录态信息：

```bash
~/.qiaoya/bin/qiaoya auth status
~/.qiaoya/bin/qiaoya auth login
~/.qiaoya/bin/qiaoya auth logout
```

只有在用户明确同意时才执行 `auth login`。不要要求用户提供密码、token 或 Cookie。

如果用户想安装或修复：

```bash
curl -fsSL https://code.xhyovo.cn/install | sh
```
