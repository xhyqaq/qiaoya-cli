# FAQ

## 用户需要安装 Node 或 Python 吗？

不需要。普通用户通过一行安装命令下载单文件 `qiaoya` runtime，并安装对应 AI 工具的 skill/rules。

## 支持登录吗？

支持浏览器授权登录。执行 `qiaoya auth login` 后，CLI 会打开敲鸭授权页，用户在浏览器里使用已有账号登录并确认授权。不要让 AI、CLI 或对话窗口接触邮箱、密码、token 或 Cookie。

## Access Token 过期后要重新登录吗？

通常不用。CLI 会使用本地保存的 Refresh Token 自动刷新 Access Token。只有 Refresh Token 失效、被撤销或用户执行 `qiaoya auth logout` 后，才需要重新 `qiaoya auth login`。
