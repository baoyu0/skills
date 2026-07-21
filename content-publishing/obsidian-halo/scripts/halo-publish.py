#!/usr/bin/env python3
"""
Halo Publish Script — six modes for the complete Obsidian-Halo workflow.

Usage:
  python halo-publish.py create <file>     # Strip frontmatter, upload raw, publish
  python halo-publish.py pull <file>       # Pull post from Halo, write frontmatter
  python halo-publish.py enhance <file>    # Auto-number H2/H3 headings
  python halo-publish.py update <file>     # Update post on Halo with enhanced content
  python halo-publish.py verify <file>     # Verify published page is accessible
  python halo-publish.py detect <file>     # Detect article language (en/zh)

State tracking: after create, UUID is saved to ~/.hermes/halo-state.json
Keyed by the file's absolute path.

Requires: pip install pyyaml requests
"""

import sys, os, json, re, uuid, yaml, requests, time, shutil
from pathlib import Path
from markdown_it import MarkdownIt

md_renderer = MarkdownIt("gfm-like", {"breaks": True, "linkify": False})

# ── Config ──
CONFIG_FILE = Path.home() / ".hermes" / "halo-config.json"
STATE_FILE  = Path.home() / ".hermes" / "halo-state.json"

def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f: cfg = json.load(f)
        pat, base_url = cfg.get("pat"), cfg.get("url", "https://jia.baoyu2023.top")
    else:
        pat, base_url = os.environ.get("HALO_PAT"), os.environ.get("HALO_URL", "https://jia.baoyu2023.top")
    if not pat:
        print("ERROR: No HALO_PAT. Set in ~/.hermes/halo-config.json or env var HALO_PAT.")
        sys.exit(1)
    return pat, base_url.rstrip("/")

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f: return json.load(f)
    return {}

def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f: json.dump(state, f, indent=2)

def get_uuid_for(filepath):
    state = load_state()
    return state.get(str(Path(filepath).resolve()))

def set_uuid_for(filepath, uuid_val):
    state = load_state()
    state[str(Path(filepath).resolve())] = uuid_val
    save_state(state)


