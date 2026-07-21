---
name: x-clip-purify
version: 1.0.0
description: "X/Twitter 剪藏文章标准化 — 剥离元数据、清理自介、检测结构化 prompt、优化 alt 文本。"
---

# X-Clip-Purify — X 剪藏标准化

## 问题

从 X/Twitter 剪藏的文章含有大量平台 UI 噪音：

| 噪声类型 | 例子 |
|---------|------|
| 线程回复元数据 | `发布你的回复`、`引用`、`@用户名`、时间戳、点赞数 |
| 作者自介 | `我是 xxx，做过 xx，关注我查看更多` |
| 空 section | `## ：`（断章标题）、`没有项目` |
| 标题机器化 | `X 上的 某某：完整推文` |
| 图片无描述 | `![图像]`、`![]()` |
| 视频嵌入 | `<video>`/`<audio>` blob: 标签 |
| 平台 UI 残留 | `由 AI 生成`、`0:05 / 0:32` |

## 执行流程

### 第一步：检测文章来源

```bash
python x-clip-purify.py detect "文件.md"
# → X / Twitter / 其他
```

### 第二步：执行清理（直接修改文件）

```bash
python x-clip-purify.py clean "文件.md"
```

完成以下清理：

1. **剥离 X 线程元数据**：删除所有 `发布你的回复`、`引用`、`@用户名`、时间戳、点赞数、`由 AI 生成`、视频时长标签
2. **清理作者自介**：全文扫描并删除 `我是……`、`做过`、`关注`、`查看更多` 等推广文本（不限 blockquote 或正文）
3. **清理空 section**：删除内容为空的 `## ：` 标题及其后的空段落
4. **优化图片 alt 文本**：`![图像]` → 从上下文推断描述
5. **检测结构化 prompt**：如果文章含 `【风格】`/`【场景】`/`【角色】` 或 `[00:00-00:XX]` → 标记

### 第三步：标题重写（如需）

```bash
python x-clip-purify.py title "文件.md" "新标题"
```

- 将 `X 上的 某某：xxx` 重写为人类可读标题
- 同步更新 slug（自动生成）

### 第四步：视频标签清理

```bash
python x-clip-purify.py video "文件.md"
```

- `<video>`/`<audio>` blob: 标签 → 替换为 poster 封面图链接
- 删除视频时间戳行

## 输出示例

```
$ python x-clip-purify.py clean "X 上的 某某文章.md"
📋 X-Clip-Purify 清理报告
─────────────────────
✅ 剥离 X 元数据: 7 处
✅ 删除作者自介: 1 处
✅ 清理空 section: 2 处
✅ 优化 alt 文本: 3 处
⚠️ 检测到结构化 prompt：含【风格】【场景】标记
   建议手动拆分为独立 code blocks
─────────────────────
文章已清理，可进入 obsidian-halo pipeline
```

## 和 obsidian-halo 的关系

```
X 原始剪藏
    │
    ▼
x-clip-purify （本 skill：剥离噪音 + 标准化）
    │
    ▼
obsidian-halo Phase 1~5 （上传 + heading + 排版 + 发布）
```

本 skill 接管 obsidian-halo 原先在 Phase 3 中手动做的「X 剪藏必做 cleanup」部分，将其自动化、独立化，减少 obsidian-halo 管线的 token 消耗和人工判断步骤。
