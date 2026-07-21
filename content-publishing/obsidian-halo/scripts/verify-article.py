#!/usr/bin/env python3
"""Ad-hoc verification: validate obsidian-halo enhanced markdown file integrity.

Usage:
    python scripts/verify-article.py <file_path>

Checks:
  - Frontmatter has valid YAML delimiters
  - title, slug, cover, halo.* are present
  - categories (>=1) and tags (>=3) are populated
  - All H2 headings are numbered (1., 2., ... pattern)
  - No unnumbered H2 headings remain
  - No raw HTML tags leaked from clippings (video, blob:, iframe)
  - File size is reasonable (> 1 KB)
"""

from __future__ import annotations

import sys, os, re
from typing import NoReturn

def main() -> NoReturn:
    if len(sys.argv) < 2:
        print("Usage: python verify-halo-article.py <file_path>")
        sys.exit(1)

    filepath: str = sys.argv[1]
    if not os.path.exists(filepath):
        print(f"FAIL: File not found: {filepath}")
        sys.exit(1)

    with open(filepath, encoding="utf-8") as f:
        text: str = f.read()

    errors: list[str] = []
    checks: list[str] = []

    def check(ok: bool, msg: str) -> None:
        if ok:
            checks.append(f"  PASS  {msg}")
        else:
            checks.append(f"  FAIL  {msg}")
            errors.append(msg)

    # 1. File size
    size: int = os.path.getsize(filepath)
    check(size > 1000, f"file size = {size:,} bytes")

    # 2. Frontmatter
    check(text.startswith("---"), "frontmatter starts with ---")
    fm_end: int = text.find("---", 3)
    check(fm_end > 3, "frontmatter has closing ---")
    fm: str = text[4:fm_end].strip()

    # 3. Required frontmatter fields
    check("title:" in fm, "title field present")
    check("slug:" in fm, "slug field present")
    check("cover:" in fm, "cover field present")
    check("halo:" in fm, "halo block present")

    # 4. Categories and tags
    check("categories:" in fm, "categories present")
    cats: list[str] = re.findall(r"^\s+-\s+(.+)", text[text.find("categories:"):text.find("tags:")]) if "categories:" in fm else []
    check(len(cats) >= 1, f"categories: {len(cats)} found")

    if "tags:" in fm:
        tags_start: int = text.find("tags:")
        # tags end at next top-level field or ---
        tags_section: str = text[tags_start:fm_end]
        tags: list[str] = re.findall(r"^\s+-\s+(.+)", tags_section, re.MULTILINE)
        check(len(tags) >= 3, f"tags: {len(tags)} found (≥3)")

    # 5. Numbered H2 headings
    body: str = text[fm_end + 3:]
    h2s: list[str] = re.findall(r"^## (.+)", body, re.MULTILINE)
    numbered: list[str] = [h for h in h2s if re.match(r"\d+\.", h)]
    unnumbered: list[str] = [h for h in h2s if not re.match(r"\d+\.", h) and "Anchor" not in h]

    check(len(numbered) >= 3, f"numbered H2 headings: {len(numbered)} (≥3)")
    check(len(unnumbered) == 0, f"no unnumbered H2 (found {len(unnumbered)}): {unnumbered}")

    # 6. No raw HTML tags leaked from clippings
    raw_video: int = len(re.findall(r'<video\b', body, re.IGNORECASE))
    raw_iframe: int = len(re.findall(r'<iframe\b', body, re.IGNORECASE))
    blob_refs: int = len(re.findall(r'blob:', body, re.IGNORECASE))
    check(raw_video == 0, f"no raw <video> tags (found {raw_video})")
    check(raw_iframe == 0, f"no raw <iframe> tags (found {raw_iframe})")
    check(blob_refs == 0, f"no blob: references (found {blob_refs})")

    # 7. (removed: slug ASCII check — Halo auto-generates slug, no need to enforce ASCII)

    # 8. Verify numbered sequence is continuous
    nums: list[int] = []
    for h in numbered:
        m = re.match(r"(\d+)", h)
        if m:
            nums.append(int(m.group(1)))
    if nums:
        expected: list[int] = list(range(1, max(nums)))
        missing: list[int] = [n for n in expected if n not in nums]
        check(len(missing) == 0, f"no gaps in numbering sequence (missing: {missing})")

    # Print report
    print("=" * 60)
    print(f"obsidian-halo 文章验证: {os.path.basename(filepath)}")
    print("=" * 60)
    for c in checks:
        print(c)
    print("-" * 60)
    if errors:
        print(f"\n❌ {len(errors)} failure(s):")
        for e in errors:
            print(f"   - {e}")
        sys.exit(1)
    else:
        print(f"\n✅ All {len(checks)} checks passed")
        print(f"   File: {filepath}")
        print(f"   Headings: {len(numbered)} numbered, {len(unnumbered)} unnumbered")


if __name__ == "__main__":
    main()
