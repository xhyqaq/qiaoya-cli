# Qiaoya CLI Test Notes

## 本地验证

在 `qiaoya-community-cli/agent-harness` 下运行：

```bash
pytest cli_anything/qiaoya/tests/test_full_e2e.py -q
```

## 覆盖范围

- `cli-anything-qiaoya --help`
- 无子命令 REPL 退出路径
- `auth login` / `auth logout`
- 会话、通知、帖子、评论、点赞、收藏、关注、课程、章节、学习、订阅命令
- `--json` 输出

## 说明

- e2e 默认使用 `CliRunner` 和 monkeypatch 的假客户端，不依赖真实网络。
- 只有在设置 `QIAOYA_LIVE_SMOKE=1` 时，才运行公开接口 smoke。
- 首版不覆盖受保护资源下载。
