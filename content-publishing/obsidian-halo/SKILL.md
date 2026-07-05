---
name: obsidian-halo
description: "上传原文 → 拉回 frontmatter → cleanup → auto-number（编号+剥离自介+叙事分段）→ 排版 → 更新发布。说「处理 xxx.md」即可。"
---

# Obsidian → Halo 文章处理 Skill

> **⚠️ 作用域警告：此 skill 只负责本地 markdown 文件处理与发布。与 Halo 后台「外观 → 代码注入」的 CSS/主题定制完全无关。**
>
> 不要在此 skill 中操作 Halo 主题 CSS、代码注入、字体配置或任何 Halo 后台渲染设置。那些归 `halo-theme-css` skill 管。
>
> **二者边界：**
> - **obsidian-halo**：本地 markdown → 推送到 Halo（内容发布）
> - **halo-theme-css**：Halo 主题渲染样式（代码注入 CSS）
>
> 见参考资料 `references/halo-css-injection.md` 了解更多。

> **⚠️ 必须记住：访问需要登录态的页面时用 `obu`（`/d/npm-global/obu`），不是 `browser_navigate`。**  \
> 包括：X/Twitter、Halo 后台（console）、Reddit 等。系统浏览器工具无登录态；obu 使用你的真实 Chrome 登录态，免输密码。CDP 参数用 `python3 -c "import json; print(json.dumps({...}))"` 构建，避免 bash 引号转义问题。

当用户说「处理这个文件」或「帮我把这篇发布到 halo」并给出文件路径时，你执行以下流程。文件通常在 `D:/1-obsidian` 仓库下，不一定总是在 Clippings/ 目录。

## 核心原则：markdown 先行，Halo 只读不写

Halo 只是一个渲染器，**不是排版工具**。所有内容调整一律改 markdown 文件，然后重新 import-markdown。

1. **永远不要直接修改 Halo**：不调主题设置、不碰后台配置来绕排版问题。Halo 只是用来「看效果」的。
2. **发现问题 → 回 markdown 修 → 重新 import**：无论 heading 层级不对、图片说明不对、还是段落被截断，根因都在 markdown 文件里。
3. **上传原始文件 → 拉回 → 再处理**：文件直接上传到 Halo（原文照搬，不做改动），然后 export-markdown 拉回完整的 frontmatter（含 UUID/cover），再集中做 cleanup/enhance/排版，最后一次 import-markdown 更新即可。不在上传前预处理。
4. **import-markdown 优于 update --content**：前者完整保留所有 markdown 格式（包括 heading 级别），后者会吞掉一级 `#`。

## 六阶段流程

### Phase 0: 语言检测（原文直接上传，不做修改）

**目标：检测文章语言，如果是英文则翻译为中文。此阶段不做文件内容修改。**

> ⚠️ **`<video>`/`<audio>` 标签清理在 Phase 3（拉回 frontmatter 后）执行**，不在 Phase 0 处理。详见 Phase 3。

**语言检测：**

```bash
# ⚠️ $HOME 在 Windows git-bash 中可能解析为畸变路径（C:\c\Users\...）
# 如果报 `can't open file`，改用绝对路径：
python "C:/Users/zhaid/.hermes/scripts/halo-publish.py" detect "<文件绝对路径>"
```

- 退出码 **0** → 中文 ✅，跳到 Phase 1
- 退出码 **1** → 英文 ⚠️，需要先翻译

**自动清理：** `<video>`/`<audio>` 标签的清理已移至 **Phase 3**（拉回 frontmatter 后）。Phase 0 不做文件修改。

**外部图片防盗链处理：** 如果文章引用了外部 CDN 图片（如 sspai.com 等），这些图片在 Halo 上可能无法显示（403/404）。此处理在 Phase 3 拉回后统一进行：

```bash
# ⚠️ 如果 `~`/`$HOME` 报 `can't open file`，用绝对路径：
python "C:/Users/zhaid/.hermes/scripts/halo-migrate-images.py" "<文件绝对路径>"
```

脚本会：扫描外部图片 → 下载到临时目录 → 生成 Halo 上传命令。agent 执行完上传后再次运行 `--apply` 替换 URL。详见 `scripts/halo-migrate-images.py` 的帮助信息。完整上传流程参见 `references/halo-image-migration.md`。

**翻译规则（AI 手动执行）：**
1. 用 `read_file` 读取文件的 **body 部分**（去掉 frontmatter）
2. 翻译 body 为简体中文，**保留以下元素不变**：
   - 代码块（含语言标注）
   - URL 和链接文本
   - 专有名词（GitHub, Kubernetes, API 等）
   - Markdown 格式标记
3. **在正文开头添加翻译声明**（在第一张图片或正文首段前）：
   ```markdown
   > 📌 本文翻译自 [原文标题](原文链接)，作者 [@作者名](作者链接)
   ```
4. **保存原文元数据（仅首次上传用）**：在 frontmatter 中添加 `source`、`original_author`、`original_title`、`original_published` 字段。这些字段 Halo 不认识，首次 import 后就会被丢弃。**它们只在本地保留用于初始追踪**——pull 回来后这些字段不存在，不要重新加回去。

5. 写回文件（保留原有的 frontmatter 不变）—— ⚠️ **write_file 时必须包含完整的 frontmatter 闭合 `---` 分隔符**。YAML 解析器要求 frontmatter 以 `---` 开头和结尾；缺少闭合分隔符会导致 `halo post import-markdown` 报 `end of the stream or a document separator is expected`。验证：文件第 1 行是 `---`，tags 后有一个空行 + `---` + 空行再开始正文

6. **翻译完整性校验**：写回后立即用 `read_file` 从头读文件，逐项检查：
   - [ ] frontmatter `---` 闭合正确（第 1 行 → tags 后空行 → `---` → 空行 → 正文）
   - [ ] 翻译声明完整（`> 📌 本文翻译自 [链接](...)，作者 ...` 中的链接和作者名未被截断）
   - [ ] 正文开头 3-5 个句子完整（关注第 8-12 行附近段落，不被 frontmatter 边界影响）
   - [ ] 代码块闭合正确（` ``` ` 成对出现）
   - [ ] 中文句子无意外截断（「因此」「所以」「但」等转折词后有完整内容）
   - [ ] 序号/编号未丢失（一、二、三 → 1. 2. 3. 完整转换）

翻译完后可以再次 `detect` 确认。

> **🔴 CHECKPOINT · 🛑 STOP：语言检测/翻译完成。确认文件内容无误后，再进入 Phase 0.5 标题重写。**

#### Phase 0.5: X 剪藏 / 无标题文章的标题重写（⚠️ Phase 1 之前必须做）

**问题：** X/Twitter 剪藏文章的原始 title 通常是机器生成的格式——如 `"X 上的 某某：...完整推文..."` 或 YAML 折叠标量长文——直接推到 Halo 会导致页面标题很长很丑、slug 也是机器生成的无意义字符串。

**触发条件：** 以下任一模式都触发重写：
- `title` 以 `"X 上的` 或 `"X 上的 ` 开头
- `title` 是 YAML `>-` 折叠标量格式的长推文原文
- `title` 明显为机器生成，无人类可读标题
- 文章 body 中完全没有 `#` / `##` / `###` heading（无标题结构的纯文本剪藏）

**做法：在 Phase 1 上传之前重写 title 和 slug**

1. 通读文章内容，理解核心主题
2. **手写一个干净简洁的 title**（10-30 字），最好是正文中会用的 H1 标题
3. **从新 title 推导一个英文 slug**（小写、连字符分隔、无特殊字符），如 `ai-interview-manager-gitops`
4. 用 `patch`（单次精确替换）更新 frontmatter 中的 `title` 和 `slug` 字段
5. 验证 frontmatter YAML 格式完整（`---` 闭合、无折叠标量残留）

**然后进入 Phase 1**，此时 Halo 会直接用干净的 title/slug 创建文章，后续 Phase 2 export 拉回的就是标准格式。

