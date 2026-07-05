# X Article Video Handling

X (Twitter) Articles embed videos differently from regular tweets. This doc covers the approaches, limitations, and recommended workflow.

## Current Behavior in cleanup

The `cleanup` mode replaces `<video>` tags with blob: URLs:
- Extracts the `poster` image URL
- Creates a clickable Markdown image linking to the original source: `[![视频截图](poster_url)](source_url)`

This is the **stable fallback** — always works, no auth needed.

## obu-based Poster Extraction (Recommended Enhancement)

The skill includes `scripts/obu_extract.py` (Python, replaces old shell script) which uses obu CDP:

```bash
python ~/.hermes/scripts/obu_extract.py "https://x.com/.../article/..." "/tmp/result.json"
```

### ✅ Reliable: Poster URL extraction
- Uses `Runtime.evaluate` on the logged-in Chrome tab
- Returns all `<video>` poster URLs as JSON
- Works every time

### ❌ Unreliable: CDN URL extraction
The real video file URL at `video.twimg.com` is NOT extractable via automation.

## Root Cause: MSE + Autoplay

X Articles use MSE (MediaSource Extensions):
- `<source src="blob:https://x.com/...">` is a transient MediaSource reference
- Real file is at `video.twimg.com/amplify_video/<id>/vid/...`
- CDN URL ONLY appears as a network request when the video actually plays
- Browser autoplay policies block programmatic `play()` even with `muted=true`
- Video player overlay requires real user clicks
- Even triggered play doesn't register in `performance.getEntries()` — segments are loaded via fetch + streaming (HLS/DASH), not standard resource loading
- The browser's Performance API doesn't capture these streaming segment requests

### Why Tools Don't Work

| Tool | Regular Tweet | X Article |
|------|:---:|:---:|
| yt-dlp | ✅ media attachments | ❌ compose-embedded video |
| gallery-dl | ✅ media tab | ❌ not a media attachment |
| vxtwitter.com | ✅ media_extended | ❌ no media in articles |
| Twitter API v1.1/v2 | ✅ media entities | ❌ article content not exposed |
| Apify Actors | ✅ tweet media | ❌ same API limitation |

## obu CDP Technique Summary

### Key Lessons Learned

1. **obu path**: `/d/npm-global/obu` (shell script, must run from git-bash)
2. **Tab lifecycle**: obu tabs CANNOT be reused across separate bash processes — each `obu cdp` call that fails with "Tab X is not part of browser session obu-cli" means the session was lost. Must open tab and run ALL CDP commands in the same script.
3. **CDP param construction**: Use `python3 -c "import json; print(json.dumps({'expression': JS_CODE, 'returnByValue': True}))"` to avoid bash quoting hell
4. **Output parsing**: obu CDP output may contain streaming events (CDP event notifications) mixed with the actual response. Use temp files to save output, then parse with Python to filter events.
   - Response has `"id": "cli-1"` — this is the reliable signal to distinguish from CDP events
   - CDP events have `"method": "onCDPEvent"` but no top-level `"id"`
5. **Avoid `grep -oP`**: git-bash's grep 3.0 has unreliable Perl mode. Use Python for JSON extraction.
6. **Avoid `tail -1` in pipes**: It can produce empty results due to buffering. Use temp files instead.

### CDP Commands Reference

```bash
# Evaluate JS (most common) — use cdp_eval helper pattern
JS='document.querySelectorAll("video").length'
PARAMS=$(python3 -c "import json; print(json.dumps({'expression': '$JS', 'returnByValue': True}))")
obu cdp --tab-id "$TAB" --method Runtime.evaluate --params "$PARAMS" | python3 -c '
import sys, json
for line in sys.stdin:
    if "\"id\"" in line:
        d = json.loads(line)
        v = d.get("result",{}).get("result",{}).get("value")
        if v is not None: print(v)
'

# OR save to temp file first (more reliable, avoids pipe issues)
obu cdp --tab-id "$TAB" --method Runtime.evaluate --params "$PARAMS" > /tmp/obu_cdp.json
python3 -c 'import json
with open("/tmp/obu_cdp.json") as f:
    for line in f:
        if "\"id\"" in line:
            d=json.loads(line); v=d.get("result",{}).get("result",{}).get("value")
            if v is not None: print(v)
'

# Mouse click
P=$(python3 "import json; print(json.dumps({'type':'mousePressed','x':$X,'y':$Y,'button':'left','clickCount':1}))")
obu cdp --tab-id "$TAB" --method Input.dispatchMouseEvent --params "$P"

# Close tab
obu cdp --tab-id "$TAB" --method Page.close
```

### Why CDP Click Doesn't Trigger X Video

X's video player has a React-based overlay (play button, scrubber, etc.) on top of the `<video>` element. Clicking the `<video>` coordinates hits the overlay elements, which do not respond to programmatic `Input.dispatchMouseEvent` the same way as real user clicks. The overlay likely checks `event.isTrusted` or uses React's synthetic event system which CDP events may not trigger correctly.

## X Article Video DOM Structure (2026-06 Findings)

X's Article video player DOM structure (from bottom up):

