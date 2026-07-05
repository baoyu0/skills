# halo-publish.py — Reference

Script at `~/.hermes/scripts/halo-publish.py`. Eight modes:

| Mode | What it does |
|------|-------------|
| `detect <file>` | Detect article language: CJK ratio ≥20% → Chinese (exit 0), else English (exit 1). Strips code blocks/URLs before counting. |
| `create <file>` | Strip frontmatter → upload raw body → set title only (slug let Halo auto-generate) → publish → save UUID. Title priority: frontmatter > first heading > filename stem. Does NOT set slug. |
| `pull <file>` | Poll until cover ready (3s × 10 = 30s timeout) → pull post from Halo → write Halo's frontmatter (cover, title, Halo-generated slug) + raw content back to file |
| `cleanup <file>` | Scan body for `<video>`/`<audio>` with `blob:` URLs → replace with poster image linked to source URL. Strip orphaned timestamp lines. Detect raw `<iframe>`/`<embed>`/`<object>` and warn. Idempotent. |
| `enhance <file>` | Auto-number H2 headings + auto-promote `X.Y` paragraph patterns to `### X.Y` H3 headings + detect flat structure (3+ H2 with no H3) → report stats → alert if categories/tags missing |
| `update <file>` | Read enhanced file → update metadata (title, slug, categories, tags, cover) + draft content → re-publish → auto-verify (HTTP 200 + title match + HTML quality check for video/iframe/blob) |
| `verify <file>` | Standalone: HTTP GET published URL (?nocache=1) → check 200 + title in body (force UTF-8 decode) + HTML quality check → pass/fail |
| `auto <file>` | **Full pipeline:** detect → create → pull → cleanup → enhance → update → verify. Saves processing report to `D:/1-obsidian/halo/_report-*.md`. Stops on English articles with instructions to translate first. |

## Retry Logic

- All API calls (`_get`, `_post`, `_put`) use `requests.Session` with `urllib3.Retry`
- Up to 3 retries with 1s backoff factor for 502/503/504 responses
- Configured in `HaloAPI.__init__`

## Markdown Rendering

Uses `markdown-it-py` with `gfm-like` preset (supports tables, strikethrough, autolinks).

```python
md_renderer = MarkdownIt("gfm-like", {"breaks": True, "linkify": False})
```

`commonmark` preset does NOT support tables — always use `gfm-like`.

## Halo API Flow

1. **Create**: `POST /apis/uc.api.content.halo.run/v1alpha1/posts`
   - Body includes `content.halo.run/content-json` annotation with `{raw, content (HTML), rawType}`
   - Content field must be HTML-rendered markdown, not raw markdown
   - Slug is set to `"untitled"` initially; Halo auto-generates proper slug from title during publish

2. **Update**: `PUT /apis/uc.api.content.halo.run/v1alpha1/posts/{name}` (metadata) + `PUT /apis/uc.api.content.halo.run/v1alpha1/posts/{name}/draft` (content)
   - Must re-publish after draft update: `PUT /apis/uc.api.content.halo.run/v1alpha1/posts/{name}/publish`
   - Without re-publish, draft changes are not reflected on the published page

3. **Pull**: `GET /apis/uc.api.content.halo.run/v1alpha1/posts/{name}` (metadata) + `GET .../draft?patched=true` (content)
   - Reads from `content.halo.run/patched-raw` annotation

## Slug Strategy

- `create` does NOT set slug — Halo auto-generates from title
- `pull` reads back the Halo-generated slug
- `update` preserves the existing slug (no manual ASCII-ization needed)

## Known Pitfalls

- **Cloudflare caching**: After update, page may serve old content. Add `?nocache=1` to URL or wait 10-15s.
- **Cover auto-generation**: `cmd_pull` now polls (3s × 10 = 30s timeout). No manual sleep needed.
- **Draft vs published**: Updating draft alone is not enough — must call publish to apply draft to live page.
- **Title detection**: Script prefers frontmatter `title` first; falls back to first ATX heading only if frontmatter has no title.
- **Content field**: Must be rendered HTML, not raw markdown. Script uses `markdown-it-py` with `gfm-like` preset.
- **PAT expiry**: Halo Personal Access Tokens expire. If API returns 401 at `/apis/uc.api.content.halo.run/...`, regenerate PAT in Halo admin console and update `~/.hermes/halo-config.json`.
- **UTF-8 encoding**: Halo may not signal charset in `Content-Type`. `cmd_verify` forces `utf-8` decode on the HTTP response to avoid garbled Chinese characters.
- **API retry**: Built-in 3x retry on 502/503/504 via `urllib3.Retry`. Transient failures auto-recover.
