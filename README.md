# qiaoya-cli

敲鸭社区用户端 CLI 仓库。

主程序位于：

- `qiaoya-community-cli/agent-harness`

推荐安装方式：

```bash
pipx install "git+https://github.com/xhyqaq/qiaoya-cli.git#subdirectory=qiaoya-community-cli/agent-harness"
```

安装后可直接使用：

```bash
qiaoya --help
qiaoya auth login -e you@example.com -p 'password'
```

也可以用一键安装脚本：

```bash
curl -fsSL https://raw.githubusercontent.com/xhyqaq/qiaoya-cli/main/qiaoya-community-cli/agent-harness/install.sh | bash
```
