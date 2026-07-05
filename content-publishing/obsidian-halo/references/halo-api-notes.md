# Halo API & Script Reference

## API Endpoints Used

| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/apis/content.halo.run/v1alpha1/categories` | GET/POST | List/create categories | Bearer PAT (content scope) |
| `/apis/content.halo.run/v1alpha1/tags` | GET/POST | List/create tags | Bearer PAT (content scope) |
| `/apis/uc.api.content.halo.run/v1alpha1/posts` | POST | Create post | Bearer PAT (uc scope) |
| `/apis/uc.api.content.halo.run/v1alpha1/posts/{name}` | GET/PUT | Get/update post metadata | Bearer PAT (uc scope) |
| `/apis/uc.api.content.halo.run/v1alpha1/posts/{name}/draft` | PUT | Update draft content | Bearer PAT (uc scope) |
| `/apis/uc.api.content.halo.run/v1alpha1/posts/{name}/draft?patched=true` | GET | Get draft with rendered content | Bearer PAT (uc scope) |
| `/apis/uc.api.content.halo.run/v1alpha1/posts/{name}/publish` | PUT | Publish/re-publish | Bearer PAT (uc scope) |
| `/apis/uc.api.content.halo.run/v1alpha1/posts/{name}/unpublish` | PUT | Unpublish | Bearer PAT (uc scope) |

**Important:** The `uc.api.content.halo.run` endpoints require a PAT with `Post Manage` permission, while `content.halo.run` works with basic content-read scope.

## PAT (Personal Access Token)

- Format: `pat_` + JWT
- Create at: `https://<blog>/console` → Personal Center → Personal Access Token
- Required permission: **Post Manage** (文章管理)
- Store in: `~/.hermes/halo-config.json` as `{"pat": "...", "url": "https://..."}`

## Key Pitfalls

### 1. Content-json needs rendered HTML, not raw markdown
The `content.halo.run/content-json` annotation must contain `{"raw": "...", "content": "<html>", "rawType": "markdown"}`.
The `content` field MUST be HTML (rendered via markdown-it-py), NOT raw markdown.
If raw markdown is passed as content, Halo displays it as raw text on the page.

### 2. Draft update requires re-publish
After updating the draft content via PUT to `/draft`, the changes are NOT reflected on the published page.
You MUST also PUT to `/publish` to promote the draft to the published version.

### 3. Cloudflare caching
The blog is behind Cloudflare. After publishing/updating:
- The page may serve a cached version for several minutes
- Force refresh with `?nocache=1` query parameter to see the latest version
- The `curl -H "Cache-Control: no-cache"` approach works for API verification

### 4. Category/tag resolution
Categories and tags use Halo's internal UUID names, not display names.
The script resolves display names → UUIDs via GET + auto-create via POST.

### 5. Update flow order
When calling `update`:
1. PUT metadata first (title, slug, categories, tags, cover)
2. PUT draft content (annotations with content-json)
3. PUT publish (to promote draft)

### 6. SinglePage API limitations
The PAT with `Post Manage` scope does **NOT** grant access to single page endpoints:
- `uc.api.content.halo.run/v1alpha1/singlepages/{name}` → `403 insufficient_scope`
- To update single pages, create a PAT with `SinglePage Manage` scope in Halo console

### 7. Snapshot API fragility (do not use directly)
Halo stores content as snapshots. The `content.halo.run/v1alpha1/snapshots` API can create new snapshots (read-write with basic PAT), but:
- `contentPatch` AND `rawPatch` must BOTH reference the same content — a mismatch causes `SinglePageReconciler.getExcerpt` to throw 500
- The reconciler auto-reverts `headSnapshot`/`releaseSnapshot` changes that break consistency
- Snapshot `checksum/content` must be updated when content changes
- **Best practice: never touch snapshots directly.** Use `uc.api.content.halo.run` endpoints or replace server files instead.
- **DELETE requires higher privilege:** `DELETE /apis/content.halo.run/v1alpha1/snapshots/{name}` returns `401` with a basic PAT. Orphan snapshots (v0, unlinked) are harmless — Halo cleans them during maintenance.

### 8. plugin-photos: attachments ≠ gallery
The `plugin-photos` plugin has its own data store and API endpoints (`core.halo.run`, `console.api.photo.halo.run`, `api.photo.halo.run`). Images uploaded through the regular Halo attachment system (post editor, attachment manager) do NOT appear in the Photos gallery. To add images:
- Use the **Halo Console → Photos** menu (plugin's own upload UI)
- Or call `POST /apis/console.api.photo.halo.run/v1alpha1/photos/upload` (requires PAT with plugin scope)
- Gallery API: `GET /apis/core.halo.run/v1alpha1/photos` lists photos, `GET /apis/core.halo.run/v1alpha1/photogroups` lists albums
