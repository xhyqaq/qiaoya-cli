#!/usr/bin/env bash

set -euo pipefail

PACKAGE_NAME="qiaoya"
REPO_URL='git+https://github.com/xhyqaq/qiaoya-cli.git#subdirectory=qiaoya-community-cli/agent-harness'

usage() {
  cat <<'EOF'
Usage:
  ./install.sh            Install qiaoya with pipx
  ./install.sh --upgrade  Upgrade existing qiaoya installation
  ./install.sh --force    Reinstall qiaoya
  ./install.sh --help     Show this help

This script installs the qiaoya CLI globally via pipx.
EOF
}

ensure_pipx() {
  if command -v pipx >/dev/null 2>&1; then
    return 0
  fi

  echo "pipx 未安装。"
  echo "macOS 可执行：brew install pipx && pipx ensurepath"
  echo "Python 环境也可执行：python3 -m pip install --user pipx && python3 -m pipx ensurepath"
  exit 1
}

install_pkg() {
  if pipx list --short 2>/dev/null | grep -Fx "${PACKAGE_NAME}" >/dev/null 2>&1; then
    echo "检测到已安装 ${PACKAGE_NAME}，改为升级。"
    pipx upgrade "${PACKAGE_NAME}"
  else
    pipx install "${REPO_URL}"
  fi
}

upgrade_pkg() {
  if pipx list --short 2>/dev/null | grep -Fx "${PACKAGE_NAME}" >/dev/null 2>&1; then
    pipx upgrade "${PACKAGE_NAME}"
  else
    echo "未检测到已安装的 ${PACKAGE_NAME}，改为安装。"
    pipx install "${REPO_URL}"
  fi
}

force_reinstall_pkg() {
  if pipx list --short 2>/dev/null | grep -Fx "${PACKAGE_NAME}" >/dev/null 2>&1; then
    pipx uninstall "${PACKAGE_NAME}"
  fi
  pipx install "${REPO_URL}"
}

main() {
  case "${1:-}" in
    --help|-h)
      usage
      exit 0
      ;;
    "")
      ensure_pipx
      install_pkg
      ;;
    --upgrade)
      ensure_pipx
      upgrade_pkg
      ;;
    --force)
      ensure_pipx
      force_reinstall_pkg
      ;;
    *)
      echo "未知参数: $1" >&2
      echo >&2
      usage >&2
      exit 1
      ;;
  esac

  echo
  echo "安装完成后可直接使用："
  echo "  qiaoya --help"
}

main "$@"
