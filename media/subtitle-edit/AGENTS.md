# AGENTS.md — Subtitle Edit

Subtitle Edit CLI — batch subtitle format conversion, time offset, frame rate, encoding, and batch replace. Supports 300+ subtitle formats.

## 前置

- `SubtitleEdit.exe` 需在 PATH 或指定路径
- 跨平台方案：`seconv`（.NET 8 console app，来自 [subtitleedit-cli](https://github.com/SubtitleEdit/subtitleedit-cli)）

---

## CLI 语法

```cmd
SubtitleEdit.exe /convert "<pattern>" "<format>" [parameters...]
```

### 常用参数

| 参数 | 说明 |
|------|------|
| `/convert "*.srt" SubRip` | 格式转换（pattern 支持通配符） |
| `/offset:hh:mm:ss.msec` | 时间偏移（正=前移，负=后移） |
| `/fps:<float>` | 强制帧率（图片类字幕） |
| `/encoding:utf-8` | 输出编码 |
| `/inputfolder:"<path>"` | 输入目录 |
| `/outputfolder:"<path>"` | 输出目录（不指定则覆盖源） |

### 常用格式名

`SubRip` (srt), `AdvancedSubStationAlpha` (ass), `WebVTT` (vtt), `SubStationAlpha` (ssa), `MicroDVD` (sub), `PlainText` (txt), `YouTubeCaptions` (sbv)

## 示例

```cmd
SubtitleEdit.exe /convert "*.srt" AdvancedSubStationAlpha
SubtitleEdit.exe /convert "*.ass" SubRip                          # ⚠️ 丢失样式
SubtitleEdit.exe /convert "*.srt" SubRip /offset:-00:00:02.000
SubtitleEdit.exe /convert "*.sub" SubRip /fps:23.976
```

## MKV 字幕提取工作流

```cmd
mkvmerge -i "input.mkv"                                          # 列出轨道
mkvextract tracks "input.mkv" 2:"extracted.sup"                  # 提取指定轨道
SubtitleEdit.exe /convert "extracted.sup" SubRip /outputfolder:"."  # 转换
```

## 注意事项

- 格式名大小写敏感 — 查 GUI 下拉菜单的精确名称
- ass→srt 会丢失字体/颜色/位置/动画
- `/list` 可能打开 GUI 而非打印到控制台
- OCR（VobSub/PGS→text）、AI 翻译、复杂编辑需 GUI
