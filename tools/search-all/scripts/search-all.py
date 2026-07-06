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
  - Python subprocess 用 cmd.exe，不认识正斜杠 D:/
  - curl 和 grep 用 Windows 原生路径格式
"""

import subprocess, sys, json, os, re
from datetime import datetime
from pathlib import Path

# ── 配置（Windows 原生路径格式） ──
OBSIDIAN_VAULT = r"D:\1-obsidian"
HALO_API = "https://jia.baoyu2023.top/apis/api.content.halo.run/v1alpha1/posts"
HERMES_HOME = r"C:\Users\zhaid\AppData\Local\hermes"
CONFIG_PATHS = [
    HERMES_HOME,
    r"C:\Users\zhaid\.hermes",
    r"C:\Users\zhaid\.bashrc",
    r"C:\Users\zhaid\.config",
]

BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RESET = "\033[0m"
SEP = "─" * 60


def print_section(title):
    print(f"\n{BOLD}{YELLOW}▎{title}{RESET}")
    print(SEP)


def search_obsidian(keyword):
    """grep Obsidian vault markdown 文件"""
    if not os.path.isdir(OBSIDIAN_VAULT):
        print(f"  {DIM}Obsidian vault 不存在: {OBSIDIAN_VAULT}{RESET}")
        return

    cmd = f'grep -rn --max-count=3 -i "{keyword}" "{OBSIDIAN_VAULT}" --include="*.md" 2>nul | head -80'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)

    lines = result.stdout.strip()
    if not lines:
        print(f"  {DIM}无匹配{RESET}")
        return

    # 统计匹配文件数
    files = set()
    for line in lines.split("\n"):
        m = re.match(r'^(.+?):\d+:', line)
        if m:
            files.add(m.group(1))

    print(f"  {BOLD}命中 {len(lines.split(chr(10)))} 行，分布在 {len(files)} 个文件{RESET}")
    for f in sorted(files):
        try:
            rel = os.path.relpath(f, OBSIDIAN_VAULT)
        except ValueError:
            rel = f
        print(f"  {GREEN}📄 {rel}{RESET}")
    print()


def search_halo(keyword):
    """通过 Halo 公开 API 搜索已发布的文章"""
    cmd = f'curl -s "{HALO_API}?keyword={keyword}&size=10" 2>nul'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

    try:
        data = json.loads(result.stdout)
        items = data.get("items", [])
        total = data.get("total", 0)
    except (json.JSONDecodeError, KeyError, ValueError):
        print(f"  {DIM}Halo API 请求失败（或网络超时）{RESET}")
        return

    if total == 0 or not items:
        print(f"  {DIM}无匹配 (共 {total} 篇){RESET}")
        return

    print(f"  {BOLD}共 {total} 篇匹配，显示前 {min(10, len(items))} 篇{RESET}")
    for post in items:
        spec = post.get("spec", {})
        status = post.get("status", {})
        title = spec.get("title", "?")
        permalink = status.get("permalink", "")
        tags = ", ".join(t.get("spec", {}).get("displayName", "") for t in post.get("tags", []))
        excerpt = status.get("excerpt", "")[:150]

        print(f"\n  {GREEN}📝 {title}{RESET}")
        if permalink:
            print(f"    {DIM}{permalink}{RESET}")
        if tags:
            print(f"    {DIM}标签: {tags}{RESET}")
        if excerpt:
            print(f"    {DIM}{excerpt}{RESET}")
    print()


def search_config(keyword):
    """搜索 Hermes 配置文件和脚本"""
    found_files = []

    for base in CONFIG_PATHS:
        if not os.path.exists(base):
            continue
        if os.path.isfile(base):
            cmd = f'grep -n -i "{keyword}" "{base}" 2>nul | head -5'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            if result.stdout.strip():
                found_files.append((base, result.stdout.strip()))
        else:
            cmd = f'grep -rn --max-count=2 -i "{keyword}" "{base}" --include="*.md" --include="*.json" --include="*.yaml" --include="*.py" --include="*.sh" 2>nul | head -30'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
            if result.stdout.strip():
                found_files.append((base, result.stdout.strip()))

    if not found_files:
        print(f"  {DIM}无匹配{RESET}")
        return

    for path, content in found_files:
        print(f"  {GREEN}⚙ {path}{RESET}")
        for line in content.split("\n")[:8]:
            print(f"    {DIM}{line}{RESET}")
    print()


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("help", "--help", "-h"):
        print(__doc__)
        return

    if len(args) == 1:
        keyword = args[0]
        sources = ["obsidian", "halo", "config"]
    else:
        source = args[0].lower()
        keyword = " ".join(args[1:])
        if source == "help":
            print(__doc__)
            return
        if source not in ("obsidian", "halo", "config"):
            print(f"未知源: {source}，可选: obsidian / halo / config")
            print(__doc__)
            return
        sources = [source]

    print(f"\n{BOLD}{GREEN}🔍 search-all{RESET} — 全源检索: {BOLD}{keyword}{RESET}")
    print(f"{DIM}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")

    if "obsidian" in sources:
        print_section("Obsidian Vault (D:\\1-obsidian)")
        search_obsidian(keyword)

    if "halo" in sources:
        print_section("Halo 博客 (jia.baoyu2023.top)")
        search_halo(keyword)

    if "config" in sources:
        print_section("Hermes 配置 & 脚本")
        search_config(keyword)

    print(f"\n{DIM}💡 Agent 专属源 (直接对我说): session DB / memory / fact_store{RESET}")
    print(f"{DIM}   例：「帮我搜 session 里关于 \"{keyword}\" 的内容」{RESET}")


if __name__ == "__main__":
    main()