> ⚠️ **常见错误**：先上传 → 拉回后再改 slug。这会导致文章 URL 已经是 ugly slug，改 slug 后旧 URL 404。务必在 Phase 1 之前改好。

> **🔴 CHECKPOINT · 🛑 STOP：标题已重写为人类可读格式，slug 已优化。现在进入 Phase 1 上传到 Halo。**

### Phase 1: 上传原始文件到 Halo (create)

**目标：将原始文件直接导入 Halo，不做任何内容修改。**  import-markdown 会解析 frontmatter 中的 title/slug/categories/tags 等字段，自动生成 cover/slug 并返回 UUID。**不要在此阶段修改文件内容**——cleanup、heading 处理、排版全部在 Phase 3 拉回后集中做。

> ⚠️ **Windows 长文件名处理**：如果源文件路径含中文引号/特殊字符导致 bash 命令报 `File name too long`，用 Python 复制到 temp 短路径后再操作：
> ```python
> import os, glob, shutil
> src = glob.glob(os.path.join(r'D:\1-obsidian\Clippings', '*关键词*'))[0]
> dst = r'C:\Users\zhaid\AppData\Local\Temp\halo-import-<slug>.md'
> shutil.copy(src, dst)
> ```
> 之后全部 Phase 1-5 均操作 `dst` temp 文件。Phase 5 完成后 `shutil.copy(dst, src)` 写回原文。详见陷阱 52。

```bash
halo post import-markdown --file "<文件绝对路径>" --force 2>&1
```

从输出中提取 UUID（`metadata.name: xxxx`），写入状态文件：

```bash
# 用 python 写一行命令保存 UUID
python3 -c "
import json, sys
p = r'<文件绝对路径>'
uuid = '''<从上一步输出粘贴 metadata.name 值>'''
state = {}
try:
  with open('$HOME/.hermes/halo-state.json') as f: state = json.load(f)
except: pass
state[p] = uuid
with open('$HOME/.hermes/halo-state.json', 'w') as f: json.dump(state, f, ensure_ascii=False, indent=2)
"
```

执行完后用 `halo post get <uuid> --json` 确认创建状态。

> **🔴 CHECKPOINT：UUID 已保存，确认 `halo post get` 返回正常后再进入 Phase 2 拉取 frontmatter。**

> ⚠️ **Slug 由 Halo 自动生成，无需手动处理**：slug 和 cover 一样，import-markdown 时 Halo 会自动从 title 生成，export-markdown 拉回 frontmatter 时自动包含。**不需要手动改 slug**——Halo 生成的就够了。如果 slug 确实太短（如 `17`），在 Phase 4 用 `halo post update <UUID> --slug <new-slug>` 修正，但通常不需要。
>
> ⚠️ **`halo.name` 拦截陷阱**
> **修复**：删掉 frontmatter 中的 `halo.name`（以及整个 `halo:` 区块）后再 import。import 成功后先 publish，再 export 拉回完整的 frontmatter（含新的 `halo.name`）。

> ⚠️ 文件路径的 key 格式用正斜杠 `D:/1-obsidian/...` 即可（与旧版 Python 脚本的兼容格式不同）。

### Phase 2: 拉回 Halo frontmatter (pull)

**目标：用官方 CLI 导出含 cover/frontmatter 的 Markdown，写回本地文件。这个 frontmatter 就是 Halo 的标准——只对它补充和填写已有字段，不要新增 Halo 不认识的属性。**

```bash
# 从状态文件读取 UUID，导出完整 frontmatter
halo post export-markdown <UUID> --output "<文件绝对路径>" 2>&1
```

**内置 cover**：`export-markdown` 拉回的 frontmatter 自动包含 `halo.cover`（如果有），无需轮询等待。注意 `export-markdown` **不支持 `--force` 标志**，直接传 `--output` 即可。

**验证 frontmatter：** 读取文件检查：
- `title` 非空 ✅
- `slug` 非空 ✅
- `cover` 非空 ✅（关键，Halo 自动配图）
- `halo.name` 非空 ✅
- `halo.publish: false` ✅（刚创建尚未发布）
- **没有新增 Halo 不认识的字段**（如 `source`/`author`/`original_*` 等） ✅
- **这个 frontmatter 就是 Halo 的标准**——后续只补充已有字段（categories/tags），不新建属性

如果 `cover` 仍为空，Halo 端可能还没生成完，稍等几秒再跑一次 export。

> ⚠️ pull 后正文可能含多余空行（段落间 3 个空行），AI 在 Phase 3 做排版优化时处理。
> ⚠️ `source` / `author` / `description` 等非 Halo 标准字段会被 Halo 丢弃，export 后不会出现。这是正常行为——**不要手动补加**。
> ⚠️ **`slug` / `title` / `halo.*` 等 Halo 已有字段不要重写**——export 拉回来的就是标准，保持原样。

> **🔴 CHECKPOINT：frontmatter 验证完毕，确认 cover/slug/halo.name 齐全后再进入 Phase 3 内容处理。**

### Phase 3: 内容处理（cleanup + heading + 排版）——拉回后集中做

**目标：** 在 `export-markdown` 拿到完整 frontmatter 后，集中进行所有内容处理：
1. 清理原始 HTML 标签（`<video>`/`<audio>`/`blob:` → poster 链接）
2. **所有文章默认三级标题结构（H1→H2→H3）。禁止扁平目录（纯 H2 无 H3）。每章至少拆 2 个 H3 子节。**
3. 编号章节标题
4. 补充分类/标签，优化排版

> ⚠️ **Phase 0 只做语言检测，不做文件修改。所有 cleanup/enhance/排版都在此阶段完成。**

#### 第〇步：清理 raw HTML 标签（Twitter 视频嵌入等）

在 heading 处理前，先清理原始 HTML 标签：

```bash
python "$HOME/.hermes/scripts/halo-publish.py" cleanup "<文件绝对路径>"
```

脚本会自动：
- 扫描 `<video>`/`<audio>` 标签 → 提取 `poster` URL → 替换为可点击封面图 `[![视频截图](poster)](原文链接)`
- 删除附件的视频时间戳行（如 `0:02 / 0:32`）
- 检测残留的 `<iframe>`/`<embed>`/`blob:` 并警告
- ⚠️ **X 线程回复元数据不在此脚本处理范围**——`halo-publish.py cleanup` 只处理 HTML 标签和 blob: URL。**X 剪藏的回复元数据（「引用」、用户名、`@`、`发布你的回复`、`由 AI 生成`、时间戳）必须 AI 在 Phase 3c 手动剥离**。详见上方「排版优化 Prompt」中的「X 剪藏必做 cleanup」子节。
- ⚠️ **替换后重新读取相邻段落**，确认删除范围没有意外截断原文
- 幂等，可重复执行

> **🚫 X Article 视频无法自动化下载**：详尽的调研（2026-06-29 验证）确认目前没有任何 CLI 工具支持 X Article 视频下载。yt-dlp、videodl、gallery-dl 均不支持。CDP 自动化也被 Service Worker + MSE 拦截。唯一可行方案是用户手动用 **OmniGet**（`Alt+O`）或 **猫抓** 扩展下载。详见 `references/x-article-video-handling.md`。

> ⚠️ **访问 X/Twitter 时用 obu，不要用 browser_navigate。** `browser_navigate`/`mcp_chrome_devtools_*` 连接的是无登录态浏览器，无法访问 X。obu 使用你的真实 Chrome 登录态，位于 `/d/npm-global/obu`。

#### 插曲：自动编号标题

清理后运行自动编号脚本（位于 skill 的 `scripts/` 目录下）：

