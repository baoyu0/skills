# Claude Code: Obsidian → Halo 发布工作流

当你收到「处理 xxx.md」或「帮我把这篇文章发布到 halo」的指令时，执行以下流程。

## 工作流

0. **检测语言 + 清理**
   `python scripts/halo-publish.py detect "<文件路径>"`
   退出码 0 → 中文，继续。退出码 1 → 英文，先翻译再继续。
   `python scripts/halo-publish.py cleanup "<文件路径>"` 清理 raw HTML 标签。

1. **完善 frontmatter**
   手动设置 title、slug（纯英文短横线格式）、categories、tags。

2. **创建文章**
   `halo post import-markdown --file "<文件路径>" --force`
   记录输出中的 UUID。

3. **拉回 frontmatter**
   `halo post export-markdown <UUID> --output "<文件路径>"`

4. **AI 增强**
   `python scripts/halo-publish.py enhance "<文件路径>"`
   执行 Heading 层级 Checklist，补充分类/标签，按排版规则优化正文。

5. **更新发布**
   `halo post update <UUID> --title "..." --slug "..." --content "..." --categories "..." --tags "..." --publish true`

6. **同步回本地 + 验证**
   `halo post export-markdown <UUID> --output "<文件路径>"`
   `halo post get <UUID> --json`

## 前置

配置文件 `~/.hermes/halo-config.json` 存放 PAT 和博客地址。
Python 脚本 `scripts/halo-publish.py` 提供 detect/cleanup/enhance。
`halo` CLI（`@halo-dev/cli` v1.3.0）用于创建/更新/导出文章。

## 排版规则

- 段落之间留一个空行
- 图片前后留空行，alt 有语义
- 引用块前后留空行
- 综合运用加粗、行内代码、引用、分隔线、结论句独立成行美化正文