```
<video>  ← aria-label="嵌入式视频"
  <source src="blob:...">  ← MSE blob reference
<div> (empty)
<div> (empty)
<div> (2 children, hasButton=true)  ← contains play button
<div>  ← React player wrapper
<div>  ← outer container
```

The play button element is:
```
BUTTON aria-label="播放 视频"
  Position: top-left of video + offset (React overlay)
  Size: 60×60
```
Found 4 levels up from `<video>`. Use:
```js
document.querySelector("[aria-label=\"播放 视频\"]")
```

### Video State After Click

| Property | Value | Meaning |
|----------|-------|---------|
| `readyState` | 0 | HAVE_NOTHING — no data loaded |
| `networkState` | 2 | NETWORK_LOADING — actively fetching |
| `paused` | true | Not playing yet |
| `currentSrc` | `blob:https://x.com/...` | MSE source buffer |

Clicking the play button triggers `networkState=2` (browser tries to load) but `readyState` stays 0 — the MSE pipeline hasn't delivered data. The actual `video.twimg.com` fetch requests are NOT captured by `performance.getEntries()` or `fetch()` override.

## Tab Cleanup (Critical!)

Always clean up obu tabs when done, otherwise Chrome fills up with orphan tabs.

**`finalize-tabs` (recommended):** Closes ALL tabs in the obu-cli session not in the keep list. Run it in `finally` blocks unconditionally (not just when tab_id was obtained):

```bash
obu finalize-tabs --keep "[]"
```

In Python:
```python
run([OBU, "finalize-tabs", "--keep", "[]"])  # always, even on error before tab_id was set
```

**Why unconditional:** If the script crashes between `open-tab` and `tab_id` assignment, the tab is orphaned. Always run `finalize-tabs`.

**Earlier script (bash) vs current (Python):** The old `obu-extract-x-video.sh` used `Page.close` which closes only one tab; the new `obu_extract.py` uses `finalize-tabs` which is more thorough.

## CDP Technique Details (Debugging History)

### Output Parsing
obu CDP output mixes event notifications with responses. The reliable filter:
- **Response**: has top-level `"id"` field (e.g., `"id": "cli-1"`)
- **Events**: no top-level `"id"`, have `"method": "onCDPEvent"`
- **Recommended**: save raw output to temp file, then parse with Python filtering for `"id"` lines

### Tab Lifecycle (Critical!)
obu tabs are bound to the process session. A tab opened in one `obu open-tab` call **cannot** be reused in a separate process — you'll get `"Tab X is not part of browser session obu-cli"`. All CDP commands for one task must run in the same script/shell invocation.

### Python subprocess Note
`obu` is a shell script (`#!/bin/sh`), NOT a Win32 binary. Python's `subprocess.run()` cannot execute it directly via `CreateProcess`. On Windows:
```python
r = subprocess.run(["/usr/bin/bash", "-c", f"obu tabs"], capture_output=True, ...)
```
However, `shutil.which("obu")` returns `D:\npm-global\obu.CMD` which IS a valid Windows executable (CMD wrapper). So availability checks work; direct subprocess doesn't.

### open-tab Response Format
The `open-tab` response does NOT have an `"id"` field like CDP responses:
```json
{"navigate": {...}, "tab": {"active": true, "id": 12345, "title": "", "url": ""}}
```
It's also multi-line JSON, so line-by-line parsing will fail. Use brace-matching or save to a file and `json.load()`.

### What We Tried (and Why It Failed)

| Approach | Result | Root Cause |
|----------|--------|------------|
| `Runtime.evaluate` with `performance.getEntries()` | ❌ empty | MSE segment fetches don't register in Resource Timing API |
| `Network.enable` CDP domain | ❌ events mixed in output | CDP events stream asynchronously, hard to capture via CLI |
| `Fetch.enable` request interception | ❌ no requests caught | Page uses Service Worker for video |
| `fetch()` override interception | ❌ no requests caught | X player uses native fetch not affected by monkey-patch |
| `Input.dispatchMouseEvent` on play button | ⚠️ networkState→2 but no data | React synthetic events + autoplay restrictions block real loading |
| `video.play()` with `muted=true` | ❌ blocked | Browser autoplay policy requires real user gesture |

## Manual CDN URL Extraction (only when absolutely needed)

When a specific video is worth the effort:

1. Open the Article in obu (real Chrome with X login)
2. Open DevTools → Network tab
3. Filter by `video.twimg`
4. **Play the video manually** by clicking the play button with your mouse
5. Look for the `amplify_video/.../vid/...` request (typically `.m3u8` manifest or `.m4s` segment)
6. Copy the URL (use the highest resolution available)

Then in the markdown, replace the poster link with:
```html
<video controls poster="poster_url">
  <source src="cdn_url.mp4" type="video/mp4">
</video>
```

## Recommended Workflow

1. Run `cleanup` → handles blob: video automatically (always works)
2. `cleanup` also auto-runs `obu_extract.py` if obu is available and source is x.com → best-effort CDN extraction
3. If CDN URLs are critical for a specific article: manual extraction via DevTools