```bash
# ⚠️ 如果报 `can't open file`，$HOME/~ 在 Windows git-bash 中可能解析异常
# 改用绝对路径：
python "C:/Users/zhaid/AppData/Local/hermes/skills/obsidian-halo/scripts/auto-number.py" "<文件绝对路径>"
```

脚本会自动完成：
- 剥离 X 文章中的作者签名/自介内容（全文扫描，不限 blockquote 或正文）
- 从 tags 中自动移除 `clippings`
- H1 缺失时从 frontmatter title 补一个
- H2 编号，支持多种原始格式（`0.N-` / `一、` / 纯文本）
- 将 `**模块X：标题**` 格式的粗体子节转为 `### X.Y 标题`
- 已有编号的标题自动跳过
- 纯叙事文章（无任何 H2）：按图片位置自动分章节、从首段提取标题

> ✅ 脚本处理短粗体标题（<20 字），支持中文句号`。`、感叹号`！`等结尾。超过 20 字或含引号的长粗体句不会被自动转——AI 在此步骤后手动补充。

#### 第一步：手动修复 heading 结构

1. 用 `search_files` 确认 auto-number 后的实际 heading 状态
2. 按下方 Checklist 逐项修复。**发现层级问题（如"第 X 步"冗余、子步骤错为 H2、X 剪藏噪音）时，用 `write_file` / `execute_code` 一次性重写完整正文，不要逐个 `patch`。**
3. 最后再用 `search_files` 确认无重复编号

**决策树——根据 heading 结构选择处理方式：**

| 当前结构 | 做法 |
|----------|------|
| 已有 `#` + `##` + `###` 三级结构 | 直接编号 + 排版 |
| 只有 `##` + `###`（无 H1） | 正文首行补 `# 文章标题` 作为一级标题 |
| 正文有 H1 | 保留 H1，搭配 `##`/`###` 形成三级结构 |
| **正文有多个 H1（如子标题分区）** | **补 `# 文章标题` 作为顶层 H1 → 现有 H1 降级为 `## N.` → 其下的 H2 子节降级为 `### N.X`。每个旧 H1 作为独立大章** |
| **首段是超长 H2（40+ 字的大段陈述句）** | 这通常是 X 剪藏文章的开场白被编辑误标为 `##`。不会出现在 auto-number 的编号中。做法：用 `str.replace` 将整行去掉（`'## 完整句子\\n\\n'` → `''`），然后 `re.sub` 将后续 H2 重新编号（从 N-1 开始倒序遍历）。**⚠️ 先 `search_files` 确认后续编号行不受影响后，再批量替换。** |
| 纯文本无 markdown 标题 | **默认 H1→H2→H3 三级**。AI 分析内容语义：首段 H1（文章标题），按主题切分 H2 章节，每章至少拆 2 个 H3 子节。**禁止只建 H2 不拆 H3**——否则 TOC 扁平。 |
| 正文用 `**粗体**` 代替 `##` 标题（X/Twitter 剪藏常见） | auto-number 会报「No H2 headings to number」。AI 必须：①用 `search_files` 找出所有独立成行的 `**粗体**`（不跟后续段落文字在同一行）；②判断哪些是章节标题、哪些是普通强调；③将标题型粗体转为 `## N. 标题`；④按内容语义拆 H3 子节。⚠️ 用 `write_file` / `execute_code` 一次性写回完整正文，不要逐个 `patch`。 |

> 💡 **H3 批量插入指南（长教程文章适用）**：当文章有 10+ 个章节需要插 H3 时，采用以下模式：
> 1. 用 `execute_code` 一次性读取文件
> 2. 构造 `[(h3_text, unique_anchor), ...]` 列表（每章 ≥2 个）
> 3. 对每条，`content.count(anchor) == 1` 后 `content.replace(anchor, h3 + anchor, 1)`
> 4. **关键先检查各 anchor 的唯一性**：同一锚句话可能在不同章节复用（如"例如："、"这种方法适合："——这些不能做 anchor，必须用足够长的上下文区分）
> 5. **跨章节 anchor 碰撞**：一个锚句可能在 A 章节和 B 章节都出现（如"你搭的这个 vault"既是第 10 章的引言又是第 11 章的内容描述）。替换后 H3 会出现在错误章节，破坏编号顺序。**修复**：每个 anchor 替换前用 `content.count(anchor)` 确认唯一性。替换后立即用 `search_files pattern="^#{1,4} "` 检查 H3 的行号顺序——如果 `10.2` 排在 `11.1` 之后、`11.2` 之前，说明 anchor 匹配错误。用 `write_file` 一次性重写正文修复。
> 6. 全部替换完后 `re.findall(r'^### \d+\.\d+ ', content, re.MULTILINE)` 验证总数
> 7. 用 `write_file` 一次写回，不要逐个 `patch`
> 8. **验证**：`terminal` 工具执行 `wc -c` 确认文件大小合理，然后用 `search_files pattern="^#{1,4} "` 确认每章 H3 ≥ 2 **且 H3 行号顺序正确**（10.1 < 10.2 < 11.1 < 11.2）

> **⚠️ inline code 替换陷阱**：用 `content.replace()` 做行内代码格式化时，如果 old_string 太短（如 `OpenAI`），可能意外命中文件中其他位置的同一文字。**始终用足够长的上下文做 old_string**（如 `OpenAI 官方对 Codex 的定位是` 而非裸 `OpenAI`）。且链式 replace 中每个替换都会改变后续内容，前面的替换不会影响后面替换的匹配位置（`replace` 操作的是已替换后的完整字符串）。
>
> **⚠️ 中文引号锚点陷阱**：在 `execute_code` 中用 `content.replace()` 时，如果 anchor 字符串包含**中文全角引号**（`"` U+201C / `"` U+201D），Python 解释器可能将它们误判为 ASCII 双引号，导致 SyntaxError。即使编辑器显示正常，Python 解析器也会在 `"` 处认为字符串已结束。**修复**：① 避免 anchor 中含有 `"`/`"`/`「`/`」` 等特殊引号字符；② 或将包含引号的文本提取到变量中再使用；③ 对于表格行中的中文引号，改用不含引号的唯一前缀做 anchor。
>
> **⚠️ `execute_code` 文件大小异常**：在 `execute_code` 环境中调用 `len(content)` 或 `os.path.getsize()` 可能返回不一致的值（如 7KB 当文件实际为 14KB）。这是因为 sandbox 环境的文件系统映射偏差。**修复**：每次 `write_file` 后，用 `terminal` 工具执行 `wc -c` 或 `wc -l` 确认真实文件大小。

#### 第二步：Heading 层级决策 Checklist（必做）

- [ ] **重复编号检查**：auto-number 后立即 `search_files` 确认所有 `##` 和 `###` 编号唯一。特别注意四种场景：(a) 若有两个 `2.1` 或两个 `3.1`，说明结论句被误转为 H3，按陷阱 48 修复；(b) 若有 `## N. N.` 格式（如 `## 1. 1\\. Title`），说明 `\\.` 转义编号被 auto-number 二次编号，按陷阱 49 修复；(c) 若有 `### N.N N.N 标题` 格式（如 `### 1.1 1.1 六项能力跃迁`），说明 auto-number 把原始 `**1.1 标题**` 的编号和自己的编号都保留了。用一条 regex 修复：`re.sub(r'^(### \\d+\\.\\d+) \\d+\\.\\d+ ', r'\\1 ', content, flags=re.MULTILINE)`。(d) H3 双重编号从粗体→H3 转换产生时（如 `### 3.1 1\\. 假设清单`），原始 `**1\\. 假设清单**` 的 `1.` 编号被 auto-number 保留 + 新编号前缀生成双重。用 `re.sub(r'^(### \\d+\\.\\d+) \\d+\\. ', r'\\1 ', content, flags=re.MULTILINE)` 修复（注意不带反斜杠转义的 `.` 匹配的是文字点号，与陷阱 49 的 `\\.` 转义格式不同）。
- [ ] **body H1 检查（区分 auto-number 添加 vs 原文自带）**：auto-number.py 会自动从 frontmatter title 补一个 H1 到正文。但 Halo 主题已从 frontmatter 渲染标题。此时需区分两种情况：
  - **auto-number 添加的 H1**（原文无 H1，auto-number 报告"补了 H1"）：立即删除（替换为空字符串），因为主题已从 frontmatter 渲染了标题。
  - **原文自带的 H1**（如翻译文章、原创文章本身就有的 `# 标题`）：**保留**。正文 H1 是文章结构的一部分，Halo 页面有两个同文 H1（主题 + 正文）是正常的——参见陷阱 6。
  
  **判断方法**：auto-number 输出中如果出现"补了 H1"则说明是添加的；如果出现"无需补充 H1"说明本身就是原文自带的。用 `search_files pattern="^# "` 确认后再决定删除或保留。