# ── API ──
class HaloAPI:
    def __init__(self, base_url, pat):
        self.base_url = base_url
        self.h = {"Authorization": f"Bearer {pat}", "Content-Type": "application/json"}
        # Transient-failure retry: up to 3 tries with backoff
        adapter = requests.adapters.HTTPAdapter(max_retries=requests.urllib3.Retry(
            total=3, backoff_factor=1, status_forcelist=[502, 503, 504]))
        self._sess = requests.Session()
        self._sess.mount("https://", adapter)
        self._sess.mount("http://", adapter)

    def _get(self, path):
        r = self._sess.get(f"{self.base_url}{path}", headers=self.h, timeout=30)
        r.raise_for_status(); return r.json()
    def _post(self, path, data):
        r = self._sess.post(f"{self.base_url}{path}", headers=self.h, json=data, timeout=30)
        r.raise_for_status(); return r.json()
    def _put(self, path, data=None):
        r = self._sess.put(f"{self.base_url}{path}", headers=self.h, json=data or {}, timeout=30)
        r.raise_for_status(); return r.json()

    def get_post(self, name):
        return self._get(f"/apis/uc.api.content.halo.run/v1alpha1/posts/{name}")
    def get_post_draft(self, name):
        return self._get(f"/apis/uc.api.content.halo.run/v1alpha1/posts/{name}/draft?patched=true")

    def create_raw_post(self, raw_md, title=""):
        """Create a new post with raw markdown. Halo will auto-generate metadata."""
        post_name = str(uuid.uuid4())
        html = md_renderer.render(raw_md)
        content_json = json.dumps({"raw": raw_md, "content": html, "rawType": "markdown"}, ensure_ascii=False)
        body = {
            "apiVersion": "content.halo.run/v1alpha1", "kind": "Post",
            "metadata": {"name": post_name, "annotations": {"content.halo.run/content-json": content_json}},
            "spec": {"title": title or "Untitled", "slug": "untitled",
                     "categories": [], "tags": [], "cover": "",
                     "publish": False, "visible": "PUBLIC", "allowComment": True,
                     "deleted": False, "priority": 0, "pinned": False,
                     "excerpt": {"autoGenerate": True, "raw": ""}, "htmlMetas": [], "template": "",
                     "baseSnapshot": "", "headSnapshot": "", "releaseSnapshot": "", "owner": "", "publishTime": ""}}
        print("  Creating post...")
        return self._post("/apis/uc.api.content.halo.run/v1alpha1/posts", body)

    def publish(self, name):
        print("  Publishing...")
        self._put(f"/apis/uc.api.content.halo.run/v1alpha1/posts/{name}/publish")

    def update_post_content(self, name, raw_md):
        """Update the draft content of an existing post."""
        snapshot = self.get_post_draft(name)
        ann = snapshot.get("metadata", {}).get("annotations", {})
        raw_type = snapshot.get("spec", {}).get("rawType", "markdown")
        html = md_renderer.render(raw_md)
        content_json = json.dumps({"raw": raw_md, "content": html, "rawType": raw_type}, ensure_ascii=False)
        ann["content.halo.run/content-json"] = content_json
        snapshot["metadata"]["annotations"] = ann
        print("  Updating content...")
        self._put(f"/apis/uc.api.content.halo.run/v1alpha1/posts/{name}/draft", snapshot)

    def update_post_metadata(self, name, title, slug, categories_display, tags_display, cover=""):
        """Update post metadata (title, slug, cat, tags, cover)."""
        cat_names = self._resolve_category_names(categories_display)
        tag_names = self._resolve_tag_names(tags_display)

        post = self.get_post(name)
        post["spec"]["title"] = title
        post["spec"]["slug"] = slug
        post["spec"]["categories"] = cat_names
        post["spec"]["tags"] = tag_names
        if cover:
            post["spec"]["cover"] = cover

        print("  Updating metadata...")
        self._put(f"/apis/uc.api.content.halo.run/v1alpha1/posts/{name}", post)

    def _resolve_category_names(self, display_names):
        data = self._get("/apis/content.halo.run/v1alpha1/categories")
        existing = {i["spec"]["displayName"]: i["metadata"]["name"] for i in data.get("items", [])}
        result = []
        for name in display_names:
            if name in existing:
                result.append(existing[name])
            else:
                print(f"  Creating category: {name}")
                c = self._post("/apis/content.halo.run/v1alpha1/categories", {
                    "apiVersion": "content.halo.run/v1alpha1", "kind": "Category",
                    "metadata": {"name": "", "generateName": "category-"},
                    "spec": {"displayName": name, "slug": slugify(name),
                             "description": "", "cover": "", "template": "",
                             "priority": 0, "children": []}})
                result.append(c["metadata"]["name"])
        return result

    def _resolve_tag_names(self, display_names):
        data = self._get("/apis/content.halo.run/v1alpha1/tags")
        existing = {i["spec"]["displayName"]: i["metadata"]["name"] for i in data.get("items", [])}
        result = []
        for name in display_names:
            if name in existing:
                result.append(existing[name])
            else:
                print(f"  Creating tag: {name}")
                t = self._post("/apis/content.halo.run/v1alpha1/tags", {
                    "apiVersion": "content.halo.run/v1alpha1", "kind": "Tag",
                    "metadata": {"name": "", "generateName": "tag-"},
                    "spec": {"displayName": name, "slug": slugify(name),
                             "color": "#ffffff", "cover": ""}})
                result.append(t["metadata"]["name"])
        return result

    @staticmethod
    def get_category_display_names(base_url, pat, names):
        h = {"Authorization": f"Bearer {pat}"}
        data = requests.get(f"{base_url}/apis/content.halo.run/v1alpha1/categories", headers=h, timeout=30).json()
        m = {v["metadata"]["name"]: v["spec"]["displayName"] for v in data.get("items", [])}
        return [m.get(n, n) for n in names]

    @staticmethod
    def get_tag_display_names(base_url, pat, names):
        h = {"Authorization": f"Bearer {pat}"}
        data = requests.get(f"{base_url}/apis/content.halo.run/v1alpha1/tags", headers=h, timeout=30).json()
        m = {v["metadata"]["name"]: v["spec"]["displayName"] for v in data.get("items", [])}
        return [m.get(n, n) for n in names]


