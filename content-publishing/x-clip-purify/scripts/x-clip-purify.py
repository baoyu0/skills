#!/usr/bin/env python3
"""
x-clip-purify — X/Twitter 剪藏文章标准化工具

用法:
  x-clip-purify detect <file>              # 检测文章来源
  x-clip-purify clean <file> [--dry-run]   # 清理 X 噪音（加 --dry-run 预览）
  x-clip-purify title <file> "新标题"      # 重写标题
  x-clip-purify video <file>               # 清理视频标签
  x-clip-purify help                       # 显示帮助
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


BOLD: str = "\033[1m"
DIM: str = "\033[2m"
GREEN: str = "\033[32m"
YELLOW: str = "\033[33m"
RED: str = "\033[31m"
RESET: str = "\033[0m"


# ══════════════════════════════════════════════
# 文件 I/O
# ══════════════════════════════════════════════


def read_file(path: str) -> str:
    """读取文件内容，失败时退出。"""
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"{RED}文件不存在: {path}{RESET}")
        sys.exit(1)
    except PermissionError:
        print(f"{RED}无权限读取: {path}{RESET}")
        sys.exit(1)
    except IOError as e:
        print(f"{RED}读取文件失败: {e}{RESET}")
        sys.exit(1)


def write_file(path: str, content: str) -> None:
    """原子写入文件（先写 tmp 再 rename）。"""
    tmp: str = path + ".tmp"
    try:
        Path(tmp).write_text(content, encoding="utf-8")
        os.replace(tmp, path)
    except IOError as e:
        print(f"{RED}写入文件失败: {e}{RESET}")
        sys.exit(1)


# ══════════════════════════════════════════════
# Frontmatter 处理
# ══════════════════════════════════════════════


def split_frontmatter(content: str) -> Tuple[str, str, bool]:
    """返回 (frontmatter 正文, body 正文, 是否有 frontmatter)。

    frontmatter 正文不含外层 ---，body 正文不含前导 ---。
    """
    if content.startswith("---"):
        idx: int = content.find("---", 3)
        if idx != -1:
            return content[3:idx], content[idx + 3:], True
        # 有开头 --- 但无闭合 ---
        return "", content, False
    return "", content, False


def join_frontmatter(frontmatter: str, body: str) -> str:
    """将 frontmatter 和 body 合并为完整文件。"""
    return f"---{frontmatter}---{body}"


# ══════════════════════════════════════════════
# 命令实现
# ══════════════════════════════════════════════


def cmd_detect(filepath: str) -> str:
    """检测文章来源。返回 'x', 'prompt', 或 'other'。"""
    content: str = read_file(filepath)
    fm: str
    body: str
    fm, body, _ = split_frontmatter(content)

    signals: Dict[str, List[bool]] = {
        "X/Twitter": [
            "x.com" in body or "twitter.com" in body,
            "pbs.twimg.com" in body,
            any(p in fm for p in ["X 上的", "x.com"]),
        ],
        "structured_prompt": [
            "【风格】" in body or "【场景】" in body,
            "【角色】" in body or "【时长】" in body,
            "[00:" in body,
        ],
    }

    is_x: bool = any(signals["X/Twitter"])
    is_prompt: bool = any(signals["structured_prompt"])

    print(f"\n{BOLD}📋 文章来源检测{RESET}")
    print(f"  路径: {filepath}")
    print(f"  X/Twitter: {'✅' if is_x else '❌'}  (信号: {sum(signals['X/Twitter'])}/3)")
    print(f"  结构化 prompt: {'✅' if is_prompt else '❌'}  (信号: {sum(signals['structured_prompt'])}/3)")

    if is_prompt:
        print(f"\n  {YELLOW}⚠️ 建议: 手动拆分为元属性 + 独立代码块{RESET}")

    if not is_x and not is_prompt:
        print(f"\n  来自: {fm[:100]}…")

    if is_x:
        return "x"
    if is_prompt:
        return "prompt"
    return "other"


def cmd_clean(filepath: str, dry_run: bool = False) -> None:
    """执行所有清理操作。"""
    content: str = read_file(filepath)
    original: str = content
    report: Dict[str, int] = {"X 元数据": 0, "作者自介": 0, "空 section": 0, "alt 文本": 0}

    # 1. 剥离 X 线程元数据
    patterns: List[str] = [
        r"发布你的回复.*", r"由 AI 生成.*", r"查看更多.*",
        r"没有项目.*",
        r"\d+:\d+\s*/\s*\d+:\d+",  # 0:05 / 0:32
    ]
    for pat in patterns:
        new: str = re.sub(pat, "", content)
        if new != content:
            report["X 元数据"] += 1
        content = new

    # 2. 清理作者自介（全文扫描推广文本）
    intro_patterns: List[str] = [
        r"(我是\s*\S+[^。]*?(?:做过|专注|关注|擅长)[^。]*)。",
        r"我是\s*\S{1,10}[，,]\s*(?:关注|点击|查看更多).*",
    ]
    for pat in intro_patterns:
        new = re.sub(pat, "", content)
        if new != content:
            report["作者自介"] += 1
        content = new

    # 3. 清理空 section（## ：断章标题）
    content = re.sub(r"^## \d+\.\s*：.*\n?", "", content, flags=re.MULTILINE)

    # 纯文本的空 section
    content = re.sub(r"^\*\*[^*]*?\*\*：\s*\n+\*\*[^*]*?\*\*", "", content, flags=re.MULTILINE)

    # 4. 优化 alt 文本
    alt_fixes: Dict[str, str] = {
        r'!\[\s*画像?\s*\]': "图像",
        r'!\[\s*图像\s*\]': "截图",
        r'!\[\s*图片\s*\]': "配图",
        r'!\[\s*图\s*\]': "插图",
        r'!\[\s*screenshot\s*\]': "截图",
        r'!\[\s*image\s*\]': "图片",
        r'!\[\s*img\s*\]': "图片",
    }
    for pat, replacement in alt_fixes.items():
        # 先用 search 确认有匹配，再用 sub 替换（flag 保持一致）
        if re.search(pat, content):
            content = re.sub(pat, f"![{replacement}]", content)

    # 5. 清理连续空行（3+ → 1）
    content = re.sub(r"\n{3,}", "\n\n", content)

    if content == original:
        print(f"  {DIM}无需清理{RESET}")
        return

    total: int = sum(report.values())
    if dry_run:
        print(f"\n{YELLOW}🔍 Dry-Run: 将清理 {total} 处{RESET}")
    else:
        write_file(filepath, content)
        print(f"\n{GREEN}✅ X-Clip-Purify 清理完成{RESET}")
    for k, v in report.items():
        if v > 0:
            print(f"  {GREEN}✅ {k}: {v} 处{RESET}")
    print(f"  {DIM}共 {total} 处{'（预览，未写入）' if dry_run else ''}{RESET}")


def slug_from_title(title: str) -> str:
    """从标题生成纯 ASCII slug（Halo 不支持中文 slug）。"""
    slug: str = title.lower()
    # 保留 ASCII 字母数字和短横线
    slug = re.sub(r'[^a-z0-9-]', '-', slug)
    slug = re.sub(r'-+', '-', slug).strip('-')
    if not slug:
        # fallback 含时间戳，避免重复
        from datetime import datetime
        slug = f"post-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    return slug


def cmd_title(filepath: str, new_title: Optional[str] = None) -> None:
    """重写标题和 slug。"""
    content: str = read_file(filepath)
    fm: str
    body: str
    has_fm: bool
    fm, body, has_fm = split_frontmatter(content)

    if not has_fm:
        print(f"  {RED}❌ 文件无 frontmatter{RESET}")
        return

    lines: List[str] = fm.split("\n")
    new_lines: List[str] = []
    title_updated: bool = False
    slug_updated: bool = False

    for line in lines:
        if line.startswith("title:") and new_title:
            new_lines.append(f"title: {new_title}")
            title_updated = True
        elif line.startswith("slug:") and new_title:
            new_lines.append(f"slug: {slug_from_title(new_title)}")
            slug_updated = True
        else:
            new_lines.append(line)

    new_fm: str = "\n".join(new_lines)
    write_file(filepath, join_frontmatter(new_fm, body))

    if title_updated:
        print(f"  ✅ title → {new_title}")
    if slug_updated:
        print(f"  ✅ slug → auto-generated")


def cmd_video(filepath: str) -> None:
    """清理视频标签。"""
    content: str = read_file(filepath)
    original: str = content

    # 替换 <video> 标签为 poster 图片链接
    content = re.sub(
        r'<video[^>]*poster="([^"]+)"[^>]*>.*?</video>',
        r'[![视频封面](\1)](\1)',
        content,
        flags=re.DOTALL,
    )

    # 替换 <audio> 标签
    content = re.sub(r'<audio[^>]*>.*?</audio>', '', content, flags=re.DOTALL)

    # 删除 blob: URL
    content = re.sub(r'blob:[^\s\)"\']+', '', content)

    if content != original:
        write_file(filepath, content)
        print(f"  ✅ 视频/音频标签已清理")
    else:
        print(f"  {DIM}无视频标签需清理{RESET}")


# ══════════════════════════════════════════════
# 入口
# ══════════════════════════════════════════════


def main() -> None:
    """CLI 入口。"""
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(__doc__)
        return

    cmd: str = sys.argv[1]

    if cmd == "help":
        print(__doc__)
        return

    if len(sys.argv) < 3:
        print(f"用法: x-clip-purify {cmd} <文件路径> [选项]")
        return

    filepath: str = os.path.abspath(sys.argv[2])

    if not os.path.exists(filepath):
        print(f"文件不存在: {filepath}")
        return

    if cmd == "detect":
        result: str = cmd_detect(filepath)
        print(f"  → 分类: {result}")
    elif cmd == "clean":
        dry_run: bool = "--dry-run" in sys.argv or "-n" in sys.argv
        cmd_clean(filepath, dry_run)
    elif cmd == "title":
        new_title: Optional[str] = sys.argv[3] if len(sys.argv) >= 4 else None
        if not new_title:
            print("请提供新标题: x-clip-purify title <文件> \"新标题\"")
            return
        cmd_title(filepath, new_title)
    elif cmd == "video":
        cmd_video(filepath)
    else:
        print(f"未知命令: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
