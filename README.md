# qiaoya-cli

敲鸭社区用户端 CLI 仓库。

主程序位于：

- `agent-harness`

推荐安装方式：

```bash
pipx install "git+https://github.com/xhyqaq/qiaoya-cli.git#subdirectory=agent-harness"
```

安装后可直接使用：

```bash
qiaoya --help
qiaoya auth login -e you@example.com -p 'password'
qiaoya public course-list
qiaoya ai-news today
```

也可以用一键安装脚本：

```bash
curl -fsSL https://raw.githubusercontent.com/xhyqaq/qiaoya-cli/main/agent-harness/install.sh | bash
```

升级：

```bash
pipx upgrade cli-anything-qiaoya
```

CI 会在 push / PR 时自动校验：

- pytest
- `bash -n agent-harness/install.sh`
- `pipx install ./agent-harness`
- `bash agent-harness/install.sh` 安装脚本路径
- `qiaoya --help` 入口命令
