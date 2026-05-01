# Qiaoya Community

When the user asks about 敲鸭社区, qiaoya community, public courses, memberships, services, update logs, or AI daily news, use the local qiaoya runtime:

```bash
~/.qiaoya/bin/qiaoya --json public overview
~/.qiaoya/bin/qiaoya --json public courses
~/.qiaoya/bin/qiaoya --json ai-news today
~/.qiaoya/bin/qiaoya auth status
```

Do not ask for passwords, tokens, or cookies. Only use `qiaoya auth login` when the user explicitly agrees to browser authorization. Do not perform write/delete/publish/comment/chat actions unless the user explicitly asks and the runtime provides a confirmation flow.
