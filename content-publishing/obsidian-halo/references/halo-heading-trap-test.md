# Halo heading 吞 # 陷阱排查记录

## 现象

`halo post update --content` 将每条 markdown heading 减少一级 `#`：
- `## 标题` → 存储为 `# 标题` → 渲染为 `<h1>`
- `### 子节` → 存储为 `## 子节` → 渲染为 `<h2>`

导致 TOC（tocbot）层级全面偏移，章节标题变成 H1（tocbot 默认不收录 H1），子节变成 H2（在 TOC 中错误地显示为顶级）。

## 复现

```bash
# 错误做法：heading 会被吞一级
halo post update <uuid> --title "文章" --content "## 章节\n\n### 子节" --publish true

# 验证存储的 heading
halo post get <uuid> --json | python3 -c "
import sys, json
c = json.load(sys.stdin)['content']['raw']
for l in c.split('\n'):
    if l.startswith('#'): print(l.strip())
"
# → 看到 # 章节（不是 ##），## 子节（不是 ###）
```

## 根因

Halo 的 content pipeline 在处理 `--content` 参数时，会经过一次 markdown→HTML→markdown 的往返转换，其中 heading 标记被减了一级。`import-markdown` 走的是文件导入路径，不经此转换，故不受影响。

## 修复方案

```bash
# 正确做法：用 import-markdown 提交正文，单独 publish
halo post import-markdown --file "文章.md" --force
halo post update <uuid> --publish true

# 验证 heading 级别正确
halo post get <uuid> --json | python3 -c "
import sys, json
c = json.load(sys.stdin)['content']['raw']
for l in c.split('\n'):
    if l.startswith('#'): print(l.strip())
"
# → ## 章节（正确），### 子节（正确）
```

## 验证渲染（curl）

```bash
curl -s "https://jia.baoyu2023.top/archives/<slug>?nocache=1" | python3 -c "
import sys, re
html = sys.stdin.read()
for tag in ['h1','h2','h3']:
    items = re.findall(rf'<{tag}[^>]*>(.*?)</{tag}>', html)
    for item in items:
        txt = re.sub(r'<[^>]+>', '', item).strip()
        if txt: print(f'<{tag}> {txt}')
"
```

期望输出：
- 1 个 H1（页面标题） + 7 个 H2（章节） + 6 个 H3（子节）
