#!/usr/bin/env python3
"""
auto-number.py — 自动编号 Markdown 文章的 H2/H3 标题

用法: python auto-number.py <文件路径>

功能:
  1. 如果正文没有 H1，从 frontmatter title 补一个
  2. H2 自动编号（支持多种原始格式：plain / 0.N- / 一、/ 已编号跳过）
  3. H3 自动编号 X.Y（支持已有 ###、或 **粗体标题** 转换）
  4. X.Y 编号跟随父章节
"""

import re
import sys
import os
from heading_utils import number_headings, bold_to_h3



def load_file(path):
    with open(path, encoding='utf-8') as f:
        text = f.read()
    fm_match = re.match(r'^---\n(.*?)\n---\n', text, re.DOTALL)
    if fm_match:
        fm = fm_match.group(0)
        body = text[fm_match.end():]
    else:
        fm, body = '', text

    fm_dict = {}
    if fm_match:
        for line in fm_match.group(1).split('\n'):
            m = re.match(r'^(\w+):\s*(.+)$', line)
            if m:
                fm_dict[m.group(1)] = m.group(2).strip('"').strip("'")

    return fm, body, fm_dict


def add_h1_if_missing(body, title):
    has_h1 = bool(re.search(r'^# ', body, re.MULTILINE))
    if not has_h1 and title:
        body = f'# {title}\n\n' + body
        print("  ℹ️  Added H1 from frontmatter title")
    return body


def strip_x_footer(body):
    """移除 X/Twitter 剪藏文章末尾的作者签名/推广信息块
    
    常见模式：末尾 blockquote 含日期 + 作者自我介绍 + 推广链接
    如：
    > 6月16日
    > 
    > 今天简单盘了一下... 我是 ian... 过去做过些...
    """
    lines = body.split('\n')
    
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i].rstrip()
        
        # Find a blockquote line with date pattern near the end
        if line.startswith('>') and re.search(r'\d+月\d+日', line):
            # Found a date line in a blockquote — check if this blockquote contains footer keywords
            # Find the full blockquote extent (going both directions)
            start = i
            while start > 0 and lines[start - 1].strip().startswith('>'):
                start -= 1
            
            end = i
            while end < len(lines) - 1 and lines[end + 1].strip().startswith('>'):
                end += 1
            
            # Check if any line in this blockquote has footer keywords
            block_text = '\n'.join(lines[start:end + 1])
            if any(kw in block_text for kw in ['我是', '做过', '关注', '订阅', '查看更多']):
                print(f"  🗑️  Removed X article footer ({end - start + 1} lines)")
                # Remove blockquote lines and trailing blank lines
                result_lines = lines[:start]
                # Trim trailing blank lines
                while result_lines and not result_lines[-1].strip():
                    result_lines.pop()
                return '\n'.join(result_lines) + '\n'
    
    return body


def add_narrative_headings(body):
    """为纯叙事文章（无 H2 标题）自动推断章节结构
    
    策略：
    1. 用图片位置做段落分割（X 剪藏文章常用图片做章节分隔）
    2. 跳过封面图（第一张），后续每张图视为一个新章节
    3. 从章节首段提取关键句作为标题
    """
    # Only run if there are no H2 headings
    has_any_h2 = bool(re.search(r'^##\s', body, re.MULTILINE))
    if has_any_h2:
        return body
    
    # Count images in body
    img_count = len(re.findall(r'<div align="center">', body))
    if img_count < 3:
        return body  # Not enough sections to split, leave for manual
    
    print(f"  📖 Detected narrative style with {img_count} images")
    
    # Split by image blocks (div wrapper)
    img_pattern = r'(<div align="center">\n<img src="[^"]+" alt="[^"]*" style="[^"]*">\n<em>[^<]*</em>\n</div>)'
    parts = re.split(img_pattern, body)
    
    # parts alternates: [text_before, img1, text_after_img1, img2, text_after_img2, ...]
    # The first text_before is the intro (before any image)
    
    sections = []
    current_text = []
    
    for i, part in enumerate(parts):
        if re.match(img_pattern, part):
            # This is an image block
            if current_text:
                text = '\n'.join(current_text).strip()
                if text:
                    sections.append({'type': 'text', 'content': text})
                current_text = []
            sections.append({'type': 'image', 'content': part})
        else:
            current_text.append(part)
    
    if current_text:
        text = '\n'.join(current_text).strip()
        if text:
            sections.append({'type': 'text', 'content': text})
    
    # First section before first image = intro (no heading)
    # Subsequent text sections after each image = new chapters
    result_parts = []
    chapter_num = 0
    
    for sec in sections:
        if sec['type'] == 'image':
            result_parts.append(sec['content'])
        else:
            text = sec['content']
            if not text.strip():
                continue
            
            chapter_num += 1
            
            if chapter_num == 1:
                # Intro section before first image — no heading
                result_parts.append(text)
            else:
                # Extract heading from first sentence
                heading = extract_heading_from_text(text)
                if heading:
                    result_parts.append(f'## {chapter_num - 1}. {heading}')
                    # Remove the heading sentence from text if it was used
                    remaining = remove_heading_from_text(text, heading)
                    if remaining:
                        result_parts.append(remaining)
                else:
                    result_parts.append(f'## {chapter_num - 1}. 续')
                    result_parts.append(text)
    
    result = '\n\n'.join(p for p in result_parts if p.strip())
    print(f"  🔖 Auto-created {chapter_num - 1} section headings")
    return result


