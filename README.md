# qiaoya-cli

面向 agent 的敲鸭社区 bootstrap 仓库。

这个仓库现在分成两层：

- `agent-harness/`
  Python runtime，负责真实 API 调用
- 根目录 npm bootstrap
  负责 `npx qiaoya` 安装 Codex skill 和 runtime

## Agent-First 用法

推荐入口：

```bash
npx qiaoya
```

它会做这些事：

- 安装 Codex skill 到 `~/.codex/skills/qiaoya`
- 用 `pipx` 安装或更新 `qiaoya` runtime
- 做一次基础自检

也可以显式执行：

```bash
npx qiaoya install
npx qiaoya doctor
```

## Runtime 说明

当前 bootstrap 安装的是现有 Python runtime，所以目前仍然需要：

- `python3`
- `pipx`

runtime 安装后可直接调用：

```bash
qiaoya public course-list --json
qiaoya ai-news today --json
```

## 欢迎页课程与 AI 日报

这是当前 skill 的两个高价值入口：

- 欢迎页课程：让 agent 总结有哪些课程、哪些适合 AI 深度使用者
- AI 日报：让 agent 总结今日/往期 AI 资讯

## 开发

Node bootstrap：

```bash
npm test
node bin/qiaoya.js --help
```

Python runtime：

```bash
cd agent-harness
pytest cli_anything/qiaoya/tests/test_core.py cli_anything/qiaoya/tests/test_full_e2e.py -q
```

## CI

CI 会同时校验：

- Node bootstrap 测试
- `node bin/qiaoya.js --help`
- Python runtime pytest
- `bash -n agent-harness/install.sh`
- 本地 `pipx` 安装 runtime