- [ ] **完整层级（所有文章默认三级）**：正文需要 `#`（H1 文章标题）→ `##`（H2 章节）→ `###`（H3 子节），至少 3 级交替。**纯 H2 无 H3 = 扁平目录，禁止**——每章至少拆 2 个子节。H3 以下用有序/无序列表，不要 H4+。
- [ ] **多版本文章结构**：当文章包含多个独立版本/案例（如不同角色的 AI 视频 prompt），用 `---` 分隔版本，每个版本用 `## N. 版本名` 编号，结尾加 `## 总结` 收束。版本内部：元属性（风格/时长/场景/角色）用加粗标头 + 分镜用独立代码块。不要把所有版本塞在同一章内。
- [ ] **逐章验证 H3 数量 ≥2**：使用快速法或脚本法：
  **快速法（推荐）**：`search_files pattern="^#{1,4} "` 查看带行号的 heading 列表。从行号间隔判断每章 H3 数——如果两个相邻 H2 的行号差 <4（中间无 H3 行），说明该章缺少子节。示例输出中 `30: ## 1. ...\n34: ### 1.1\n38: ### 1.2\n42: ## 2. ...` 即表明第 1 章有 2 个 H3。
  **脚本法**：用 `python3 << 'PYEOF'` 按章节分组精确统计：
  ```python
  # 检测方法
  with open(path) as f:
      lines = [l.strip() for l in f]
  ch = None; h3s = 0
  for l in lines:
      if l.startswith('## ') and l[3].isdigit():
          if ch and h3s < 2: print(f'⚠️  {ch} 只有 {h3s} 个 H3')
          ch = l.split('## ')[1]; h3s = 0
      elif l.startswith('### '): h3s += 1
  if ch and h3s < 2: print(f'⚠️  最后章节 {ch} 只有 {h3s} 个 H3')
  ```
  **常见修复**：不足 2 个 H3 的章节通常是定义区（列出了触发/停止/适用场景等属性但没有独立 H3）。在章节开头补 `### N.1 定义与适用场景`（从列表上方提取核心描述）即可达到 ≥2。不要删除原有 H3——修正方向是**补**不是删。
- [ ] **X.Y 子节编号**：H3 子节必须带章节编号前缀。如第 4 章的子节为 `### 4.1 正文长度`、`### 4.2 正文的内容框架`，第 5 章为 `### 5.1` ~ `### 5.4`。不要出现「4.1 一、正文长度」这类冗余中文编号。
- [ ] **X Article blockquote 标题**：`> **一、章节名**` → `## N. 章节名`
- [ ] **「第 X 步」冗余清理**：auto-number 会让教程型文章的 `## 第 0 步 准备清单` 变成 `## 1. 第 0 步 准备清单`。用 Python `re.sub` 批量去掉冗余的「第 N 步」前缀（`r'(## \d+\.)第 \d+ 步 '` → `\1`），使标题干净为 `## 1. 准备清单`。
- [ ] **子步骤 H2 → H3 降级**：auto-number 不认识 `## 1、创建 API Key` / `## 2、下载 opencode` 这类子步骤格式，把它们编号为 H2。AI 必须：①分析哪些 H2 是其他章节的子步骤（一级结构 vs 二级结构）；②将它们降级为 `### X.Y` 并放在正确的父 H2 下。此步必须手动用 `write_file` 或 `execute_code` 一次性重写完整正文，不要逐个 `patch`。
- [ ] **中文数字标题补齐（十一~十九等）**：auto-number 的 H2 格式化只处理单字中文数字（`一、`~`十、`），不处理多字（`十一、`~`十九、`）。如果 Phase 3b 后 H2 仍含 `十一、` `十二、` 等前缀，用 `re.sub(r'^## (\\d+\\. )(?:十一、|十二、|十三、|十四、|十五、)', r'^## \\1', content, flags=re.MULTILINE)` 批量清理。
- [ ] **中文数字前缀清理（`## N. 一、` → `## N. `）**：auto-number 将 `# 一、标题` 转为 `## N. 一、标题` 后，H2 编号和中文数字同时存在（如 `## 1. 一、标题`）。用 `re.sub(r'^(## \\d+\\.)[一二三四五六七八九十][、，]? ', r'\\1 ', content, flags=re.MULTILINE)` 一键清理。对十一~十九做二次处理。
- [ ] **断章检测（`## ：` 空内容标题）**：某些 X 剪藏的 `## 九、` 可能因复制异常变成 `## ：`（缺了中文数字）。auto-number 不会报错，编号后变成 `## 13. ：`。`search_files pattern="^## \d+\. ："` 有命中即需修复。
- [ ] **断章标题检查**：X 剪藏文章的中文数字章节标题可能丢失数字，变成 `## ：标题`（只剩冒号）。检测方法：`search_files pattern="^## \d+\. ："`，有命中即需从上下文推测章节编号后修复。

> **💡 编号做法**：H2 章节编号（`## 1. 标题` → `## 8. 标题`）推荐用 Python `re.sub` + `MULTILINE` 一行完成，不做 N 个独立 patch。详见陷阱 32 的代码示例。

#### 第三步：补充分类/标签 + 排版优化

1. **export 回来的 frontmatter 就是标准**——`title`、`slug`、`halo.*` 已经齐全且正确，不要动它们
2. **先检查 frontmatter 实际状态，再操作 `categories` 和 `tags`**：auto-number 可能已将 `tags:` 清空（移除了 `clippings` 后无其他标签）。用 `read_file` 读前 15 行确认 `tags:` 的行状态后再构造替换字符串：
   - `tags:` 空时（`tags:\nhalo:`），替换 `tags:\nhalo:` 为完整新块
   - `tags:` 有子项时（`tags:\n  - xxx\nhalo:`），追加新标签到列表中
3. **加新分类、新标签（3-8 个）**。⚠️ **绝对不能留空或 `categories: []`**——空分类/标签会导致 Halo 在 import-markdown 时静默清空已有值。其他字段一律不动。**不要新增 Halo 不认识的属性**（如 `source`、`author`、`description`、`original_*` 等——export 后它们本来就不存在）
4. 按排版规则优化正文（见「排版优化 Prompt」）
5. **验证 frontmatter 完整性**：`write_file` 写回前，用 `read_file` 读前 15 行确认 `categories:` 有值、`tags:` 有值（非空列表）。如果留空，import-markdown 后 Halo 端分类/标签会消失。
4. `write_file` 写回

#### 排版优化 Prompt

在写回前，对正文执行以下排版规则：

- **段落间距**：段落之间保留且只保留一个空行
- **图片说明**：图片和说明用 HTML 包裹（markdown 语法在 HTML 块内不生效）。居中对齐、自适应屏幕、不溢出。格式：

  ```html
  <div align="center">
  <img src="图片URL" alt="说明" style="max-width:100%;height:auto;display:block;margin:0 auto;">
  <em>▲ 说明文字</em>
  </div>
  ```

  `▲` 表示"上图"。图片宽度不超过屏幕（`max-width:100%`），高度自适应，居中显示。

  ⚠️ **不要包裹 poster 链接图片**：`[![alt](img_url)](原文链接)` 格式的 poster 链接必须在 markdown 链接内保留原始 `[![alt](img)](url)` 格式。HTML `<div>` 包裹在 markdown 链接内是无效语法。只对裸 `![alt](url)` 图片应用 HTML 包裹。检测方法：`[` + `![` 相邻即为 poster 链接，跳过。