def slugify(text):
    s = text.lower().strip()
    s = re.sub(r'[\u4e00-\u9fff]+', '', s)
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-')[:200] or "post"


def parse_frontmatter(md):
    md = md.lstrip('\ufeff')
    if md.startswith('---'):
        parts = md.split('---', 2)
        if len(parts) >= 3:
            try: return yaml.safe_load(parts[1]) or {}, parts[2]
            except yaml.YAMLError: pass
    return {}, md

def build_fm(fm):
    return f"---\n{yaml.dump(fm, allow_unicode=True, sort_keys=False).strip()}\n---\n"


# ── Modes ──

def cmd_create(filepath):
    """Strip frontmatter, upload raw markdown to Halo, publish. Save UUID."""
    md = Path(filepath).read_text(encoding="utf-8")
    fm, body = parse_frontmatter(md)
    raw_body = body.strip()

    pat, base_url = load_config()
    api = HaloAPI(base_url, pat)

    # Priority: frontmatter title > first ATX heading > filename stem
    title = (fm.get("title") or "").strip()
    if not title:
        title = Path(filepath).stem
        lines = raw_body.split('\n')
        in_code = False
        for line in lines:
            if line.strip().startswith('```'):
                in_code = not in_code
                continue
            if not in_code:
                m = re.match(r'^#{1,6}\s+(.+)$', line)
                if m:
                    # Strip numbering prefixes like "0.1- ", "1、", "1. "
                    t = m.group(1).strip()
                    t = re.sub(r'^[\d.]+[-\s、.]+', '', t).strip()
                    if t:
                        title = t
                        break

    print(f"📤 Uploading raw: {title}")
    post = api.create_raw_post(raw_body, title)

    post_name = post["metadata"]["name"]
    # Set title only — let Halo auto-generate slug from title during publish
    post["spec"]["title"] = title
    # Don't set slug — Halo generates a proper one from the title
    print("  Updating title...")
    api._put(f"/apis/uc.api.content.halo.run/v1alpha1/posts/{post_name}", post)

    api.publish(post_name)
    set_uuid_for(filepath, post_name)

    # Write placeholder: stripped body only (no frontmatter)
    Path(filepath).write_text(raw_body + "\n", encoding="utf-8")

    print(f"✅ Created & published")
    print(f"   UUID: {post_name}")
    print(f"   Title: {title}")
    return post_name


def cmd_pull(filepath):
    """Pull post from Halo, write Halo-generated frontmatter to file.
    Polls until cover is ready (timeout 30s) — no more blind sleeps.
    """
    uuid_val = get_uuid_for(filepath)
    if not uuid_val:
        print("ERROR: No UUID found for this file. Run 'create' first.")
        sys.exit(1)

    pat, base_url = load_config()
    api = HaloAPI(base_url, pat)

    print(f"📥 Pulling post (UUID={uuid_val})...")

    # Poll until cover is ready
    cover = ""
    for attempt in range(10):  # 10 × 3s = 30s total
        post = api.get_post(uuid_val)
        spec = post.get("spec", {})
        cover = (spec.get("cover") or "").strip()
        if cover:
            if attempt > 0:
                print(f"   Cover ready after ~{attempt * 3}s")
            break
        if attempt == 0:
            print("   Waiting for Halo to generate cover...")
        time.sleep(3)

    draft = api.get_post_draft(uuid_val)
    ann = draft.get("metadata", {}).get("annotations", {})
    raw = ann.get("content.halo.run/patched-raw", "")

    # Get display names for categories and tags
    cat_ids = spec.get("categories", [])
    tag_ids = spec.get("tags", [])
    cat_display = HaloAPI.get_category_display_names(base_url, pat, cat_ids)
    tag_display = HaloAPI.get_tag_display_names(base_url, pat, tag_ids)

    fm = {
        "title": spec.get("title", ""),
        "slug": spec.get("slug", ""),
    }
    if cover:
        fm["cover"] = cover
    if cat_display:
        fm["categories"] = cat_display
    if tag_display:
        fm["tags"] = tag_display
    fm["halo"] = {
        "site": base_url,
        "name": uuid_val,
        "publish": spec.get("publish", False),
    }

    result = build_fm(fm) + raw.strip() + "\n"
    Path(filepath).write_text(result, encoding="utf-8")

    print(f"✅ Frontmatter written to file")
    print(f"   Title: {fm['title']}")
    print(f"   Cover: {cover or '(none)'}")
    print(f"   Cats: {cat_display}")
    print(f"   Tags: {tag_display}")
    return fm


