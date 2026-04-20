# qiaoya

敲鸭社区用户端 CLI，默认对接 `https://code.xhyovo.cn/`，无子命令时进入 REPL。

## 安装

### 方式一：本地开发环境

在 `agent-harness` 下执行：

```bash
pip install -e .
```

安装后可直接运行：

```bash
qiaoya --help
```

### 方式二：从 GitHub 安装给日常使用

推荐让用户用 `pipx` 安装。这样安装后可以直接全局使用 `qiaoya`，不用手动进项目目录，也不用自己管理虚拟环境。

先安装 `pipx`：

```bash
brew install pipx
pipx ensurepath
```

然后从 GitHub 安装：

```bash
pipx install "git+https://github.com/xhyqaq/qiaoya-cli.git#subdirectory=agent-harness"
```

安装完成后直接使用：

```bash
qiaoya --help
qiaoya auth login -e you@example.com -p 'password'
qiaoya post list
qiaoya public course-list
```

或者直接使用仓库自带安装脚本：

```bash
curl -fsSL https://raw.githubusercontent.com/xhyqaq/qiaoya-cli/main/agent-harness/install.sh | bash
```

升级：

```bash
pipx upgrade cli-anything-qiaoya
```

## 常用示例

登录：

```bash
qiaoya auth login -e you@example.com -p 'password'
```

查看帖子和课程：

```bash
qiaoya post list
qiaoya course list
qiaoya course get <course-id>
qiaoya public course-list
qiaoya public plans
```

查看会话和通知：

```bash
qiaoya session list
qiaoya notification unread
qiaoya notification read-all
```

前台扩展能力：

```bash
qiaoya public about
qiaoya public stats
qiaoya ai-news today
qiaoya ai-news history
qiaoya chat rooms
qiaoya chat send <room-id> --content '你好'
qiaoya unread summary
qiaoya resource access-url <resource-id>
```

进入交互模式：

```bash
qiaoya
```

## 说明

- 安装后同时提供两个命令：`qiaoya` 和 `cli-anything-qiaoya`。推荐日常使用 `qiaoya`，旧命令保留兼容。
- 如果是发布给其他人使用，优先推荐 `pipx install`，这样用户安装后可以直接全局执行 `qiaoya`。
- 仓库提供了 [install.sh](../../../install.sh) 作为一键安装脚本，内部同样走 `pipx`。
- 当前保留邮箱密码登录与用户态前台内容命令。
- `--json` 会尽量输出结构化结果，方便脚本消费。
- 已登录会话会保存到 `~/.cli-anything-qiaoya/session.json`，其中包含 `token`、`user` 和 `device_id`。
- 资源命令当前提供列表和访问 URL 生成，不模拟浏览器 Cookie jar 下载行为。
- GitHub Actions 会自动校验 pytest、`install.sh`、`pipx install` 和 `qiaoya --help`，用于保证发布后新用户安装链路可用。
