# 猫抓 (Cat-Catch) X Article Video Workflow

When user has the 猫抓 Chrome extension installed, this is the only reliable way to get actual video files from X (Twitter) Articles.

## Prerequisites
- Chrome extension **猫抓** (Cat-Catch) v2.6.9+, ID: `jfedfbgedapdagkghmgibemcoggfppbb`
- Installed at: `C:\Users\zhaid\AppData\Local\Google\Chrome\User Data\Default\Extensions\jfedfbgedapdagkghmgibemcoggfppbb\`
- Real Chrome with X login (via obu)

## Workflow

### Step 1: User Downloads Videos
1. User opens the X Article page in Chrome (obu can open it)
2. User clicks **play** on each video with their mouse (CDP automation cannot trigger this — X Article's player requires real user gesture)
3. 猫抓 automatically detects `video.twimg.com/amplify_video/...` CDN URLs via its `webRequest` interception (background service worker at `js/background.js`)
4. User opens cat-catch popup → downloads each video → saved to `~/Downloads/` as `X (N).mp4` + `X (N).mp3`

### Step 2: Agent Handles Files
1. Find downloaded files: `ls -lt ~/Downloads/ | grep -i 'X ('`
2. Deduplicate by file size (cat-catch often creates multiple copies)
3. Copy unique files to temp dir with meaningful names:
   ```bash
   cp ~/Downloads/"X (18).mp4" ~/AppData/Local/hermes/halo-videos/fpv-video-1.mp4
   ```
4. Check video codec (must be h264 for all browsers):
   ```bash
   ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of csv=p=0 file.mp4
   ```
5. Upload to Halo attachment:
   ```bash
   halo attachment upload --file file.mp4
   # → get UUID from output
   halo attachment get <UUID> --json | python3 -c "import sys,json;d=json.load(sys.stdin);print('https://jia.baoyu2023.top'+d['status']['permalink'])"
   ```

### Step 3: Replace Article Content
1. Replace poster links `[![视频截图](poster)](url)` with Halo video URLs:
   ```html
   <video controls preload="metadata" width="100%" style="max-width:100%;border-radius:8px;">
     <source src="https://jia.baoyu2023.top/upload/fpv-video-N.mp4" type="video/mp4">
   </video>
   ```
2. Remove orphan `![](...)` lines that are leftover poster images
3. Remove `halo.*` block from frontmatter
4. Import: `halo post import-markdown --file <path> --force`
5. Set cover in frontmatter, re-import, publish

## Why CDP Automation Can't Replace This

X Articles use Service Worker + MSE (MediaSource Extensions):
- Content scripts / page-context `fetch()` overrides can't intercept SW-initiated requests
- CDP `Network.enable` doesn't capture SW-mediated media fetches
- `performance.getEntries()` doesn't register MSE segment requests
- The play button requires a genuine `event.isTrusted=true` click that CDP `Input.dispatchMouseEvent` cannot produce

猫抓 works because the Chrome extension `webRequest` API operates at the browser level, before the Service Worker intercepts the request.

## Order Matching

cat-catch numbers videos by **detection order**, not article order. After downloading, use `references/video-order-matching.md` to re-sync them via perceptual hash matching.

## Cat-Catch Technical Notes

**Content script** (`js/content-script.js`):
- Runs `document_start` on all pages
- Tracks `<video>`/`<audio>` elements in `_videoObj` / `_videoSrc`
- Accepts `chrome.runtime.onMessage` with messages: `getVideoState`, `getKey`, `speed`, `play`, `pause`, `ffmpeg`, etc.

**Background** (`js/background.js`):
- Intercepts `webRequest.onSendHeaders` + `onResponseStarted` for `<all_urls>`
- Calls `findMedia()` on each request to detect video/audio by URL extension, Content-Type, and request type `media`
- Stores detected media in `cacheData[tabId]` array
- Persists to `chrome.storage.session` with key `MediaData` via alarm "save"

**Extension pages** (cannot be navigated via obu/Hermes browser):
- `popup.html?tabId=N&type=current` — shows detected media list
- Chrome extension pages are sandboxed by the browser