def cmd_update(filepath):
    """Push the enhanced file back to Halo (content + metadata)."""
    md = Path(filepath).read_text(encoding="utf-8")
    fm, body = parse_frontmatter(md)
    uuid_val = fm.get("halo", {}).get("name") if isinstance(fm.get("halo"), dict) else get_uuid_for(filepath)

    if not uuid_val:
        print("ERROR: No UUID in frontmatter or state. Run 'create' and 'pull' first.")
        sys.exit(1)

    pat, base_url = load_config()
    api = HaloAPI(base_url, pat)
    raw_body = body.strip()

    title = fm.get("title", "")
    slug = fm.get("slug", "")
    cover = fm.get("cover", "")
    cats = fm.get("categories", [])
    tags = fm.get("tags", [])

    print(f"📝 Updating post (UUID={uuid_val})...")
    api.update_post_metadata(uuid_val, title, slug, cats, tags, cover)
    api.update_post_content(uuid_val, raw_body)
    # Re-publish to apply draft changes to published version
    api.publish(uuid_val)

    print(f"✅ Updated: {title}")
    print(f"   URL: {base_url}/archives/{slug}")

    # Auto-verify
    return _verify_post(base_url, slug, title)


def _verify_post(base_url, slug, title):
    """Verify published page: HTTP 200 + title match + HTML quality checks."""
    url = f"{base_url}/archives/{slug}?nocache=1"
    print(f"\n🔍 Verifying: {url}")
    try:
        r = requests.get(url, timeout=15, allow_redirects=True)
        if r.status_code == 200:
            # Force UTF-8 decode (Halo may not signal charset in Content-Type)
            body = r.content.decode("utf-8")
            issues = []
            if title:
                if title in body:
                    print(f"   ✅ HTTP 200 — title match")
                else:
                    print(f"   ⚠️  HTTP 200 — title not found in body (may be JS-rendered)")
                    issues.append("Title not found in HTML body")
            else:
                print(f"   ✅ HTTP 200 (no title to match)")

            # HTML quality checks
            for tag, name in [("video", "<video>"), ("iframe", "<iframe>"),
                               ("embed", "<embed>")]:
                if f"<{tag}" in body:
                    issues.append(f"⚠️  Raw {name} found in rendered page")
            if "blob:" in body:
                issues.append("⚠️  blob: URL found in rendered page")

            if issues:
                for i in issues:
                    print(f"   {i}")
                print(f"   ⚠️  Page has {len(issues)} issue(s) — review recommended")
            else:
                print(f"   ✅ HTML quality check passed (no hidden embeds)")

            return True
        else:
            print(f"   ❌ HTTP {r.status_code}")
            return False
    except requests.RequestException as e:
        print(f"   ❌ Request failed: {e}")
        return False


def cmd_verify(filepath):
    """Verify a published Halo post is accessible."""
    md = Path(filepath).read_text(encoding="utf-8")
    fm, _ = parse_frontmatter(md)
    pat, base_url = load_config()
    slug = fm.get("slug", "")
    title = fm.get("title", "")
    if not slug:
        print("ERROR: No slug in frontmatter.")
        sys.exit(1)
    ok = _verify_post(base_url, slug, title)
    if ok:
        print("✅ Verification passed")
    else:
        print("❌ Verification failed")
        sys.exit(1)


