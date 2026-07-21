#!/usr/bin/env python3
"""
heading_utils.py -- Shared heading utilities for Markdown articles.

Code-block aware H2/H3 numbering, heading demotion/promotion, CJK numeral
conversion, and bold-to-H3 conversion.

All functions operate on the *body* portion of a markdown file
(frontmatter stripped). Pass fm_end=0 when body is pre-stripped.

Extracted from auto-number.py and halo-publish.py.
"""

import re
from typing import Dict, List, Optional


# -- CJK numeral mapping --

CN_MAP: Dict[str, str] = {
    '一': '1',  # 一
    '二': '2',  # 二
    '三': '3',  # 三
    '四': '4',  # 四
    '五': '5',  # 五
    '六': '6',  # 六
    '七': '7',  # 七
    '八': '8',  # 八
    '九': '9',  # 九
    '十': '10', # 十
    '壹': '1',  # 壹
    '贰': '2',  # 贰
    '叁': '3',  # 叁
    '肆': '4',  # 肆
    '伍': '5',  # 伍
    '陆': '6',  # 陆
    '柒': '7',  # 柒
    '捌': '8',  # 捌
    '玖': '9',  # 玖
    '拾': '10', # 拾
}

_CN_RE = re.compile(
    '[' + ''.join(CN_MAP.keys()) + ']'
)



def cjk_to_arabic(text: str) -> str:
    """Convert CJK numeral characters in text to Arabic numerals.

    Supports both simplified (一二三) and traditional
    (壹贰叁) forms.
    """
    return _CN_RE.sub(lambda m: CN_MAP[m.group(0)], text)


# -- H2 prefix normalization patterns --

# Already numbered with "N. " prefix
_ALREADY_NUM = re.compile(r'^\d+\.\s')
# "0.1- content" or "0.1--content" format
_RANGE_LIKE = re.compile(r'^\d+\.\d+[—–\-]\s+(.+)$')
# "1.1 content" format (multi-part number, no hyphen)
_DOT_NUM = re.compile(r'^\d+\.\d+\s+(.+)$')
# CJK numeral prefix: "一、content" / "一." / "一．"
_CN_PREFIX = re.compile(
    r'^([一-九壹贰叁肆伍陆柒捌玖拾])[、.．]\s*(.*)$'
)
# [bracket]prefix: "[【category】]content"
_BRACKET_PREFIX = re.compile(r'^【[^】]+】\s*(.*)$')

# -- Bold heading patterns --

# Standalone **Title** on its own line (<=30 chars)
_BOLD_STANDALONE = re.compile(r'^\*\*([^*]{1,30}?)[。！？]?\*\*[：:;]?\s*$')
# **N. Title** trailing text on same line
_BOLD_NUM = re.compile(r'^\*\*(\d+\.\s+)([^*]{2,25}?)\*\*\s+(.*)$')
# **Step N · Title** trailing text on same line
_BOLD_STEP = re.compile(r'^\*\*(Step\s+\d+\s*[·•]\s*[^*]{2,30}?)\*\*\s+(.*)$')

# Sentence-level bold patterns -- NOT headings
_CONCLUSION_KW = re.compile(
    r'(结论|注意|关键|提示|建议|本质|差异|根本|核心|一是|二是|既要|又要)'
)


# -- Internal helpers --


def _find_parent_h2_number(lines: List[str], idx: int) -> Optional[int]:
    """Search backward from *idx* to find the nearest numbered H2 heading.

    Returns the section number (e.g., 3 for ``## 3. Title``) or None.
    """
    for i in range(idx, -1, -1):
        m = re.match(r'^## (\d+)\.\s+.+$', lines[i].rstrip())
        if m:
            return int(m.group(1))
    return None


def _is_code_fence(line: str) -> bool:
    """Check if a line opens or closes a fenced code block."""
    return line.rstrip().startswith('```')


# ======================================================================
# Public API
# ======================================================================


