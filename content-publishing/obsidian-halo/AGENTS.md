# AGENTS.md — Obsidian → Halo 发布工作流

当你被要求发布文章到 Halo 博客时，执行以下 5 阶段流程。

## 前置

- 配置文件 `~/.hermes/halo-config.json`（PAT + 博客地址）
- `halo` CLI（`@halo-dev/cli`）：`import-markdown` / `export-markdown` / `get` / `update`
- Python 脚本 `scripts/halo-publish.py`：`detect` / `cleanup`
- `scripts/auto-number.py`：自动编号 H2/H3 标题
- ⚠️ 用绝对路径调用 Python 脚本（Windows git-bash 下 `$HOME` 可能解析异常）

---

## 五阶段流程

### Phase 0: 语言检测 + X 剪藏预处理

```bash
python "scripts/halo-publish.py" detect "<文件路径>"
# exit 0 → 中文 ✅
# exit 1 → 英文 ⚠️ → 先翻译 body
```

如果是 X/Twitter 剪藏，优先用 `x-clip-purify` 预处理：

```bash
python "scripts/x-clip-purify.py" detect "<文件路径>"
python "scripts/x-clip-purify.py" clean "<文件路径>"
```

### Phase 1: 上传原始文件 + 拉回 frontmatter

```bash
# 创建文章（只传文件，不做修改）
halo post import-markdown --file "<文件路径>" --force
# 记录输出中的 UUID（metadata.name: xxxx）

# 拉回完整 frontmatter（含 cover/slug/halo.name）
halo post export-markdown <UUID> --output "<文件路径>"
```

### Phase 2: 内容处理

```bash
# 2a. 清理 raw HTML
python "scripts/halo-publish.py" cleanup "<文件路径>"

# 2b. 自动编号标题
python "scripts/auto-number.py" "<文件路径>"

# 2c. AI 手动修复：
#   - 检查 Heading 层级（H1→H2→H3），每章至少 2 个 H3
#   - 删除重复编号、「第 X 步」冗余、中文数字前缀
#   - 补充 categories / tags 到 frontmatter（不可为空）
#   - 按排版规则美化正文
#   - 用 read_file 验证 frontmatter 完整性
```

### Phase 3: 更新发布

⚠️ **永远不要用 `halo post update --content`** — 它会吞掉一级 `#`（`##`→`#`），导致 TOC 错乱。

正确做法：
```bash
# 用 import-markdown 更新内容（保留 heading 级别不变）
halo post import-markdown --file "<文件路径>" --force

# 单独发布
halo post update <UUID> --publish true
```

### Phase 4: 验证

```bash
# 验证 publish 状态
halo post get <UUID> --json

# 同步回本地
halo post export-markdown <UUID> --output "<文件路径>"

# 验证线上 heading
curl -s "https://jia.baoyu2023.top/archives/<slug>?nocache=1" | grep -oP '<h[1-3][^>]*>[^<]+</h[1-3]>'
```

---

## Heading 规则

- **H1→H2→H3 三级结构**。body 首行放 `# 文章标题` 作为 H1
- 每章至少拆 **2 个 H3** 子节。禁止扁平目录（纯 H2 无 H3）
- 标题用阿拉伯数字编号（`## 1. xxx`、`### 1.1 xxx`）
- H3 以下用列表，不能再切 H4+
- 禁止用 `--content` 提交正文（会破坏 heading 层级）

## 排版规则

- 段落之间留一个空行
- 图片前后留空行，alt 有语义
- 引用块前后留空行
- 代码块有语言标注
- 综合运用加粗、行内代码、引用、分隔线、结论句独立成行美化正文