- **图片**：前后各留一个空行，alt 文本应有语义（非 `![图像]`），禁止空 `![]()`
- **连续图片**：多张图片之间只留一个空行，避免视觉堆积
- **代码块**：前后各留一个空行，必须标注语言（如 ` ```python `、` ```bash `），禁止裸 ` ``` `
- **用户指令/prompt 示例**：以下两类 prompt 格式必须转为 ` ```text ` 代码块，代码块更清晰地分离「用户指令」和「文章正文」，且支持长 prompt 不破坏页面布局。

  **类型 A：`[text]` 引用格式** — X/Twitter 文章中常见的 `> **\[text\]** 指令内容`，作者用来表示"用户给 AI 的输入"。替换为 ` ```text ` 代码块。


  **类型 B：结构化 prompt（含 【风格】/【场景】/【角色】/【时长】或 `[00:00-00:XX]` 时间码）** — 当文章以分享 AI 视频/代码提示词为主要内容时，区分两层处理：

  - **元属性层（【风格】/【时长】/【场景】/【角色】）**：保持为正文 `**【属性名】 值` 的加粗标头格式。这是说明性质，不需要放进代码块——读者一看就懂是 prompt 参数设定。
  - **分镜/场景层（`[00:00-00:03]` 镜头 + 描述 + 音效）**：**每个场景独立一个 ` ```text ` 代码块**，不做合并在一个巨型代码块里。原因：
    - 单个大代码块太长，无法快速定位特定场景
    - 每个场景独立代码块有独立的复制按钮，便于读者单独提取
    - 视觉上清晰分隔不同镜头，阅读节奏更好

  元属性用 `---` 分隔线与分镜详情分隔，分镜详情前加 H3 `### 分镜详情`，然后逐个 scene 代码块排列。

  **替换方式**（execute_code 中）：
  ```python
  result = []
  for line in content.split('\n'):
      if '\[text\]' in line:

          prompt = line[line.index('**', 2)+4:]  # skip "> **[text]** "
          result.append('```text\n' + prompt.strip() + '\n```')
      else:
          result.append(line)
  content = '\n'.join(result)
  # 清理残留的 ** 前缀（如果 prompt 开头有 ** 闭合标记）
  content = re.sub(r'```text\n\*\* ', '```text\n', content)
  ```
  ```
  替换后用 `search_files` 确认无残留 `[text]`、`**###` 或 `> **` 污染。
- **引用块**：前后各留一个空行，引用内连续行不用空行（维持同一 blockquote）
- **列表**：列表前后各留一个空行，嵌套列表用 4 空格缩进
- **重点标注**：专业名词、关键结论、术语首次出现时用 `**加粗**` 强调
- **视觉美化**：综合运用多种 Markdown 标注方式提升阅读体验，每类 3-8 处，不过度：

  - `**加粗**` — 专业名词首次出现、关键结论句的**核心部分**。不要整段加粗，只加粗结论中的点睛词或短句（5-15 字最佳）。
  - `` `行内代码` `` — 文件名、命令、API 名称、版本号、协议名、工具名。长文中每隔 1-2 段出现一次，形成视觉节奏。
  - `> 引用` — 全文最精彩的一两句洞察独立成段。适合：章节末尾的核心判断、全文升华总结。一篇长文 1-2 处引用就够，多了反而稀释效果。
  - `---` 分隔线 — 只在**主题大切换**处使用。判断标准：读者读到此处应有一个自然的「换气」停顿。一般 2-3 条分隔线即可，不要每章之间都加。
  - `**结论句独立成行**` — 段落末尾的观点提炼句，加粗后单独一行。读完后自然形成视觉锚点，比埋在段落里更容易被记住。

- **结论标题测试（借鉴 CyberPPT）**：H2 章节标题应当是**可辩护的判断句**，而非标签。用「弱标题 vs 强标题」自检：
  - ❌ 弱：`## 3. 市场概览` → 只是标签，没有观点
  - ✅ 强：`## 3. 市场增长正在修复，但价值正在向结构性优势赛道转移`
  - ❌ 弱：`## 5. 消费者分析` → 不知道要说什么
  - ✅ 强：`## 5. 核心消费者继续扩大，但购买逻辑更加分化`
  
  强标题必须是「可以被页面证据挑战并守住」的完整判断。如果标题改成判断句后觉得证据撑不住，说明章节内容本身需要补强，而不是退回标签。每写完一个 H2，花 5 秒问自己：「这个标题有没有结论？」

- **证据层级结构（借鉴 CyberPPT）**：每节正文按「结论→主证据→次级证据→解读→含义」的顺序组织，不要只摆图表/数据不说明它证明了什么。一篇长文中至少 2-3 节完整走完这个层级：
  1. **结论** — 该节的核心判断（对应 H2/H3 标题）
  2. **主证据** — 最强的一两个数据、事实或引用来支撑结论，标记来源
  3. **次级证据** — 细分数据、对比、趋势拆解（可选，看篇幅）
  4. **解读** — 这些证据放在一起说明了什么（连接证据和结论的逻辑链）
  5. **含义 / SO WHAT** — 读者为什么要关心这个？影响是什么？下一步行动？

  最低要求：每节至少要有「结论 + 证据 + 含义」三层。避免「只有数据没有解读」或「只有观点没有证据」。

  **X 剪藏必做 cleanup（比普通文章多三步）：**
  1. 剥离 X 线程回复元数据：「引用」、用户名、`@`、时间戳、`发布你的回复`、`由 AI 生成`、点赞数、视频时长标签等 X UI 元素——全部从正文中删除。它们属于网页 UI，不应出现在文章正文段落。\n  2. 检查文章是否为结构化 prompt 分享（含 `【风格】`/`【场景】`/`【角色】`/`【时长】` 或 `[00:XX-00:XX]` 时间码）。如果是：元属性段（【风格】【时长】【场景】【角色】）用 `**【属性名】**` 加粗标头 + 正文保留在代码块外；分镜段（含时间码的镜头描述）按 `[00:XX-00:XX]` 自然分界**拆成多个独立 ` ```text ` 代码块**，每个场景一块。用 `---` 分隔元属性与分镜，分镜部分前加 H3 `### 分镜详情`。\n  3. 拆分后全文搜「引用」、「发布你的回复」、「没有项目」、「由 AI 生成」等——不可有任何残留。
  3. 剥离后检查：全文搜「引用」、「发布你的回复」、「没有项目」、「由 AI 生成」等——不可有任何残留。

> **🔴 CHECKPOINT · 🛑 STOP：内容处理完毕。确认以下 3 项后再进入 Phase 4 发布：**
> 1. ✅ heading 结构：H1→H2→H3，无重复编号
> 2. ✅ 分类标签：`categories:` 和 `tags:` 非空（用 `read_file` 前 15 行确认）
> 3. ✅ 排版满意
>
> **⚠️ 如果 frontmatter 中 `categories:` 或 `tags:` 为空，import-markdown 后 Halo 端会丢失已有分类/标签。这是不可逆操作，发布后修复需要手动删掉重新 import。**

### Phase 4: 推送更新到 Halo (update)

**目标：将 AI 增强后的内容发布到 Halo。**

#### 推荐方式（保留 heading 级别）：import-markdown → 单独 publish

> ⚠️ **`halo post update --content` 会吞掉一级 `#`**（`##`→`#`），导致 heading 层级偏移、TOC 错乱。
> **永远优先用 `import-markdown` 提交含 heading 的正文。**

