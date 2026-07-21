#!/usr/bin/env python3
"""
search-all — 全源检索脚本
统一搜索 Obsidian Vault + Halo 博客 + Hermes 配置文件

用法:
  search-all <关键词>              # 同时搜所有源
  search-all obsidian <关键词>     # 只搜 Obsidian
  search-all halo <关键词>         # 只搜博客
  search-all config <关键词>       # 只搜 Hermes 配置
  search-all help                  # 显示帮助

注意: ⚠️ Windows + git-bash 环境
  - 路径用反斜杠 \\ 和原始字符串 r'...'
  - 某些 exe 路径需要绝对路径
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from urllib.request import urlopen, quote
from urllib.error import URLError


# ── 配置（可通过环境变量覆盖） ──
OBSIDIAN_VAULT: str = os.environ.get(
    "SEARCH_ALL_OBSIDIAN",
    r"D:\1-obsidian",
)
HALO_API: str = os.environ.get(
    "SEARCH_ALL_HALO_API",
    "https://jia.baoyu2023.top/apis/api.content.halo.run/v1alpha1/posts",
)
HERMES_HOME: str = os.environ.get(
    "SEARCH_ALL_HERMES",
    r"C:\Users\zhaid\AppData\Local\hermes",
)
CONFIG_PATHS: List[str] = [
    HERMES_HOME,
    os.environ.get("HERMES_DIR", ""),
    str(Path.home() / ".hermes"),
    str(Path.home() / ".bashrc"),
    str(Path.home() / ".config"),
]

BOLD: str = "\033[1m"
DIM: str = "\033[2m"
GREEN: str = "\033[32m"
YELLOW: str = "\033[33m"
CYAN: str = "\033[36m"
RESET: str = "\033[0m"
SEP: str = "─" * 60


# ══════════════════════════════════════════════
# 原生 Python 文件搜索（替代 shell grep）
# ══════════════════════════════════════════════


def grep_file(filepath: Path, keyword: str, max_count: int = 3) -> List[str]:
    """在单个文件中搜索关键词，返回匹配行列表（行号前缀）。"""
    matches: List[str] = []
    try:
        text: str = filepath.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return matches
    for i, line in enumerate(text.splitlines(), 1):
        if keyword.lower() in line.lower():
            matches.append(f"{filepath}:{i}:{line.strip()}")
            if len(matches) >= max_count:
                break
    return matches


def search_obsidian(keyword: str) -> None:
    """用原生 Python 搜索 Obsidian vault markdown 文件。"""
    vault: Path = Path(OBSIDIAN_VAULT)
    if not vault.is_dir():
        print(f"  {DIM}Obsidian vault 不存在: {OBSIDIAN_VAULT}{RESET}")
        return

    matched_files: set = set()
    all_lines: List[str] = []
    total_files: int = 0

    for md_file in vault.rglob("*.md"):
        lines: List[str] = grep_file(md_file, keyword, max_count=3)
        if lines:
            matched_files.add(str(md_file))
            all_lines.extend(lines)
            total_files += 1

    if not all_lines:
        print(f"  {DIM}无匹配{RESET}")
        return

    print(f"  {BOLD}命中 {len(all_lines)} 行，分布在 {len(matched_files)} 个文件{RESET}")
    for f in sorted(matched_files):
        try:
            rel: str = os.path.relpath(f, OBSIDIAN_VAULT)
        except ValueError:
            rel = f
        print(f"  {GREEN}📄 {rel}{RESET}")
    print()


def url_encode(s: str) -> str:
    """URL 全量编码（含中文）。使用 urllib.parse.quote 对非 ASCII 字符编码。"""
    return quote(s, safe="")


def search_halo(keyword: str) -> None:
    """通过 Halo 公开 API 搜索已发布的文章。"""
    encoded: str = url_encode(keyword)
    url: str = f"{HALO_API}?keyword={encoded}&size=10"

    try:
        with urlopen(url, timeout=30) as resp:
            body: str = resp.read().decode("utf-8")
    except (URLError, OSError, TimeoutError) as e:
        print(f"  {DIM}Halo API 请求失败: {e}{RESET}")
        return

    try:
        data: dict = json.loads(body)
        items: list = data.get("items", [])
        total: int = data.get("total", 0)
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"  {DIM}Halo API 响应解析失败: {e}{RESET}")
        return

    if total == 0 or not items:
        print(f"  {DIM}无匹配 (共 {total} 篇){RESET}")
        return

    print(f"  {BOLD}共 {total} 篇匹配，显示前 {min(10, len(items))} 篇{RESET}")
    for post in items:
        spec: dict = post.get("spec", {})
        status: dict = post.get("status", {})
        title: str = spec.get("title", "?")
        permalink: str = status.get("permalink", "")
        tags_str: str = ", ".join(
            t.get("spec", {}).get("displayName", "")
            for t in post.get("tags", [])
        )
        excerpt: str = status.get("excerpt", "")[:150]

        print(f"\n  {GREEN}📝 {title}{RESET}")
        if permalink:
            print(f"    {DIM}{permalink}{RESET}")
        if tags_str:
            print(f"    {DIM}标签: {tags_str}{RESET}")
        if excerpt:
            print(f"    {DIM}{excerpt}{RESET}")
    print()


def search_single_file(filepath: Path, keyword: str, max_lines: int = 5) -> Optional[str]:
    """在单个文件中搜索（简单版），返回匹配内容或 None。"""
    try:
        text: str = filepath.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError, UnicodeDecodeError):
        return None
    matches: List[str] = []
    for i, line in enumerate(text.splitlines(), 1):
        if keyword.lower() in line.lower():
            matches.append(f"{i}:{line.strip()}")
            if len(matches) >= max_lines:
                break
    return "\n".join(matches) if matches else None


def search_config(keyword: str) -> None:
    """搜索 Hermes 配置文件和脚本（原生 Python 实现）。"""
    found_files: List[tuple] = []
    MAX_LINES: int = 30

    for base_str in CONFIG_PATHS:
        if not base_str:
            continue
        base: Path = Path(base_str)
        if not base.exists():
            continue

        if base.is_file():
            match: Optional[str] = search_single_file(base, keyword, max_lines=5)
            if match:
                found_files.append((str(base), match))
        else:
            # 搜索配置目录下的常见文件格式
            lines: List[str] = []
            for ext in ("*.md", "*.json", "*.yaml", "*.yml", "*.py", "*.sh", "*.toml", "*.conf", "*.ini"):
                for f in base.rglob(ext):
                    result: Optional[str] = search_single_file(f, keyword, max_lines=2)
                    if result:
                        lines.append(f"{f}:{result}")
                        if len(lines) >= MAX_LINES:
                            break
                if len(lines) >= MAX_LINES:
                    break
            if lines:
                found_files.append((str(base), "\n".join(lines)))

    if not found_files:
        print(f"  {DIM}无匹配{RESET}")
        return

    for path, content in found_files:
        print(f"  {GREEN}⚙ {path}{RESET}")
        for line in content.split("\n")[:8]:
            print(f"    {DIM}{line}{RESET}")
    print()


def print_section(title: str) -> None:
    """打印分节标题。"""
    print(f"\n{BOLD}{YELLOW}▎{title}{RESET}")
    print(SEP)


def main() -> None:
    """入口函数。"""
    args: List[str] = sys.argv[1:]

    if not args or args[0] in ("help", "--help", "-h"):
        print(__doc__)
        return

    if len(args) == 1:
        keyword: str = args[0].strip()
        if not keyword:
            print("搜索关键词不能为空")
            return
        if len(keyword) > 200:
            print("搜索关键词过长（最多 200 字符）")
            return
        sources: List[str] = ["obsidian", "halo", "config"]
    else:
        source: str = args[0].lower()
        keyword = " ".join(args[1:]).strip()
        if source == "help":
            print(__doc__)
            return
        if not keyword:
            print("搜索关键词不能为空")
            return
        if source not in ("obsidian", "halo", "config"):
            print(f"未知源: {source}，可选: obsidian / halo / config")
            print(__doc__)
            return
        sources = [source]

    print(f"\n{BOLD}{GREEN}🔍 search-all{RESET} — 全源检索: {BOLD}{keyword}{RESET}")
    print(f"{DIM}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")

    if "obsidian" in sources:
        print_section("Obsidian Vault")
        search_obsidian(keyword)

    if "halo" in sources:
        print_section("Halo 博客")
        search_halo(keyword)

    if "config" in sources:
        print_section("Hermes 配置 & 脚本")
        search_config(keyword)

    print(f"\n{DIM}💡 Agent 专属源 (直接对我说): session DB / memory / fact_store{RESET}")
    print(f"{DIM}   例：「帮我搜 session 里关于 \"{keyword}\" 的内容」{RESET}")


if __name__ == "__main__":
    main()