# Common heading-starting patterns — sentences that read like section titles
_X_SELF_INTRO_KW = ['我是', '我叫', '做过', '关注', '订阅', '查看更多', 'build in public', 'Dribbble', '全网同名', '即刻', '下一期']


def strip_x_self_intro(body):
    """移除 X/Twitter 剪藏文章中所有含自介/推广的内容，无论是否在 blockquote 中
    
    扫描范围：
    1. 全文所有 blockquote（已实现）
    2. 正文首尾段落（正文中夹杂的自介行）
    """
    # ── Phase 1: 移除含自介关键词的 blockquote ──
    lines = body.split('\n')
    in_blockquote = False
    bq_lines = []
    result_lines = []
    removed_count = 0

    def flush_blockquote():
        nonlocal bq_lines, removed_count
        if bq_lines:
            block_text = '\n'.join(bq_lines)
            if any(kw in block_text for kw in _X_SELF_INTRO_KW):
                removed_count += 1
                bq_lines = []
                return
            result_lines.extend(bq_lines)
            bq_lines = []

    for i, line in enumerate(lines):
        stripped = line.rstrip()
        is_bq = stripped.startswith('>')
        
        if is_bq and not in_blockquote:
            in_blockquote = True
            bq_lines = [line]
        elif is_bq and in_blockquote:
            bq_lines.append(line)
        elif not is_bq and in_blockquote:
            in_blockquote = False
            flush_blockquote()
            result_lines.append(line)
        else:
            result_lines.append(line)
    
    if in_blockquote:
        flush_blockquote()

    body = '\n'.join(result_lines)

    # ── Phase 2: 扫描全文所有段落，移除匹配自介模式的 ──
    paragraphs = body.split('\n\n')
    cleaned = []
    removed_count_phase2 = 0
    for p in paragraphs:
        text = p.strip()
        if not text:
            cleaned.append(p)
            continue
        # Never remove headings
        if text.startswith('#') or text.startswith('<div'):
            cleaned.append(p)
            continue
        if is_self_intro_paragraph(text):
            removed_count_phase2 += 1
        else:
            cleaned.append(p)
    removed_count += removed_count_phase2

    if removed_count:
        print(f"  🗑️  Removed {removed_count} self-intro block(s) ({removed_count_phase2} from body)")
    
    return '\n\n'.join(cleaned)


def is_self_intro_paragraph(text):
    """判断一段正文是否为自介/推广内容"""
    # Must contain at least one self-intro keyword
    if not any(kw in text for kw in _X_SELF_INTRO_KW):
        return False
    # Must be relatively short (self-intro is usually 1-3 lines)
    if len(text) > 500:
        return False
    # Additional heuristics:
    # - Contains career intro patterns
    intro_signals = 0
    if re.search(r'(我是|我叫|我是一个)', text):
        intro_signals += 1
    if re.search(r'(做过|任职|毕业于|目前|现在主要|过去)', text):
        intro_signals += 1
    if re.search(r'(关注|订阅|查看更多|戳|👈|👉)', text):
        intro_signals += 1
    if re.search(r'(产品设计师|工程师|开发者|创始人|设计师|作者)', text):
        intro_signals += 1
    return intro_signals >= 2