```bash
# 1. 用 import-markdown 更新内容（保留 heading 级别不变）
halo post import-markdown --file "<文件绝对路径>" --force 2>&1

# 2. 单独发布（不传 --content）
halo post update <UUID> --publish true 2>&1

# ⚠️ 验证发布是否真正生效（CLI 可能返回 success 但实际还是 draft）
halo post get <UUID> --json 2>&1 | tail -n +2 | python3 -c "
import sys, json
full = sys.stdin.read()
start = full.index('{')  # 跳过 TARGET 等非 JSON 前缀行
d = json.loads(full[start:])['post']['spec']
print('publish:', d.get('publish'), '←', '✅' if d.get('publish') else '❌ STILL DRAFT!')
"
# 如果还是 false，重跑一次 halo post update <UUID> --publish true
```

从输出提取 UUID。`import-markdown` 会解析 frontmatter 中的 title/slug/categories/tags，无需额外传参。

> ⚠️ **slug 由 Halo 自动管理**，import-markdown 创建时从 title 生成，export-markdown 拉回时自动包含，无需手动处理。如果 slug 确实太短（如 `17`），用 `halo post update <UUID> --slug <new-slug>` 修正。

> ⚠️ **`halo.name` 导致 heading 损坏（重要！）**：如果 frontmatter 中含 `halo.name`，`--force` 走的是「更新」流程而非「创建」。此时 Halo 会重新处理 heading 编号，导致 `# 3 个Skill` 变成 `# 1- 个Skill`、`## 1. 标题` 变成 `## 1.1- 标题`。**第一次上传文章时务必删除整个 `halo:` 块**，import 成功后再 publish → export 拉回含新 `halo.name` 的 frontmatter。后续用 `halo.name` 做 update 则不会损坏 heading。详见陷阱 43。

#### 验证 heading 级别 + 同步回本地

发布后立即验证 heading 级别是否正确：

```bash
halo post get <UUID> --json 2>&1 | python3 -c "
import sys, json
full = sys.stdin.read()
start = full.index('{')  # 跳过 TARGET 等非 JSON 前缀行
c = json.loads(full[start:])['content']['raw']
for l in c.split('\n'):
    if l.startswith('#'): print(l.strip())
"
```

> ⚠️ **代码块内 `#` 行会被误显示为 heading**：bash 代码块里的 `# 注释` 行会在上述输出中看起来像 H1 标题，但实际页面渲染为代码块。**以 browser_console 的 `document.querySelectorAll('h1').length` 为准**，别被 raw content 里的伪 heading 误导。

确认 heading 级别与本地一致（`##`/`###` 未被吞掉）。然后用 `export-markdown` 同步回本地：

```bash
halo post export-markdown <UUID> --output "<文件绝对路径>" 2>&1
curl -s "https://jia.baoyu2023.top/archives/<slug>?nocache=1" | grep "<title>"
```

### Phase 5: 校验 Halo 页面效果

`update` 已自动验证。如有必要，用浏览器确认视觉渲染。**Twitter 来源的文章尤其建议浏览器验证**（auto-verify 只能检查 HTTP + 标题，无法检测嵌入 HTML 造成的布局问题）。

> ⚠️ **关于登录态页面**：系统浏览器工具（`browser_navigate`/`mcp_chrome_devtools_*`）**没有登录态**，无法访问需要登录的页面（如 X/Twitter、Halo 后台）。必须使用 **obu**（Open Browser Use，`/d/npm-global/obu`）——它使用你的真实 Chrome 登录态。详见 `references/x-article-video-handling.md`。

用 `browser_navigate` 打开 Halo 页面后，执行以下检查：

**快速检查（browser_console）：**
```javascript
({
  h1: document.querySelectorAll('h1').length,
  h2: document.querySelectorAll('h2').length,
  h3: document.querySelectorAll('h3').length,
  video: document.body.innerHTML.indexOf('<video') >= 0 ? '⚠️' : '✅',
  blob: document.body.innerHTML.indexOf('blob:') >= 0 ? '⚠️' : '✅'
})
```

**完整检查列表：**
- [ ] 标题正确显示
- [ ] 封面图存在
- [ ] **三级标题结构完整（H1 + H2 + H3）**
- [ ] 标题编号正确（1. / 2. / 3. ...）
- [ ] 代码块有语言标注且渲染正常
- [ ] 无原始 HTML 标签泄漏（video / iframe / blob: URL）
- [ ] 无段落被意外截断

如果发现问题，修改文件后重新 update。最多重新处理 2 次。

---

## 命令参考

### Python 脚本（保留检测/清理/增强能力）

配套 Python 脚本位于 `C:/Users/zhaid/.hermes/scripts/halo-publish.py`（⚠️ 勿用 `~`/`$HOME`，Windows git-bash 可能解析异常），保留暂时无法被 CLI 替代的功能：

| 命令 | 作用 | 备注 |
|------|------|------|
| `detect <file>` | 检测文章语言，CJK 比例≥20%→中文 | CLI 无替代 |
| `cleanup <file>` | **自动清理** `<video>`/`<audio>` blob: 标签→海报图 | CLI 无替代 |
| `auto-number <file>` | **自动编号 H2/H3** + 补 H1 + 剥离 X 自介内容 + 叙事文章按图片分段 | skill 的 `scripts/auto-number.py`；`--check` 仅检视不改动 |
| `verify <file>` | 独立验证 | 可用 `halo post get` + curl 替代 |

### 官方 CLI 命令（替代原 create/pull/update）

| 操作 | 命令 | 说明 |
|------|------|------|
| 创建/更新文章（推荐） | `halo post import-markdown --file <path> --force` | 保留 heading 级别，解析 frontmatter |
| 导出 frontmatter | `halo post export-markdown <uuid> --output <path>` | 拉回 cover/slug/halo.*；不支持 `--force` |
| 单独发布 | `halo post update <uuid> --publish true` | 不传 --content，避免 heading 降级 |
| 删除文章 | `halo post delete <uuid> --force` | 清理测试数据 |
| 查分类 | `halo post category list` | 查阅已有分类 |
| 查标签 | `halo post tag list` | 查阅已有标签 |

状态通过 `~/.hermes/halo-state.json` 自动追踪 UUID。
配置通过 `~/.hermes/halo-config.json`（PAT + blog URL）。

辅助脚本：
| 脚本 | 作用 |
|------|------|
| `scripts/auto-number.py <file>` | **自动编号 H2/H3 标题**，支持 0.N- / 一、/ 纯文本；补 H1；粗体→H3；剥离 X 自介内容；叙事文章按图片分段；`--check` 仅检视 |
| `scripts/obu_extract.py <article_url> <output.json>` | Python 版 obu 视频提取器（替代旧 sh 版），自动找播放按钮 → 点击 → 提取 CDN URL（best-effort）；**始终在 `finally` 块执行 `finalize-tabs` 清理** |
| `scripts/verify-article.py <file>` | 独立文章完整性验证 |
| `scripts/halo-migrate-images.py <file>` | 扫描外部图片→下载→生成 Halo 上传命令 | 防盗链图片迁移；已推送到 GitHub 仓库 |

