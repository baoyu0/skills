# Subtitle Edit — Agent Skill

[![Agent Skill](https://img.shields.io/badge/Agent%20Skill-Subtitle%20Edit-blue)](https://github.com/baoyu0/subtitle-edit-skill)

AI agent skill for batch subtitle format conversion using [Subtitle Edit](https://www.nikse.dk/subtitleedit) CLI.

Supports Hermes, Claude Code, Codex, OpenCode, and any agent with SKILL.md support.

## Quick Install

```bash
npx skills add baoyu0/subtitle-edit-skill -g -y
```

Then your agent will automatically know how to convert subtitles when you ask.

## What It Does

- **Format conversion**: srt ↔ ass ↔ vtt ↔ ssa ↔ sub ↔ txt ↔ 300+ formats
- **Time offset**: batch shift all subtitles forward/backward
- **Frame rate**: force FPS for image-based subtitle timing
- **Encoding**: specify output encoding (utf-8, shift-jis, etc.)
- **Batch replace**: bulk text replacement across subtitle files
- **MKV workflow**: extract + convert subtitles from Matroska containers

## Prerequisites

- [Subtitle Edit](https://www.nikse.dk/subtitleedit) installed (`SubtitleEdit.exe` on PATH)
- Or [subtitleedit-cli](https://github.com/SubtitleEdit/subtitleedit-cli) for cross-platform headless use

## Links

- [Subtitle Edit](https://www.nikse.dk/subtitleedit) — official website
- [Subtitle Edit CLI](https://github.com/SubtitleEdit/subtitleedit-cli) — standalone .NET 8 CLI tool
- [Subtitle Edit on GitHub](https://github.com/SubtitleEdit/subtitleedit) — main project repo