def number_headings(content: str, fm_end: int = 0) -> str:
    """Normalize and number H2/H3 headings in *content*.

    What this does, in order:
    1. Skip everything before *fm_end* (frontmatter guard).
    2. Skip content inside `` ``` `` code blocks entirely.
    3. Strip CJK numeral prefixes, N.N- prefixes, and [bracket]prefixes
       from H2 lines, then number them with ``N. ``.
    4. Number bare H3 lines with ``X.Y`` based on the current H2 section.
    5. Leave already-numbered headings untouched.

    Args:
        content: Body text (frontmatter already stripped).
        fm_end: Line index where body content begins (0 when pre-stripped).

    Returns:
        Content with normalised and numbered headings.
    """
    lines = content.split(chr(10))
    new_lines: List[str] = []
    changes: List[str] = []
    h2_counter = 0
    h3_counter = 0
    in_code_block = False

    for i, line in enumerate(lines):
        stripped = line.rstrip()

        # -- Code-block tracking --
        if _is_code_fence(stripped):
            in_code_block = not in_code_block
            new_lines.append(line)
            continue
        if in_code_block:
            new_lines.append(line)
            continue

        # -- Frontmatter guard --
        if i < fm_end:
            new_lines.append(line)
            continue

        # -- Does this line look like a heading? --
        m = re.match(r'^(#{2,3})\s+(.+)$', stripped)
        if not m:
            new_lines.append(line)
            continue

        level = len(m.group(1))
        text = m.group(2)

        # -- H2 --
        if level == 2:
            # Already numbered -- update counter but do not touch
            if _ALREADY_NUM.match(text):
                m2 = re.match(r'^(\d+)\.\s+(.+)$', text)
                if m2:
                    h2_counter = int(m2.group(1))
                    h3_counter = 0
                new_lines.append(line)
                continue

            original = stripped

            # Sequential normalization (later match may overwrite)
            m2 = _RANGE_LIKE.match(text)
            if m2:
                text = m2.group(1)

            m2 = _DOT_NUM.match(text)
            if m2:
                text = m2.group(1)

            m2 = _CN_PREFIX.match(text)
            if m2:
                text = m2.group(2)

            m2 = _BRACKET_PREFIX.match(text)
            if m2:
                text = m2.group(1)

            h2_counter += 1
            h3_counter = 0
            new_line = f'## {h2_counter}. {text}'
            new_lines.append(new_line)
            changes.append(f"    {original} -> {new_line}")

        # -- H3 --
        elif level == 3:
            # Already numbered -- keep and track sub-counter
            if re.match(r'^\d+\.\d+\s', text):
                m2 = re.match(r'^(\d+)\.(\d+)', text)
                if m2:
                    parent = int(m2.group(1))
                    sub = int(m2.group(2))
                    if parent == h2_counter and sub > h3_counter:
                        h3_counter = sub
                new_lines.append(line)
                continue

            if h2_counter == 0:
                new_lines.append(line)
                continue

            h3_counter += 1
            new_line = f'### {h2_counter}.{h3_counter} {text}'
            new_lines.append(new_line)
            changes.append(f"    {stripped} -> {new_line}")

    if changes:
        print("  🔢 Numbered / normalized headings:")
        for c in changes:
            print(c)

    return chr(10).join(new_lines)

def demote_headings(content: str, fm_end: int = 0) -> str:
    """Demote body headings by one level: H1->H2, H2->H3, H3->H4.

    Code-block aware.  Use this when Halo export-markdown has downgraded
    heading levels and you need to restore the hierarchy.

    Args:
        content: Body text (frontmatter already stripped).
        fm_end: Line index where body content begins (0 when pre-stripped).

    Returns:
        Content with headings demoted one level.
    """
    lines = content.split(chr(10))
    new_lines: List[str] = []
    h1_demoted = 0
    in_code_block = False

    for i, line in enumerate(lines):
        stripped = line.rstrip()

        if _is_code_fence(stripped):
            in_code_block = not in_code_block
            new_lines.append(line)
            continue
        if in_code_block:
            new_lines.append(line)
            continue

        if i < fm_end:
            new_lines.append(line)
            continue

        # Order matters: process deeper levels first
        if stripped.startswith('### '):
            new_lines.append('#### ' + line[4:])
        elif stripped.startswith('## '):
            new_lines.append('### ' + line[3:])
        elif stripped.startswith('# '):
            new_lines.append('## ' + line[2:])
            h1_demoted += 1
        else:
            new_lines.append(line)

    if h1_demoted:
        print(f"  ✅ Demoted {h1_demoted} H1 heading(s) to H2 ")
        print(f"  (and adjusted sub-headings)")

    return chr(10).join(new_lines)


def promote_xy_paragraphs(content: str) -> str:
    """Promote ``X.Y Title`` paragraphs to H3 headings.

    A line matching ``N.N <text>`` is promoted to ``### N.N <text>`` only
    when it is short (<= 100 chars) and preceded by a blank line.  Code
    blocks are skipped.

    Args:
        content: Body text (frontmatter already stripped).

    Returns:
        Content with X.Y paragraphs promoted to H3.
    """
    lines = content.split(chr(10))
    new_lines: List[str] = []
    promoted = 0
    in_code_block = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        if _is_code_fence(stripped):
            in_code_block = not in_code_block
            new_lines.append(line)
            continue
        if in_code_block:
            new_lines.append(line)
            continue

        m = re.match(r'^(\d+)\.(\d+)\s+(.+)$', stripped)
        if not m:
            new_lines.append(line)
            continue

        # Only promote if preceded by a blank line (or at file start)
        pre = lines[i - 1].strip() if i > 0 else ''
        if pre != '':
            new_lines.append(line)
            continue

        text = m.group(3).strip()
        if len(text) > 100:
            new_lines.append(line)
            continue

        new_lines.append(f'### {m.group(1)}.{m.group(2)} {text}')
        promoted += 1

    if promoted:
        print(f"  ✅ Promoted {promoted} X.Y paragraph(s) to H3")

    return chr(10).join(new_lines)


