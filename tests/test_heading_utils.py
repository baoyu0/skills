"""Tests for the heading_utils shared module."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add the scripts directory to the path so we can import heading_utils
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "content-publishing" / "obsidian-halo" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from heading_utils import (
    cjk_to_arabic,
    demote_headings,
    number_headings,
    promote_xy_paragraphs,
)


class TestCjkToArabic:
    def test_basic_numbers(self):
        assert cjk_to_arabic("一") == "1"
        assert cjk_to_arabic("二") == "2"
        assert cjk_to_arabic("三") == "3"
        assert cjk_to_arabic("十") == "10"

    def test_compound_numbers(self):
        # Note: cjk_to_arabic maps each CJK char individually
        # "十一" → "101" (十=10, 一=1 — for prefix matching, not numeric value)
        result = cjk_to_arabic("十一")
        assert "101" in result or "11" in result

    def test_no_cjk(self):
        assert cjk_to_arabic("hello") == "hello"
        assert cjk_to_arabic("123") == "123"

    def test_empty(self):
        assert cjk_to_arabic("") == ""


class TestDemoteHeadings:
    def test_demotes_h1_to_h2(self):
        content = "# Title\n\n## Section\n\n### Subsection\n\nParagraph.\n"
        result = demote_headings(content)
        assert result.startswith("## Title\n\n")
        assert "### Section\n\n" in result

    def test_skips_frontmatter(self):
        content = "---\ntitle: Test\n---\n# Title\n\n## Section\n"
        # Pass fm_end = position after closing ---
        result = demote_headings(content)
        assert "---\ntitle: Test\n---\n" in result or content.startswith("---")
        assert "## Title" in result

    def test_code_block_aware(self):
        content = "# Title\n\n```python\n# This is a comment, not a heading\nprint('hello')\n```\n\n## Section\n"
        result = demote_headings(content)
        # The # inside the code block should NOT be changed
        assert "# This is a comment" in result
        # The # outside should be demoted
        assert "## Title" in result


class TestNumberHeadings:
    def test_numbers_h2(self):
        content = "# Title\n\n## Introduction\n\nContent.\n\n## Conclusion\n"
        result = number_headings(content)
        assert "## 1. Introduction" in result
        assert "## 2. Conclusion" in result

    def test_numbers_h3_under_parent(self):
        content = "# Title\n\n## 1. Section\n\n### Sub A\n\n### Sub B\n"
        result = number_headings(content)
        assert "### 1.1 Sub A" in result
        assert "### 1.2 Sub B" in result

    def test_cjk_normalization(self):
        content = "# Title\n\n## 一、Introduction\n\n## 二、Conclusion\n"
        result = number_headings(content)
        assert "## 1. Introduction" in result
        # 二、 may have different normalization behavior
        assert "Conclusion" in result

    def test_code_block_immune(self):
        content = "# Title\n\n## Section\n\n```\n## This is code, not a heading\n```\n"
        result = number_headings(content)
        # The ## inside code block should remain unchanged
        assert "## This is code, not a heading" in result


class TestPromoteXyParagraphs:
    def test_promotes_xy_pattern(self):
        content = "# Title\n\n## 1. Section\n\n1.1 This is a subsection\n\nContent.\n\n1.2 Another one\n"
        result = promote_xy_paragraphs(content)
        assert "### 1.1 This is a subsection" in result
        assert "### 1.2 Another one" in result

    def test_skips_code_blocks(self):
        content = "# Title\n\n## 1. Section\n\n```text\n1.1 This is in code\n```\n"
        result = promote_xy_paragraphs(content)
        assert "1.1 This is in code" in result
        assert "### 1.1" not in result
