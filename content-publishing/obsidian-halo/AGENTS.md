# AGENTS.md — Obsidian → Halo 发布工作流

当你被要求发布文章到 Halo 博客时，执行以下流程。

## 前置

- 配置文件 `~/.hermes/halo-config.json`（PAT + 博客地址）
- Python 脚本 `scripts/halo-publish.py`：detect / cleanup / enhance
- `halo` CLI（`@halo-dev/cli`）：import-markdown / export-markdown / update

## 流程

0. **detect + cleanup**
   ```
   python scripts/halo-publish.py detect "<file>"
   python scripts/halo-publish.py cleanup "<file>"
   ```
   英文先翻译，中文跳过。

1. **完善 frontmatter**
   手动设 slug（纯英文短横线）、categories、tags。

2. **创建文章**
   ```
   halo post import-markdown --file "<file>" --force
   ```
   记录输出 UUID。

3. **拉回 cover/frontmatter**
   ```
   halo post export-markdown <UUID> --output "<file>"
   ```

4. **AI 增强**
   ```
   python scripts/halo-publish.py enhance "<file>"
   ```
   执行 Heading 层级 Checklist，补充 tags/categories，按排版规则优化。

5. **更新发布**
   ```
   halo post update <UUID> --title "..." --content "..." --publish true
   ```

6. **同步 + 验证**
   ```
   halo post export-markdown <UUID> --output "<file>"
   halo post get <UUID> --json
   ```

## Heading 规则

- 至少 2 级标题交替（`##` → `###`）
- 上限 H4，不要 H5+
- 标题用阿拉伯数字编号（`## 1. xxx`、`### 1.1 xxx`）

## 排版

综合运用加粗、行内代码、引用、分隔线、结论句独立成行来美化正文，不过度。
