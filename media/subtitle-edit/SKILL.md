---
name: subtitle-edit
version: 1.0.0
description: Subtitle Edit CLI — batch subtitle format conversion, time offset, frame rate, encoding, and batch replace. Supports 300+ subtitle formats via /convert or the standalone seconv CLI.
---

# Subtitle Edit — Batch Subtitle Conversion

Subtitle Edit is a free and open-source subtitle editor supporting 300+ formats. This skill covers its command-line interface for batch format conversion and processing.

## Installation

```bash
# npx skills (cross-agent)
npx skills add baoyu0/subtitle-edit-skill -g -y

# Or clone directly
git clone https://github.com/baoyu0/subtitle-edit-skill.git ~/.agents/skills/subtitle-edit
```

## CLI Syntax

```cmd
SubtitleEdit.exe /convert <pattern> <format-name> [parameters...]
```

> **Note:** `/list` may open the GUI instead of printing to console on some versions. Check the format dropdown in the GUI for exact format names.

### Parameters

| Parameter | Description |
|---|---|
| `/convert "<pattern>" "<format>"` | Batch convert, pattern supports wildcards (e.g. `*.srt`) |
| `/list` | List all supported subtitle format names (may open GUI) |
| `/offset:hh:mm:ss.msec` | Time offset (positive = forward, negative = backward) |
| `/fps:<float>` | Force frame rate (for image-based subtitle timing) |
| `/encoding:<name>` | Output encoding (e.g. `utf-8`, `shift-jis`) |
| `/inputfolder:"<path>"` | Input directory |
| `/outputfolder:"<path>"` | Output directory (default: overwrite source) |
| `/multiplereplace` | Batch text replacement (requires pre-configured list in GUI) |
| `/batchconvert` | Open batch convert GUI |

### Supported format names (partial)

`SubRip` (srt), `AdvancedSubStationAlpha` (ass), `WebVTT` (vtt), `SubStationAlpha` (ssa), `MicroDVD` (sub), `PlainText` (txt), `YouTubeCaptions` (sbv), `Json` — 300+ total.

## Examples

```cmd
# srt → ass
SubtitleEdit.exe /convert "*.srt" AdvancedSubStationAlpha

# ass → srt (⚠️ loses styling: fonts, colors, position, effects)
SubtitleEdit.exe /convert "*.ass" SubRip

# srt → vtt (WebVTT)
SubtitleEdit.exe /convert "*.srt" WebVTT

# Time offset (shift all subtitles back 2 seconds)
SubtitleEdit.exe /convert "*.srt" SubRip /offset:-00:00:02.000

# Force frame rate
SubtitleEdit.exe /convert "*.sub" SubRip /fps:23.976

# Specify output encoding
SubtitleEdit.exe /convert "*.srt" SubRip /encoding:utf-8 /outputfolder:"D:\output\"
```

## Workflow: MKV → Subtitle Conversion

```cmd
# 1. List subtitle tracks in MKV
mkvmerge -i "input.mkv"

# 2. Extract specific track (e.g. track ID 2)
mkvextract tracks "input.mkv" 2:"extracted.sup"

# 3. Convert with SE (text formats directly; image formats need GUI OCR)
SubtitleEdit.exe /convert "extracted.sup" SubRip /outputfolder:"."
```

## Standalone CLI (cross-platform, headless)

The [subtitleedit-cli](https://github.com/SubtitleEdit/subtitleedit-cli) repo provides a lightweight .NET 8 console app without GUI dependencies.

```bash
# Build
git clone https://github.com/SubtitleEdit/subtitleedit-cli.git
cd subtitleedit-cli
dotnet build seconv.csproj

# Run
./src/se-cli/bin/Debug/net8.0/seconv *.sub SubRip

# Docker
docker build -t seconv:1.0 -f docker/Dockerfile .
docker run --rm -it -v $(pwd)/subtitles:/subtitles seconv:1.0 sample.srt pac
```

## Configuration

```
%APPDATA%\Subtitle Edit\Settings.xml          — Global settings
Dictionaries\<lang>_OCRFixReplaceList.xml      — OCR fix dictionaries
```

## Troubleshooting

| Problem | Cause & Solution |
|---|---|
| `/convert` hangs / times out | SE shows a confirmation dialog without visible window. Ensure `outputfolder` is set and writable |
| Format name "not found" | Format names are case-sensitive. Check the exact name in the GUI format dropdown |
| Output file garbled | Source encoding is not UTF-8. Add `/encoding:utf-8` or `/encoding:shift-jis` |
| ass → srt loses all styling | ASS font/color/position/animation can't map to plain-text SRT |
| `/list` produces no output | Some versions open GUI instead. Check format names in GUI dropdown |

## Limitations ⚠️

| Feature | CLI Support |
|---|---|
| Text format conversion | ✅ |
| Time offset / frame rate | ✅ |
| Encoding | ✅ |
| Batch text replace | ✅ |
| OCR (VobSub/PGS → text) | ❌ GUI required |
| AI translation | ❌ GUI only |
| Complex editing | ❌ |
| REST API | ❌ |
