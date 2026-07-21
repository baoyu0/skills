"""Tests for x-clip-purify utility functions."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

# Import the module by file path since it has a hyphen in the name
SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "content-publishing" / "x-clip-purify" / "scripts" / "x-clip-purify.py"
)
spec = importlib.util.spec_from_file_location("x_clip_purify", SCRIPT_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

slug_from_title = mod.slug_from_title
split_frontmatter = mod.split_frontmatter
join_frontmatter = mod.join_frontmatter


class TestSplitFrontmatter:
    def test_with_frontmatter(self):
        content = "---\ntitle: Test\nslug: test\n---\n\nBody text"
        fm, body, has = split_frontmatter(content)
        assert has is True
        assert "title: Test" in fm
        assert "Body text" in body

    def test_without_frontmatter(self):
        content = "Just body text\n\nNo frontmatter."
        fm, body, has = split_frontmatter(content)
        assert has is False
        assert fm == ""
        assert "Just body text" in body

    def test_empty_content(self):
        fm, body, has = split_frontmatter("")
        assert has is False
        assert body == ""

    def test_unclosed_frontmatter(self):
        content = "---\ntitle: Test\nNo closing dash"
        fm, body, has = split_frontmatter(content)
        assert has is False
        assert body == content


class TestJoinFrontmatter:
    def test_roundtrip(self):
        fm = "\ntitle: Test\nslug: test\n"
        body = "\nBody text"
        result = join_frontmatter(fm, body)
        assert result == "---\ntitle: Test\nslug: test\n---\nBody text"

    def test_empty_body(self):
        result = join_frontmatter("\ntitle: Test\n", "")
        assert result == "---\ntitle: Test\n---"


class TestSlugFromTitle:
    def test_ascii_title(self):
        slug = slug_from_title("Hello World Test")
        assert slug == "hello-world-test"

    def test_mixed_chars(self):
        slug = slug_from_title("Hello! @World #2024")
        assert "hello" in slug
        assert "world" in slug

    def test_cjk_title(self):
        slug = slug_from_title("我的博客文章")
        # CJK-only should fall back to timestamp-based slug
        assert slug.startswith("post-")
        assert len(slug) > 5

    def test_empty_title(self):
        slug = slug_from_title("")
        assert slug.startswith("post-")