_HEADING_CUES = [
    '为什么', '什么是', '怎么', '如何', '关键', '核心',
    '第一个', '第二个', '第三个', '第四个', '第五个',
    '还有一条', '有一条', '搭完之后', '日常协作',
]


def extract_heading_from_text(text):
    """从段落文本中提取合适的章节标题"""
    lines = text.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Skip blockquotes and short lines
        if line.startswith('>') or line.startswith('-') or line.startswith('|'):
            continue
        if len(line) < 6:
            continue
            
        # Try first significant paragraph
        for cue in _HEADING_CUES:
            if cue in line[:40]:
                # Truncate to reasonable heading length
                return truncate_heading(line)
    
    # Fallback: use first non-empty, non-image line
    for line in lines:
        line = line.strip()
        if line and not line.startswith('<') and not line.startswith('>') and not line.startswith('!['):
            return truncate_heading(line)
    
    return None


def truncate_heading(text):
    """截断为合适的标题长度（最多 30 字）"""
    # Remove markdown links
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Take first sentence
    text = re.split(r'[。！？\n]', text)[0]
    # Limit to 30 chars
    if len(text) > 30:
        text = text[:28] + '…'
    return text


def remove_heading_from_text(text, heading):
    """从文本中移除已用作标题的句子"""
    # Simple approach: remove the first occurrence of the heading text
    if heading in text:
        idx = text.index(heading)
        remaining = text[idx + len(heading):].strip()
        # Remove leading punctuation
        remaining = re.sub(r'^[，。！？、：；\s\n]+', '', remaining)
        return remaining
    return text


def strip_clippings_tag(fm):
    """从 frontmatter tags 中移除 clippings，返回修改后的 frontmatter"""
    new_fm = re.sub(r'\n\s*- clippings', '', fm)
    # If tags section became empty, remove the tags line too
    new_fm = re.sub(r'\ntags:\n(?=---|\n\w+)', '\n', new_fm)
    if new_fm != fm:
        print("  🏷️  Removed 'clippings' tag")
    return new_fm


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="自动编号 Markdown 文章的 H2/H3 标题",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  python auto-number.py article.md
  python auto-number.py D:/1-obsidian/Clippings/article.md"""
    )
    parser.add_argument('path', help='Markdown 文件路径')
    parser.add_argument('--check', action='store_true', help='仅检查 heading 结构，不修改文件')
    args = parser.parse_args()

    path = args.path
    if not os.path.isfile(path):
        print(f"❌ 文件不存在: {path}")
        sys.exit(1)

    print(f"📄 {os.path.basename(path)}")
    fm, body, fm_dict = load_file(path)

    body = add_h1_if_missing(body, fm_dict.get('title'))
    body = strip_x_self_intro(body)
    fm = strip_clippings_tag(fm)

    # Check if narrative article (no H2s) — build structure from images
    if not re.search(r'^##\s', body, re.MULTILINE):
        body = add_narrative_headings(body)

    body = number_headings(body, fm_end=0)
    body = bold_to_h3(body)


    h1_count = len(re.findall(r'^# ', body, re.MULTILINE))
    h2_count = len(re.findall(r'^## \d+\.\s+', body, re.MULTILINE))
    h3_count = len(re.findall(r'^### \d+\.\d+\s+', body, re.MULTILINE))
    
    if args.check:
        print(f"\n📊 Heading structure: H1={h1_count} H2={h2_count} H3={h3_count}")
        has_issues = False
        if h1_count == 0:
            print("  ⚠️  Missing H1 — add '# title' at body start")
            has_issues = True
        if h2_count == 0:
            print("  ⚠️  No numbered H2 headings found")
            has_issues = True
        if not has_issues:
            print("  ✅ Structure looks good")
        return
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(fm + body)
    
    print(f"\n✅ Done: H1={h1_count} H2={h2_count} H3={h3_count}")
    print(f"   文件已更新: {path}")


if __name__ == '__main__':
    main()
