---
name: search-all
description: "全源检索工具 — 一次搜索 Obsidian Vault + Halo 博客 + Hermes 配置。破数据孤岛。"
---

# search-all — 全源检索 Skill

## 问题

你有四个知识容器：Obsidian vault、Halo 博客、Hermes session DB、memory/fact_store。它们各自为政，找东西要先想「这在我哪个仓库里」。重复调研的概率随着知识积累指数增长。

## 解决方案

`search-all` 脚本统一检索三个文件级源，Agent 专属源由我（Hermes agent）在对话中补齐。

| 源 | 覆盖范围 | 实现 |
|----|---------|------|
| 📄 Obsidian Vault | `D:\1-obsidian` 下全部 `.md` 文件 | `grep -rn` |
| 📝 Halo 博客 | jia.baoyu2023.top 已发布的全部文章 | `curl` Halo 公开 API |
| ⚙ Hermes 配置 | `~/.hermes/`, `%LOCALAPPDATA%/hermes/`, `.bashrc` | `grep -rn` |
| 💬 Session DB | 历史对话 | 对我说「帮我搜 session 里关于 xxx 的内容」 |
| 🧠 Memory / fact_store | 持久化记忆 | 对我说「帮我搜 memory 里关于 xxx 的内容」 |

## 安装

```bash
# 1. 复制脚本
cp scripts/search-all.py ~/bin/
cp scripts/search-all.sh ~/bin/search-all
chmod +x ~/bin/search-all

# 2. 确保 ~/bin 在 PATH 中（默认已在）
```

## 用法

```bash
search-all <关键词>              # 同时搜所有文件级源
search-all obsidian <关键词>     # 只搜 Obsidian
search-all halo <关键词>         # 只搜博客
search-all config <关键词>       # 只搜 Hermes 配置
search-all help                  # 帮助
```

## 示例

```bash
# 搜所有源
search-all "AI Agent"
# → Obsidian: 23 个文件命中
# → Halo: 21 篇文章匹配
# → Config: 3 个配置文件

# 搜 Agent 专属源（直接对我说）
# 「帮我搜 session 里关于 Agentic Engineering 的内容」
# 「帮我搜 fact_store 里关于 Karing 路由的内容」
```

## 注意事项

- **Windows 路径**：Python subprocess 用 cmd.exe 不认识正斜杠（`D:/`），所以脚本用反斜杠（`D:\`）
- **grep 限制**：每文件最多返回 3 行匹配，避免输出爆炸
- **Halo API**：使用公开 API，无需鉴权，但受限于 Halo 的分页和关键词匹配算法
- **Agent 专属源**：session DB / memory / fact_store 只能由 Agent 在对话中搜索，不可通过 CLI 直接访问
