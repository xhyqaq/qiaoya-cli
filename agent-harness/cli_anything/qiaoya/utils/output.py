"""输出工具：统一 JSON / 表格 输出"""
import json
import sys
from typing import Any, Iterable, Sequence, Tuple


def print_json(data: Any):
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def print_table(headers: list[str], rows: list[list], max_width: int = 40):
    if not rows:
        print("（无数据）")
        return
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = min(max(col_widths[i], len(str(cell))), max_width)
    fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
    sep = "  ".join("-" * w for w in col_widths)
    print(fmt.format(*headers))
    print(sep)
    for row in rows:
        truncated = [str(c)[:col_widths[i]] for i, c in enumerate(row)]
        print(fmt.format(*truncated))


def print_kv(pairs: Sequence[Tuple[str, Any]]):
    for label, value in pairs:
        print(f"{label}：{value}")


def error(msg: str, json_mode: bool = False):
    if json_mode:
        print_json({"error": msg})
    else:
        print(f"\033[31m✗ {msg}\033[0m", file=sys.stderr)


def success(msg: str, json_mode: bool = False):
    if json_mode:
        print_json({"success": True, "message": msg})
    else:
        print(f"\033[32m✓ {msg}\033[0m")


def page_info(page_data: dict) -> str:
    total = page_data.get("total", 0)
    current = page_data.get("current", 1)
    pages = page_data.get("pages", 1)
    return f"第 {current}/{pages} 页，共 {total} 条"