def cmd_enhance(filepath):
    """Enhance article: number H2 headings, promote X.Y sub-sections to H3,
    report stats, detect flat structure. Idempotent — safe to run multiple times.
    """
    md = Path(filepath).read_text(encoding="utf-8")
    fm, body = parse_frontmatter(md)
    raw_body = body.strip()
    lines = raw_body.split('\n')

    # ── Phase 0: Demote H1 body headings (H1→H2, H2→H3, H3→H4) ──
    # H1 body headings cause flat TOC since the article title is already H1 from frontmatter
    h1_demoted = 0
    new_lines = []
    for line in lines:
        # Demote ### → #### (must be before ## → ###)
        if line.startswith('### '):
            new_lines.append('#### ' + line[4:])
        # Demote ## → ### (must be before # → ##)
        elif line.startswith('## '):
            new_lines.append('### ' + line[3:])
        # Demote # → ## (body H1 only, not frontmatter H1)
        elif line.startswith('# '):
            new_lines.append('## ' + line[2:])
            h1_demoted += 1
        else:
            new_lines.append(line)
    if h1_demoted:
        print(f"   ✅ Demoted {h1_demoted} H1 heading(s) to H2 (and adjusted sub-headings)")
    lines = new_lines

    # ── Phase A: Promote X.Y pattern paragraphs to H3 ──
    h3_promoted = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Match "X.Y Some Title" or "X.Y一些文字" where X and Y are digits
        m = re.match(r'^(\d+)\.(\d+)\s+(.+)$', stripped)
        if not m:
            continue
        # Only promote near-blank-line-delimited paragraphs that look like headings (short)
        text = m.group(3).strip()
        if len(text) > 100:
            continue  # too long, likely a body paragraph
        # Only promote if it starts clean (after blank line or at file start)
        pre = lines[i-1].strip() if i > 0 else ""
        if pre == "":
            lines[i] = f"### {m.group(1)}.{m.group(2)} {text}"
            h3_promoted += 1

    # ── Phase B: Number headings (skip if already numbered) ──
    h2_counter = 0
    h3_counter = 0
    h2_changed = 0
    for i, line in enumerate(lines):
        s = line.strip()
        m = re.match(r'^##\s+(.+)$', s)
        if m:
            content = m.group(1).strip()
            if re.match(r'^\d+(\.\d+)?[\.\s]', content):
                m2 = re.match(r'^(\d+)', content)
                if m2:
                    h2_counter = int(m2.group(1))
                    h3_counter = 0
                continue
            h2_counter += 1
            h3_counter = 0
            lines[i] = line.replace("## ", f"## {h2_counter}. ", 1)
            h2_changed += 1
            continue
        m = re.match(r'^###\s+(.+)$', s)
        if m:
            content = m.group(1).strip()
            if re.match(r'^\d+(\.\d+)?[\.\s]', content) or h2_counter == 0:
                continue
            h3_counter += 1
            lines[i] = f"### {h2_counter}.{h3_counter} {content}"
            h2_changed += 1

    # ── Write back ──
    new_body = '\n'.join(lines)
    Path(filepath).write_text(build_fm(fm) + new_body + "\n", encoding="utf-8")

    # ── Report ──
    h2s = re.findall(r'^##\s+\d+\.\s+.+', new_body, re.MULTILINE)
    h3s = re.findall(r'^###\s+\d+\.\d+\s+.+', new_body, re.MULTILINE)
    h4s = re.findall(r'^####\s+.+', new_body, re.MULTILINE)
    wc = len(new_body.split())
    has_h3_natural = bool(re.findall(r'^###\s', new_body, re.MULTILINE))
    print(f"📊 [{Path(filepath).name}]")
    print(f"   Headings: {len(h2s)} H2 + {len(h3s)} H3 + {len(h4s)} H4 = {len(h2s)+len(h3s)+len(h4s)} total")
    if h3_promoted:
        print(f"   ✅ Promoted {h3_promoted} X.Y sub-section(s) to H3")
    print(f"   Changes: {h2_changed} heading(s) numbered")
    print(f"   Words: ~{wc}")
    for h in h2s:
        print(f"     {h.strip()}")
    # Detect flat structure
    if len(h2s) >= 3 and not has_h3_natural and h3_promoted == 0:
        print("   ⚠️  Flat H2-only structure — consider splitting long sections into H3 sub-sections")
    if not fm.get("categories"):
        print("   ⚠️  No categories — recommend adding some")
    if not fm.get("tags"):
        print("   ⚠️  No tags — recommend adding some")