参考文件：
| 文件 | 作用 |
|------|------|
| `references/halo-css-injection.md` | Halo 后台代码注入 CSS 的陷阱与最佳实践（prefers-color-scheme vs Color Toggle、主题变量覆盖、字体加载优化） |
| `references/halo-cli-usage.md` | Halo 官方 CLI 完整命令清单、import-markdown 的创建/更新区别、与 Python 脚本的功能对比 |
| `references/cli-content-length.md` | CLI `--content` 参数长度限制、base64 曲线方案、`--publish true` 单独使用技巧 |
| `references/import-export-pitfalls.md` | `halo.name` 跳过导入陷阱 + export 覆盖本地文件的安全流程 |
| `references/halo-update-heading-trap.md` | `--content` 吞 `#` 导致 TOC 错乱的根本原因与修复路径 |
| `references/halo-publish-script.md` | Python 脚本各功能说明（detect/cleanup/enhance/verify） |
| `references/halo-api-notes.md` | Halo API 注意事项与常见问题 |
| `references/heading-hierarchy.md` | 文章 heading 层级规范详解 |
| `references/obu-cdp-patterns.md` | obu + CDP 调试模式和代码片段 |
| `references/twitter-video-cleanup.md` | Twitter 视频嵌入的清理流程 |
| `references/video-codec-compatibility.md` | 视频编码兼容性（HEVC → H.264） |
| `references/structured-prompt-formatting.md` | 结构化 prompt 排版方案（元属性加粗 + 分镜独立代码块） |
| `references/halo-image-migration.md` | 外部图片迁移全流程（下载→上传→映射） |
| `references/x-article-video-handling.md` | X Article 视频处理的限制和方法 |
| `references/cat-catch-video-workflow.md` | 猫抓 (Cat-Catch) X Article 视频下载工作流 |
| `references/h3-insertion-technique.md` | 用 `execute_code` + `str.replace` 内容锚点批量插入 H3 子节的技术与陷阱 |
| `references/crlf-patch-silent-failure.md` | `patch` 工具在 CRLF 文件上静默失败——返回 success:true 但内容不变 |
| `references/halo-theme-icons.md` | Fluid 主题菜单图标系统（iconfont 注释机制）+ Reicon SVG 图标库速查 + JS 注入替代方案 |

## 完整执行流

### 标准执行流

```bash
# ── Phase 0: 语言检测 ──
# ⚠️ 用绝对路径避免 $HOME 解析异常
python "C:/Users/zhaid/.hermes/scripts/halo-publish.py" detect "D:/1-obsidian/Clippings/文章.md"
# → 英文：AI 翻译 body，保留 frontmatter 不变
# → 中文：跳过

# ── Phase 0.5: 标题重写（条件触发）──
# 如果 title 是 "X 上的..." / YAML 折叠标量 / 无人类可读标题：
#   手写干净 title + 推导 slug → patch 更新 frontmatter → 验证 YAML 闭合

# ── Phase 1: 上传到 Halo ──
halo post import-markdown --file "D:/1-obsidian/Clippings/文章.md" --force
# → 记录 UUID（metadata.name: xxxx）

# ── Phase 2: 拉回完整 frontmatter ──
halo post export-markdown <UUID> --output "D:/1-obsidian/Clippings/文章.md"
# → 验证 frontmatter：title/slug/halo.name/cover ✅

# ── Phase 3: 内容处理 ──
# 3a. 清理 raw HTML（用绝对路径）
python "C:/Users/zhaid/.hermes/scripts/halo-publish.py" cleanup "D:/1-obsidian/Clippings/文章.md"
# 3b. 自动编号标题（用绝对路径）
python "C:/Users/zhaid/AppData/Local/hermes/skills/obsidian-halo/scripts/auto-number.py" "D:/1-obsidian/Clippings/文章.md"
# 3c. AI 修复：检查 Checklist（重复编号/第 X 步/H2→H3/尾部噪音）+ 写回
# 3d. 补 categories/tags + 排版优化（行内代码、加粗、图片说明、引用）
#     write_file 写回

# ── Phase 4: 更新并发布 ──
halo post import-markdown --file "D:/1-obsidian/Clippings/文章.md" --force
halo post update <UUID> --publish true

# ── Phase 5: 验证 ──
halo post export-markdown <UUID> --output "D:/1-obsidian/Clippings/文章.md"
curl -s "https://jia.baoyu2023.top/archives/<slug>?nocache=1" | grep -oP '<title>[^<]+</title>|<h[1-3][^>]*>[^<]+</h[1-3]>'
```

> **⚠️ 关键顺序不可颠倒**：Phase 0.5（重写 title/slug）→ Phase 1（上传）→ Phase 2（拉回 frontmatter）→ Phase 3（处理内容）→ Phase 4（更新发布）→ Phase 5（验证）。`update` 时 frontmatter 会自动包含 `halo.name`，`--force` 会更新已有文章。**frontmatter 以 Halo export 的为准**——只补充已有字段（categories/tags），不新增 Halo 不认识的属性（source/author/description/original_* 等）。

## 黄金规则（工具复用优先）

> 🚨 **全局第一原则**：每次任务按优先级调研 — ①官方 CLI/Skills/MCP/API/插件 → ②社区成熟开源工具 → ③自己写代码。选型以降低 token 消耗、缩短执行链路、提升稳定性为核心标准。**未经调研不得从零编码造轮子。**

在直接 curl Halo API 或调用 Python 脚本之前，先确认官方工具是否已覆盖：

0. **🚨 工具复用优先**：优先查 `@halo-dev/cli`、`obsidian` CLI、`obu`、内置 Skill、MCP 工具等现有能力。不要手写 ad-hoc Python 读 vault 文件——用 `read_file`/`search_files`（文件系统）或 `obsidian read`（Obsidian 运行时）。
1. **`@halo-dev/cli`**（v1.3.0，已安装）— `halo <command> --help`，已有 auth/post/theme/plugin/attachment/backup/comment/moment 等命令
2. **`halo post import-markdown --file <path> --force`** — 导入含 frontmatter 的 Markdown，保留 heading 级别。如果有 `halo.name` 则更新已有文章，否则创建新文章 |
3. **7 个内置 Agent Skill** 在 `/d/npm-global/node_modules/@halo-dev/cli/skills/` — 详见 `references/halo-cli-usage.md`
4. **只有确认无官方封装后，才用 curl 调底层 API**

> 💡 详见 `references/halo-cli-usage.md`（完整命令清单 + 与 Python 脚本的功能对比）。

## 🚫 反例黑名单

以下操作是 obsidian-halo 工作流中的**高危禁区**，违反可能导致内容丢失、heading 损坏或不可逆故障：

| # | 绝对不能做的事 | 后果 | 正确做法 |
|---|---------------|------|---------|
| 1 | 用 `--content` 提交含 heading 的正文 | Halo 吞掉一级 `#`，TOC 全面错乱 | 用 `import-markdown` + 单独 `--publish true` |
| 2 | 首次上传时保留 `halo.name` 做 `import --force` | 跳过解析返回旧 UUID，**本地修改丢失** | 首次上传前删掉整个 `halo:` 区块 |
| 3 | `replace_all=True` 批量替换 | 匹配过宽时级联截断正文，难以恢复 | 用独立 patch 逐一处理，带足够上下文 |
| 4 | 直接调 Halo API 绕过官方 CLI | 复杂的 ConfigMap 操作失败 | 优先用 `@halo-dev/cli` 官方命令 |
| 5 | 在 Python `-c` 双引号内用反引号 | 反引号被 bash 吞噬为**空字符串** | 用 heredoc `<< 'PYEOF'` 或独立 `.py` 文件 |
| 6 | 上传 HEVC/H.265 视频不做兼容处理 | Firefox/Zen 无法播放（`NS_ERROR`） | 用 ffmpeg 转 H.264 + `-movflags +faststart` |
| 7 | export-markdown 后手动补 source/author 等非 Halo 字段 | Halo 不保存，下次 export 消失 | 以 `halo.*` 为准，不新增 Halo 不认识属性 |
| 8 | 在 Obsidian 打开文档时开自动编号插件 | 插件覆盖手动编号（层级编号 vs 平铺编号冲突） | 保持 `number-headings-obsidian` 卸载/关闭 |
| 9 | `&&` 链式连接多个 halo 命令 | git-bash 偶发 exit 127，后续命令不执行 | 拆分到独立的 `terminal()` 调用 |

> 完整陷阱列表见下方章节，每条内含根因分析 + 修复路径。

## 已知陷阱

