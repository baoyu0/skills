# AGENTS.md — X-Clip-Purify

X/Twitter 剪藏文章标准化 — 剥离平台 UI 噪音、清理元数据、优化 alt 文本、检测结构化 prompt。

## 前置

- Python 脚本 `scripts/x-clip-purify.py`：`detect` / `clean` / `title` / `video`
- 路径用于 obsidian-halo pipeline 上游预处理

---

## CLI 命令

```bash
python x-clip-purify.py detect "文件.md"     # 检测文章来源（X / Twitter / 其他）
python x-clip-purify.py clean "文件.md"       # 直接修改文件：剥离元数据 + 清理自介 + 清理空 section + 优化 alt + 检测 prompt
python x-clip-purify.py title "文件.md" "新标题"  # 重写标题 + 同步更新 slug
python x-clip-purify.py video "文件.md"       # 清理 <video>/<audio> blob 标签
```

## clean 子命令清理项

- 剥离 X 线程元数据（回复/引用/@用户名/时间戳/点赞数/AI 生成/视频时长）
- 清理作者推广自介（我是/做过/关注/查看更多）
- 删除空 section 标题（`## ：`）
- 优化图片 alt 文本：`![图像]` → 从上下文推断描述
- 检测结构化 prompt 标记（【风格】/【场景】/【角色】/时间码）

## 和 obsidian-halo 的关系

```
X 原始剪藏 → x-clip-purify（本 skill）→ obsidian-halo pipeline
```

本 skill 接管 obsidian-halo 原先在 Phase 3 中手动做的「X 剪藏必做 cleanup」，将其自动化、独立化。
