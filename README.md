# qiaoya-cli

面向 agent 的敲鸭社区 bootstrap 仓库。

这个仓库现在分成两层：

- `agent-harness/`
  Python runtime，负责真实 API 调用
- 根目录 npm bootstrap
  负责 `npx qiaoya` 安装 Codex skill bundle 和 runtime

## Agent-First 用法

推荐入口：

```bash
npx qiaoya
```

它会做这些事：

- 安装 Codex skill bundle 到 `~/.codex/skills/qiaoya`
- 把 runtime 放进 `~/.codex/skills/qiaoya/scripts/qiaoya`
- 用 skill bundle 内部的 `.runtime/` 承载 pipx runtime
- 做一次基础自检

也可以显式执行：

```bash
npx qiaoya install
npx qiaoya doctor
```

二进制模式骨架已经接好，但当前默认仍保留 Python runtime 路径。显式指定时可以把单文件二进制放进 skill bundle：

```bash
npx qiaoya install --runtime-kind binary --binary-source /path/to/qiaoya-binary
```

## Runtime 说明

当前 bootstrap 安装的是现有 Python runtime，所以目前仍然需要：

- `python3`
- `pipx`

后续如果 GitHub Releases 提供了平台二进制，`binary` 模式会把对应文件安装到：

```text
~/.codex/skills/qiaoya/scripts/qiaoya
```

runtime 安装后可直接调用：

```bash
~/.codex/skills/qiaoya/scripts/qiaoya public course-list --json
~/.codex/skills/qiaoya/scripts/qiaoya ai-news today --json
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
node bin/qiaoya.js install --runtime-kind binary --binary-source /tmp/qiaoya-binary
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
- skill bundle 内 runtime 安装校验