0. **🚨 视频下载先调研，别闷头折腾自动化**：X Article 视频 MSE + Service Worker 防自动化，所有 CLI 工具（yt-dlp、gallery-dl、videodl、Cobalt API）都不支持。obr CDP 的 `fetch()` 拦截、`Network.enable`、`Input.dispatchMouseEvent` 全试过，全部无效。
   **正确的优先级**：先查 GitHub issues 看工具是否支持 → 再决定是用 poster 链接兜底，还是推荐用户手动 OmniGet。不要花 10+ 工具调用试 CDP 自动化——社区已经验证过这条路不通。详见 `references/x-article-video-handling.md` 的「RESEARCH FIRST!」章节。

1. **Cloudflare 缓存**：验证时加 `?nocache=1` 绕过。
2. **import-markdown + --force 可更新已有文章**：如果 frontmatter 包含 `halo.name`（UUID），`--force` 会更新该 UUID 对应的文章而非新建。但注意陷阱 21：`halo.name` 跳过导入陷阱。
3. **内容更新走 import-markdown，不走 --content**：`halo post update --content` 会吞掉一级 `#`（陷阱 23）。正文更新应使用 `halo post import-markdown --file <path> --force`，然后 `halo post update <uuid> --publish true` 单独发布。
4. **export-markdown 后不补加本地字段**：Halo 不存 source/author/description/original_* 等字段，export 后它们会自然消失。**不要加回去**——以 `halo.*` 为准，本地文件即 Halo 快照。
5. **Heading 层级必须人工审核**：`auto-number.py` 自动编号后，子节归属（X.Y 前缀是否跟随正确的父章节）仍需 AI 按 Checklist 逐项核对。**最终以线上页面渲染结果为准**（browser_console 检查 h2/h3 数量）。
6. **正文要包含 H1（文章标题）**：正文首行必须有 `# 文章标题`，形成完整的 H1→H2→H3 三级标题结构。主题会渲染 frontmatter title 为另一个 H1 页面标题，页面上会出现两个 H1（相同文字），这是正常的——一个来自主题（页面标题），一个来自正文（文章结构头部）。TOC 以 H1 为顶层，H2→H3 正确嵌套。H3 以下用有序/无序列表，不要再切 H4+。
7. **Twitter 视频嵌入已自动清理**：`cleanup` 模式可替换 `<video>`/`blob:`，但无法处理需要登录的 CDN。X Article 视频无法通过自动化提取真实 CDN URL（见 `references/x-article-video-handling.md`）。
8. **文件位置**：文章通常在 `D:/1-obsidian/Clippings/`，但接受任意绝对路径。
9. **`patch` 的 `replace_all` 是危险操作**：`replace_all=True` 会匹配文件中所有出现位置。用独立的 patch 逐一处理，每次用足够多的上下文确保唯一匹配。
10. **每次 patch 后验证正文完整性**：patch 修改 body 后，快速检查关键句未被意外截断。
11. **obu 用于 X/Twitter 登录态**：访问 X 原文时必须用 `obu`（`/d/npm-global/obu`），系统浏览器无登录态。
12. **obu CDP 输出跨多行**：不能按行 `json.loads()`，用大括号平衡累积至完整 JSON。
13. **`halo` 和 `obu` 是 shell 脚本，Python 子进程不能直接调用**：`obu` 和 Node.js 全局安装的 `halo` 在 Windows 上都是 `#!/bin/sh` 脚本，Python 的 `subprocess.run` 会 `FileNotFoundError`。必须在 `terminal` 工具中执行（git-bash）。通过 Python 调用时，用 `terminal()` 工具而非 `subprocess`。
14. **写完 obu 脚本后务必验证 tab 清理**：`finally` 块无条件执行 `finalize-tabs --keep "[]"`。
15. **X Article 的 blockquote 标题需转为 H2**：`> **一、章节名**` → `## N. 章节名`（作为章节标题，非子节）。
16. **export-markdown 后清理多余空行**：导出会在段落间插入 3 个空行，需归一化为 1 个空行。
17. **图片 alt 文本优化**：X 剪藏的 `![图像]` 应改为有语义的描述（如 `![豆包 2.1 Pro 发布会]`）。
18. **halo-state.json 路径格式**：UUID 映射的 key 用正斜杠 `D:/1-obsidian/...` 即可，与旧版 Python 脚本不同。
19. **update publish 409**：如果 `--publish true` 报 409，说明文章已发布，内容已生效。用 `halo post get` 确认即可。
20. ⚠️ 重复——已合并到上方。
21. **永远优先使用 `import-markdown` 而非 `--content`**：`halo post update --content` 会吞掉一级 `#`（陷阱 23），且 Windows Git Bash 下中文可能编码失败。内容更新全部走 `halo post import-markdown --file <path> --force` + `halo post update <uuid> --publish true`。
22. **`--content` 超长时用 import-markdown 替代（首选！）**：Windows 命令行正文限制约 8K 字符。正文超过此长度时，`--content "$body"` 报 `Argument list too long`。方案：用 `halo post import-markdown --file <path> --force` 导入（保留 heading 级别），然后 `halo post update <uuid> --publish true` 单独发布。无需 `--content`。
23. **`--content` 会吞掉一级 `#`（致命！）**：`halo post update --content` 处理正文时，每条 markdown heading 都会减少一级 `#`（`##`→`#`，`###`→`##`），导致渲染出的 heading 层级全面偏移，TOC 错乱。**绝对不要用 `update --content` 提交含 heading 的正文**。改用 `import-markdown` 导入（保留 heading 级别），然后 `halo post update --publish true` 单独发布。验证方法：`halo post get <uuid> --json` 检查 `content.raw` 中的 heading 级别是否正确。
24. **Heading 层级改前先确认用户意图**：不要凭猜测重组 heading 层级。用「文章现有 X 个 H2/Y 个 H3，建议保留 H2 章节 + H3 子节」询问确认后再动手。
25. **obu 也用于 Halo 后台，不仅 X/Twitter**：Halo console（`/console/*`）和后台设置页也需要登录态。遇后台操作时优先用 `obu open-tab` 配合 `--session-id`。
26. **视频编码兼容性（HEVC → H.264）**：上传到 Halo 的视频如果用手机录制，很可能是 HEVC/H.265 编码。Chrome 能播，但 Firefox/Zen Browser 报 `NS_ERROR_DOM_MEDIA_METADATA_ERR`。修复方法见 `references/video-codec-compatibility.md`。
27. **优先用文件级方案，不绕 CMS API**：遇到上传的视频/图片在部分浏览器出问题时，优先替换服务器文件本身，不要试图通过 Halo API 修改页面内容来换 URL。
28. **export-markdown 会覆盖本地文件**：跑完 export 后本地文件被 Halo 端内容完全替换。如果 import/update 未正确执行（如被 `halo.name` 跳过），export 会把**旧内容**拉回来覆盖你的本地修改。**先确认 Halo 端的文章内容正确，再 export 同步回本地**。
（陷阱 29~68 已在历史版本中废弃或合并）\n（陷阱 30~71 已在历史版本中废弃或合并到 `halo-theme-css` skill 中。\n\n69. **代码块内的假 heading 被当作真实标题**：当教程文章的 markdown 代码块中展示了一道「CLAUDE.md 示例内容」，里面含有 `## knowledge` 或类似 heading 文本时，auto-number 的 H2 编号可能跳过该真实标题，或者后续 AI 的 renumber 操作把代码块内的示例文本当成真实 heading 一起修改——导致代码块内出现 `## 11. 知识库的核心结构` 这种**看起来像 heading 实际是代码**的混乱。**修复**：① 在 auto-number 后，用 `search_files pattern=\"^#{1,4} \"` 对比实际渲染的 H1/H2/H3 数量与预期数量；② 如果某章节 heading 出现在预期不该有的位置（比如 header 列表中第 10 章和第 12 章之间的 heading 来自代码块），用 `write_file` 一次性还原被污染的代码块内容；③ **永不信任 `search_files` 输出的绝对精确性**——页面渲染以 `browser_console` 的 `querySelectorAll('hN').length` 为准。④ 预防措施：在 `rename_h2()` 操作后，立即检查代码块范围内有无 `##` 行被误改。

