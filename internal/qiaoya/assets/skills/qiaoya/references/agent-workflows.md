# Agent 工作流

这个文件把常见用户意图映射到 `qiaoya` 命令。Agent 应先调用 CLI，再组织答案。

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

当前 CLI 可能还没有发布/评论命令。Agent 应该：

1. 检查 CLI 是否支持相关命令
2. 如果不支持，明确说明当前 CLI 暂未开放
3. 如果未来支持，必须先 dry-run 或生成预览
4. 让用户确认最终内容
5. 再执行写入

禁止在没有用户确认时发布、评论、删除或修改内容。