def bold_to_h3(content: str) -> str:
    """Convert standalone bold lines to numbered H3 headings.

    Three bold patterns are recognised:

    1. **Short title** on its own line
    2. **N. Title** trailing body text on same line
    3. **Step N · Title** trailing body text on same line

    Sentence-level bold (ending with 。** / ！** or matching
    conclusion keywords) is left unchanged.

    H2s must already be numbered in *content* (run ``number_headings``
    first).  Code blocks are skipped.

    Args:
        content: Body text with H2s already numbered.

    Returns:
        Content with eligible bold lines promoted to numbered H3s.
    """
    lines = content.split(chr(10))
    new_lines: List[str] = []
    h3_counter: Dict[int, int] = {}
    changes: List[str] = []
    in_code_block = False

    for i, line in enumerate(lines):
        stripped = line.rstrip()

        if _is_code_fence(stripped):
            in_code_block = not in_code_block
            new_lines.append(line)
            continue
        if in_code_block:
            new_lines.append(line)
            continue

        # -- Track already-numbered H3s for sub-counter continuity --
        m = re.match(r'^### (\d+)\.(\d+)\s+', stripped)
        if m:
            parent = int(m.group(1))
            sub = int(m.group(2))
            h3_counter[parent] = max(h3_counter.get(parent, 0), sub)
            new_lines.append(line)
            continue

        # -- Skip H1/H2 (headings are not bold conversion candidates) --
        if re.match(r'^#{1,2}\s', stripped):
            new_lines.append(line)
            continue

        # -- Safety net: bare ### without a number --
        if stripped.startswith('### '):
            parent = _find_parent_h2_number(lines, i)
            if parent is not None:
                h3_counter[parent] = h3_counter.get(parent, 0) + 1
                title = stripped[4:]
                new_line = f'### {parent}.{h3_counter[parent]} {title}'
                new_lines.append(new_line)
                changes.append(f"    {stripped[:50]}... -> {new_line}")
            else:
                new_lines.append(line)
            continue

        # -- Pattern 1: standalone **Title** --
        m = _BOLD_STANDALONE.match(stripped)
        if m:
            title = m.group(1)

            # Heuristics to reject sentence-level bold
            if stripped.rstrip().endswith('。**') or stripped.rstrip().endswith('！**'):
                new_lines.append(line)
                continue
            if re.search(r'[，、；]$', title):
                new_lines.append(line)
                continue
            if _CONCLUSION_KW.search(title):
                new_lines.append(line)
                continue
            if '——' in title:
                new_lines.append(line)
                continue

            parent = _find_parent_h2_number(lines, i)
            if parent is not None and len(title) < 20:
                h3_counter[parent] = h3_counter.get(parent, 0) + 1
                new_line = f'### {parent}.{h3_counter[parent]} {title}'
                new_lines.append(new_line)
                changes.append(f"    {stripped[:50]}... -> {new_line}")
            else:
                new_lines.append(line)
            continue

        # -- Pattern 2: **N. Title** trailing text --
        m = _BOLD_NUM.match(stripped)
        if m:
            title = m.group(2).strip()
            trailing = m.group(3).strip()
            parent = _find_parent_h2_number(lines, i)

            if parent is not None:
                h3_counter[parent] = h3_counter.get(parent, 0) + 1
                new_line = f'### {parent}.{h3_counter[parent]} {title}'
                new_lines.append(new_line)
                changes.append(f"    {stripped[:50]}... -> {new_line}")
                if trailing:
                    new_lines.append('')
                    new_lines.append(trailing)
                continue

            new_lines.append(line)
            continue

        # -- Pattern 3: **Step N · Title** trailing text --
        m = _BOLD_STEP.match(stripped)
        if m:
            step_title = m.group(1).strip()
            trailing = m.group(2).strip()
            parent = _find_parent_h2_number(lines, i)

            if parent is not None:
                h3_counter[parent] = h3_counter.get(parent, 0) + 1
                new_line = f'### {parent}.{h3_counter[parent]} {step_title}'
                new_lines.append(new_line)
                changes.append(f"    {stripped[:50]}... -> {new_line}")
                if trailing:
                    new_lines.append('')
                    new_lines.append(trailing)
                continue

            new_lines.append(line)
            continue

        # -- No match -> pass through --
        new_lines.append(line)

    if changes:
        print(f"  🔢 Converted {len(changes)} bold line(s) to H3 headings:")
        for c in changes:
            print(c)

    return chr(10).join(new_lines)