def cmd_detect(filepath):
    """Detect primary language of article body. Exits 0 if Chinese, 1 if English."""
    md = Path(filepath).read_text(encoding="utf-8")
    fm, body = parse_frontmatter(md)
    raw = body.strip()

    # Remove code blocks, URLs, and data: URIs (not relevant for language detection)
    no_code = re.sub(r'```.*?```', '', raw, flags=re.DOTALL)
    no_code = re.sub(r'https?://\S+', '', no_code)
    no_code = re.sub(r'data:[^,]+,[A-Za-z0-9+/=]{100,}', '', no_code)
    plain = re.sub(r'[#*_`~>\[\]()|]', '', no_code)

    # Count Chinese characters vs English letters
    cn_chars = len(re.findall(r'[\u4e00-\u9fff]', plain))
    en_letters = len(re.findall(r'[a-zA-Z]', plain))
    en_words = len(re.findall(r'[a-zA-Z]+', plain))
    meaningful = cn_chars + en_letters
    ratio = cn_chars / meaningful if meaningful > 0 else 0

    print(f"🌐 [{Path(filepath).name}]")
    print(f"   Chinese chars: {cn_chars} | English letters: {en_letters} | CJK ratio: {ratio:.1%}")

    if ratio >= 0.20:
        print(f"   ✅ 中文文章，无需翻译")
        if en_words > 100 and ratio < 0.60:
            print(f"   💡 含较多英文 ({en_words} 词)，可选择性翻译部分段落")
        sys.exit(0)
    else:
        sample = re.sub(r'\s+', ' ', raw[:200]).strip()
        print(f"   ⚠️ 英文文章，需要翻译")
        print(f"   Preview: {sample[:120]}...")
        sys.exit(1)


# ── Cleanup Mode ──

