# `halo post update --content` 吞 `#` 陷阱

## 现象

用 `halo post update <uuid> --content "正文markdown"` 更新文章后：
- `## 章节标题` → 页面渲染为 `<h1>`（而非 `<h2>`）
- `### 子节` → 页面渲染为 `<h2>`（而非 `<h3>`）
- TOC 错乱：H2 章节从 TOC 消失，H3 子节升级为 TOC 顶级条目

## 根因

Halo 的 `update` API 经过内容处理管道时，每条 markdown heading 会**减少一级 `#`**。这是 Halo 服务端行为，与客户端编码无关。

## 修复方案

**永远不用 `--content` 提交含 heading 的正文。** 改用两步走：

```bash
# 1. 用 import-markdown 提交内容（保留 heading 级别）
halo post import-markdown --file "<文件路径>" --force

# 2. 单独发布（不传 --content）
halo post update <UUID> --publish true
```

## 验证方法

发布后检查 heading 级别是否被吞：

```bash
halo post get <UUID> --json 2>&1 | python3 -c "
import sys, json
c = json.load(sys.stdin)['content']['raw']
for l in c.split(chr(10)):
    if l.startswith('#'): print(l.strip())
"
```

期望输出：heading 级别与本地文件一致（`##`/`###`/`####` 保持原样）。

## 例外情况

只有当你确认正文**不含任何 markdown heading**（纯段落文本）时，才可以用 `--content`。即便如此，也优先走 `import-markdown`。
