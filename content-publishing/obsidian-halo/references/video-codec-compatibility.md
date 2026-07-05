# Video Codec Compatibility on Web Pages

## The Problem: HEVC/H.265 in Firefox-based Browsers

When a blog page embeds an MP4 video, **different browsers support different codecs**:

| Codec | Chrome | Firefox/Zen | Safari |
|-------|--------|------------|--------|
| H.264 (AVC) | ✅ | ✅ | ✅ |
| H.265 (HEVC) | ✅ (Windows GPU) | ❌ | ✅ |
| VP9 | ✅ | ✅ | ⚠️ partial |
| AV1 | ✅ | ✅ | ✅ (M3+) |

If a video plays in Chrome but shows `NS_ERROR_DOM_MEDIA_METADATA_ERR (0x806e0006)` in Firefox/Zen, the video is HEVC-encoded.

## Diagnosis

```bash
# Check codec from server
ffprobe -v quiet -print_format json -show_streams \
  -select_streams v:0 <video.mp4> | python3 -c \
  "import json,sys; d=json.load(sys.stdin); print(d['streams'][0]['codec_name'])"

# Also check Content-Type + Range request support
curl -s -D - -o /dev/null -H "Range: bytes=0-100" <video_url> | head -20
```

## Fix: Re-encode to H.264

```bash
ffmpeg -i input.mp4 -c:v libx264 -preset slow -crf 23 \
  -c:a aac -movflags +faststart -y output.mp4
```

Key flags:
- `-c:v libx264` — H.264 encoder
- `-preset slow` — better compression/smaller file (vs fast)
- `-crf 23` — good quality (lower=better, 18-28 range)
- `-movflags +faststart` — moves moov atom to file start for web playback

## Deployment: Keep URLs Stable

**Don't change the page content.** Simply replace the server file:

```bash
# Backup original
cp old.mp4 old-hevc-backup.mp4

# Replace with H.264 version
cp new-h264.mp4 old.mp4
```

The page HTML keeps referencing the same URL, but the underlying file is now H.264.

## What NOT to Do

- **Don't modify Halo snapshots directly** — the contentPatch/rawPatch/checksum chain is fragile. A mismatch causes `SinglePageReconciler.getExcerpt` to throw, resulting in HTTP 500.
- **Don't use content.halo.run API to update single pages** — PAT scope for "Post Manage" does NOT cover single pages (`uc.api.content.halo.run/singlepages` returns 403).
- **Don't create orphan snapshots** — the reconciler may auto-revert headSnapshot changes, and orphan snapshots (version 0, no parent chain) clutter the database.