def cmd_cleanup(filepath):
    """Scan the article body and fix common embeds that break on Halo.
    - Replace <video>/<audio> tags containing blob: URLs with clickable poster images
    - Detect raw <iframe>, <embed>, <object> tags and report them
    - Strip orphaned timestamp lines ("0:02 / 0:32") left after video removal
    - Idempotent — safe to run multiple times.
    """
    md = Path(filepath).read_text(encoding="utf-8")
    fm, body = parse_frontmatter(md)
    raw_body = body.strip()
    source_url = (fm.get("source") or "").strip()
    changes = []

    # ── 1. Replace <video>/<audio> with blob: → poster image ──
    def replace_media_blob(match):
        tag = match.group(0)
        inner = match.group(1)
        poster = ""
        poster_m = re.search(r'''poster\s*=\s*["']([^"']+)["']''', tag, re.IGNORECASE)
        if poster_m:
            poster = poster_m.group(1)
        has_blob = "blob:" in inner or "blob:" in tag
        if not has_blob and not poster:
            return tag  # no blob and no poster, leave it
        alt_text = "视频截图"
        if has_blob:
            changes.append(f"  Removed <{match.re.pattern[:5]}> with blob: URL")
            if poster:
                if source_url:
                    return f"[![{alt_text}]({poster})]({source_url})"
                else:
                    return f"![{alt_text}]({poster})"
            else:
                return ""
        return tag

    # Match <video...>...</video> and <audio...>...</audio>
    new_body = re.sub(
        r'<(video|audio)\b([^>]*)>.*?</\1\s*>',
        replace_media_blob, raw_body, flags=re.DOTALL | re.IGNORECASE
    )

    # Also match self-closing <video>/<audio> (edge case)
    if new_body == raw_body:
        new_body = re.sub(
            r'<(video|audio)\b[^>]*?/>',
            replace_media_blob, new_body, flags=re.DOTALL | re.IGNORECASE
        )

    # ── 2. Strip orphaned timestamp lines like "0:02 / 0:32" ──
    timestamp_count = 0
    def strip_timestamp(m):
        nonlocal timestamp_count
        # Only strip if preceded by another blank line or start of section
        # to avoid stripping legitimate text
        pre = m.string[max(0, m.start()-20):m.start()]
        if '\n\n' in pre or m.start() == 0:
            timestamp_count += 1
            return ""
        return m.group(0)
    new_body = re.sub(r'^\d+:\d{2}\s*/\s*\d+:\d{2}\s*$', strip_timestamp, new_body, flags=re.MULTILINE)
    if timestamp_count:
        changes.append(f"  Removed {timestamp_count} orphaned timestamp line(s)")

    # ── 3. Warn about raw <iframe>/<embed>/<object> tags ──
    for tag_name in ["iframe", "embed", "object"]:
        remaining = re.findall(f'<{tag_name}\b', new_body, re.IGNORECASE)
        if remaining:
            changes.append(f"  ⚠️  Found {len(remaining)} raw <{tag_name}> tag(s) — review manually")

    # ── 4. Warn about remaining blob: references ──
    leftover_blob = re.findall(r'blob:', new_body, re.IGNORECASE)
    if leftover_blob:
        changes.append(f"  ⚠️  {len(leftover_blob)} blob: reference(s) still remain — review manually")

    # ── 5. obu CDN extraction removed — obu_extract.py is deprecated ──
    # X Article 视频无法通过 CLI/CDP 自动化下载。
    # 见 references/x-article-video-handling.md。
                if result_file.exists():
                    result_file.unlink(missing_ok=True)

    # Write back if anything changed
    if changes:
        Path(filepath).write_text(build_fm(fm) + new_body + "\n", encoding="utf-8")

    print(f"🧹 [{Path(filepath).name}]")
    for c in changes:
        print(c)
    if not changes:
        print("   No cleanup needed — body is clean")
    return len(changes) > 0


# ── Auto Mode ──

