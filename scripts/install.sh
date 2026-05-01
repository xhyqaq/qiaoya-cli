#!/usr/bin/env sh
set -eu

RELEASE_BASE_URL="${QIAOYA_RELEASE_BASE_URL:-https://github.com/xhyqaq/qiaoya-cli/releases/latest/download}"
AGENTS="${QIAOYA_AGENTS:-auto}"
PROJECT_DIR="${QIAOYA_PROJECT_DIR:-}"

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "缺少依赖命令: $1" >&2
    exit 1
  fi
}

detect_asset() {
  os="$(uname -s | tr '[:upper:]' '[:lower:]')"
  arch="$(uname -m)"

  case "$os" in
    darwin) platform="darwin" ;;
    linux) platform="linux" ;;
    *)
      echo "暂不支持当前系统: $os" >&2
      exit 1
      ;;
  esac

  case "$arch" in
    x86_64|amd64) cpu="amd64" ;;
    arm64|aarch64) cpu="arm64" ;;
    *)
      echo "暂不支持当前架构: $arch" >&2
      exit 1
      ;;
  esac

  echo "qiaoya-${platform}-${cpu}"
}

checksum_file() {
  file="$1"
  expected_file="$2"
  asset_name="$3"

  expected="$(awk -v name="$asset_name" '$2 == name { print $1 }' "$expected_file" | head -n 1)"
  if [ -z "$expected" ]; then
    echo "checksums.txt 中未找到 $asset_name" >&2
    exit 1
  fi

  if command -v sha256sum >/dev/null 2>&1; then
    actual="$(sha256sum "$file" | awk '{print $1}')"
  elif command -v shasum >/dev/null 2>&1; then
    actual="$(shasum -a 256 "$file" | awk '{print $1}')"
  else
    echo "缺少 sha256 校验命令: sha256sum 或 shasum" >&2
    exit 1
  fi

  if [ "$actual" != "$expected" ]; then
    echo "SHA256 校验失败: $asset_name" >&2
    exit 1
  fi
}

main() {
  need_cmd curl
  need_cmd awk
  need_cmd uname

  asset_name="$(detect_asset)"
  tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/qiaoya-install.XXXXXX")"
  trap 'rm -rf "$tmp_dir"' EXIT INT TERM

  binary_path="$tmp_dir/qiaoya"
  checksums_path="$tmp_dir/checksums.txt"

  echo "下载 qiaoya: $asset_name"
  curl -fsSL "$RELEASE_BASE_URL/$asset_name" -o "$binary_path"
  curl -fsSL "$RELEASE_BASE_URL/checksums.txt" -o "$checksums_path"
  checksum_file "$binary_path" "$checksums_path" "$asset_name"
  chmod +x "$binary_path"

  if [ -n "$PROJECT_DIR" ]; then
    "$binary_path" install --agents "$AGENTS" --project-dir "$PROJECT_DIR"
  else
    "$binary_path" install --agents "$AGENTS"
  fi

  echo
  echo "安装完成。请重启 Codex / Claude Code，或在 Cursor / Windsurf 项目里重新加载规则。"
}

main "$@"

