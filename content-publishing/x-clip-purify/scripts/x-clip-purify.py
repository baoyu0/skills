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

import re, sys, os
from pathlib import Path

BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"


def read_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def split_frontmatter(content):
    """返回 (frontmatter: str, body: str, has_frontmatter: bool)"""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[1], parts[2], True
    return "", content, False


def join_frontmatter(frontmatter, body):
    return f"---{frontmatter}---{body}"


def cmd_detect(filepath):
    content = read_file(filepath)
    fm, body, _ = split_frontmatter(content)

    # 检测标志
    signals = {
        "X/Twitter": [
            "x.com" in body or "twitter.com" in body,
            "pbs.twimg.com" in body,
            any(p in fm for p in ["X 上的", "x.com"]),
        ],
        "结构化 prompt": [
            "【风格】" in body or "【场景】" in body,
            "【角色】" in body or "【时长】" in body,
            "[00:" in body,
        ],
    }

    is_x = any(signals["X/Twitter"])
    is_prompt = any(signals["结构化 prompt"])

    print(f"\n{BOLD}📋 文章来源检测{RESET}")
    print(f"  路径: {filepath}")
    print(f"  X/Twitter: {'✅' if is_x else '❌'}  (信号: {sum(signals['X/Twitter'])}/3)")
    print(f"  结构化 prompt: {'✅' if is_prompt else '❌'}  (信号: {sum(signals['结构化 prompt'])}/3)")

    if is_prompt:
        print(f"\n  {YELLOW}⚠️ 建议: 手动拆分为元属性 + 独立代码块{RESET}")

    if not is_x and not is_prompt:
        fm, body, _ = split_frontmatter(content)
        print(f"\n  来自: {fm[:100]}…")
        return "other"

    if is_x:
        return "x"
    return "prompt"


def cmd_clean(filepath, dry_run=False):
    """执行所有清理操作"""
    content = read_file(filepath)
    original = content
    report = {"X 元数据": 0, "作者自介": 0, "空 section": 0, "alt 文本": 0}

    # 1. 剥离 X 线程元数据
    patterns = [
        r"发布你的回复.*", r"由 AI 生成.*", r"查看更多.*",
        r"没有项目.*",
        r"\d+:\d+\s*/\s*\d+:\d+",  # 0:05 / 0:32
    ]
    for pat in patterns:
        new = re.sub(pat, "", content)
        if new != content:
            report["X 元数据"] += 1
        content = new

    # 2. 清理作者自介（全文扫描推广文本）
    intro_patterns = [
        r"(我是\s*\S+[^。]*?(?:做过|专注|关注|擅长)[^。]*)。",
        r"我是\s*\S{1,10}[，,]\s*(?:关注|点击|查看更多).*",
    ]
    for pat in intro_patterns:
        new = re.sub(pat, "", content)
        if new != content:
            report["作者自介"] += 1
        content = new

    # 3. 清理空 section （## ： 断章标题）
    content = re.sub(r"^## \d+\.\s*：.*\n?", "", content, flags=re.MULTILINE)

    # 纯文本的空 section
    content = re.sub(r"^\*\*[^*]*?\*\*：\s*\n+\*\*[^*]*?\*\*", "", content, flags=re.MULTILINE)

    # 4. 优化 alt 文本（![图像] → 从上下文推断）
    alt_fixes = {
        r'!\[\s*画像?\s*\]': "图像",
        r'!\[\s*图像\s*\]': "截图",
        r'!\[\s*图片\s*\]': "配图",
        r'!\[\s*图\s*\]': "插图",
        r'!\[\s*screenshot\s*\]': "截图",
        r'!\[\s*image\s*\]': "图片",
        r'!\[\s*img\s*\]': "图片",
    }
    for pat, replacement in alt_fixes.items():
        if re.search(pat, content, re.IGNORECASE):
            content = re.sub(pat, f"![{replacement}]", content, flags=re.IGNORECASE)
            report["alt 文本"] += 1

    # 5. 清理连续空行（3+ → 1）
    content = re.sub(r"\n{4,}", "\n\n", content)

    if content == original:
        print(f"  {DIM}无需清理{RESET}")
        return

    total = sum(report.values())
    if dry_run:
        print(f"\n{YELLOW}🔍 Dry-Run: 将清理 {total} 处{RESET}")
    else:
        write_file(filepath, content)
        print(f"\n{GREEN}✅ X-Clip-Purify 清理完成{RESET}")
    for k, v in report.items():
        if v > 0:
            print(f"  {GREEN}✅ {k}: {v} 处{RESET}")
    print(f"  {DIM}共 {total} 处{'（预览，未写入）' if dry_run else ''}{RESET}")


def cmd_title(filepath, new_title=None):
    """重写标题和 slug"""
    content = read_file(filepath)
    fm, body, has_fm = split_frontmatter(content)

    if not has_fm:
        print(f"  {RED}❌ 文件无 frontmatter{RESET}")
        return

    lines = fm.split("\n")
    new_lines = []
    title_updated = False
    slug_updated = False

    for line in lines:
        if line.startswith("title:") and new_title:
            new_lines.append(f"title: {new_title}")
            title_updated = True
        elif line.startswith("slug:") and new_title:
            # 自动生成纯 ASCII slug（Halo 不支持中文 slug）
            slug = new_title.lower()
            slug = re.sub(r'[^a-z0-9-]', '-', slug)  # 只保留 ASCII 字母数字
            slug = re.sub(r'-+', '-', slug).strip('-')
            if not slug:
                slug = "post"
            new_lines.append(f"slug: {slug}")
            slug_updated = True
        else:
            new_lines.append(line)

    new_fm = "\n".join(new_lines)
    write_file(filepath, join_frontmatter(new_fm, body))

    if title_updated:
        print(f"  ✅ title → {new_title}")
    if slug_updated:
        print(f"  ✅ slug → auto-generated")


def cmd_video(filepath):
    """清理视频标签"""
    content = read_file(filepath)
    original = content

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


def main():
    if len(sys.argv) < 3 or sys.argv[1] in ("-h", "--help", "help"):
        print(__doc__)
        return

    cmd = sys.argv[1]
    filepath = os.path.abspath(sys.argv[2])

    if not os.path.exists(filepath):
        print(f"文件不存在: {filepath}")
        return

    if cmd == "detect":
        cmd_detect(filepath)
    elif cmd == "clean":
        dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
        cmd_clean(filepath, dry_run)
    elif cmd == "title":
        new_title = sys.argv[3] if len(sys.argv) >= 4 else None
        cmd_title(filepath, new_title)
    elif cmd == "video":
        cmd_video(filepath)
    else:
        print(f"未知命令: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