def cmd_auto(filepath):
    """Run the full script pipeline: detect → create → pull → cleanup → enhance → update → verify.
    Stops at AI-reasoning boundary and prints a next-steps checklist.
    """
    fp = Path(filepath)
    print(f"╔══ Auto: {fp.name} ══╗\n")

    # 0. Detect language
    print("── Phase 0: Detect ──")
    pat, base_url = load_config()
    md = fp.read_text(encoding="utf-8")
    fm_pre, _ = parse_frontmatter(md)
    source_url = (fm_pre.get("source") or "").strip()

    # Quick lang heuristic for auto mode
    body_no_fm = re.sub(r'^---.*?---\s*', '', md, count=1, flags=re.DOTALL)
    # Exclude base64 data URIs which are all ASCII and skew detection
    body_no_fm = re.sub(r'data:[^,]+,[A-Za-z0-9+/=]{100,}', '', body_no_fm)
    cn = len(re.findall(r'[\u4e00-\u9fff]', body_no_fm))
    en = len(re.findall(r'[a-zA-Z]', body_no_fm))
    total = cn + en
    ratio = cn / total if total > 0 else 0
    if total > 0 and ratio < 0.20:
        print(f"   ⚠️  English article (CJK={ratio:.0%}). Auto stops — needs translation.\n")
        print("   Next: translate body to Chinese, then run:")
        print(f"     python halo-publish.py create \"{filepath}\"")
        sys.exit(1)
    print(f"   ✅ Chinese ({cn}/{total}, {ratio:.0%})")

    if source_url:
        print(f"   Source: {source_url}")

    # 1. Create
    print("\n── Phase 1: Create ──")
    try:
        cmd_create(filepath)
    except Exception as e:
        print(f"   ❌ Create failed: {e}")
        sys.exit(1)

    # 2. Pull
    print("\n── Phase 2: Pull ──")
    try:
        cmd_pull(filepath)
    except Exception as e:
        print(f"   ❌ Pull failed: {e}")
        sys.exit(1)

    # 3. Cleanup
    print("\n── Phase 3: Cleanup ──")
    cmd_cleanup(filepath)

    # 4. Enhance
    print("\n── Phase 4: Enhance ──")
    cmd_enhance(filepath)

    # Re-read final frontmatter
    final_md = fp.read_text(encoding="utf-8")
    fm_final, body_final = parse_frontmatter(final_md)
    slug = fm_final.get("slug", "")
    title = fm_final.get("title", "")
    has_cats = bool(fm_final.get("categories"))
    has_tags = bool(fm_final.get("tags"))

    # 5. Update + Verify
    if slug:
        print("\n── Phase 5: Update & Verify ──")
        try:
            cmd_update(filepath)
        except Exception as e:
            print(f"   ❌ Update failed: {e}")
            sys.exit(1)

    # ── Save processing report to vault ──
    vault = Path("D:/1-obsidian/halo")
    report = vault / f"_report-{fp.stem}.md"
    lines_r = [
        f"# Halo Publish Report: {title}",
        f"",
        f"- **File**: {fp.name}",
        f"- **URL**: https://jia.baoyu2023.top/archives/{slug}",
        f"- **Status**: Published",
        f"- **Source**: {source_url or '(none)'}",
        f"",
        f"## Phase Progress",
        f"- [x] Detect (Chinese: {ratio:.0%})",
        f"- [x] Create",
        f"- [x] Pull",
        f"- [x] Cleanup",
        f"- [x] Enhance",
        f"- [x] Update & Verify",
        f"",
        f"## ⚠️  AI Attention Needed",
    ]
    if not has_cats:
        lines_r.append(f"- [ ] Add categories to frontmatter")
    if not has_tags:
        lines_r.append(f"- [ ] Add tags to frontmatter")
    if slug and re.search(r'[\u4e00-\u9fff]', fm_final.get("slug", "")):
        lines_r.append(f"- [ ] Fix slug (remove Chinese characters for cleaner URL)")
    # Check for remaining <iframe>/<embed> warnings
    if "<iframe" in body_final or "<embed" in body_final:
        lines_r.append(f"- [ ] Review remaining HTML embed tags in body")

    vault.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines_r) + "\n", encoding="utf-8")

    print(f"\n   📄 Report saved: {report}")

    # ── Summary ──
    print(f"\n╔══ Summary ══╗")
    print(f"   ✅ Published: {title}")
    print(f"   📎 {base_url}/archives/{slug}")
    print(f"   📄 {report.name}")
    ai_items = len(lines_r) - lines_r.index("## ⚠️  AI Attention Needed") - 1
    print(f"")
    if ai_items > 0:
        print(f"   ⚠️  {ai_items} item(s) need AI attention — see report above")
    else:
        print(f"   ✅ No AI attention items — ready to go")
    return True


# ── Main ──
def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <create|pull|update|verify|enhance|detect|cleanup|auto> <file>")
        sys.exit(1)

    mode, filepath = sys.argv[1], sys.argv[2]
    fp = Path(filepath)
    if not fp.exists():
        print(f"ERROR: File not found: {fp}")
        sys.exit(1)

    if mode == "create":
        cmd_create(filepath)
    elif mode == "pull":
        cmd_pull(filepath)
    elif mode == "update":
        cmd_update(filepath)
    elif mode == "verify":
        cmd_verify(filepath)
    elif mode == "enhance":
        cmd_enhance(filepath)
    elif mode == "detect":
        cmd_detect(filepath)
    elif mode == "cleanup":
        cmd_cleanup(filepath)
    elif mode == "auto":
        cmd_auto(filepath)
    else:
        print(f"ERROR: Unknown mode '{mode}'. Use create/pull/update/verify/enhance/detect/cleanup/auto.")
        sys.exit(1)

if __name__ == "__main__":
    main()
