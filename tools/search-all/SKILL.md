---
name: search-all
version: 1.0.0
description: "全源检索 — 一次搜索 Obsidian + Halo 博客 + Hermes 配置。用户输入 `search-all <关键词>` 触发。"
---

# search-all — 全源检索

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

## 触发条件

用户说「帮我找xxx」「搜一下xxx」「xxx在哪」「之前我们聊过xxx」时，优先走本 skill。

## 执行流程

### 用户可自搜（CLI）

```bash
search-all <关键词>              # 所有源
search-all obsidian <关键词>     # Obsidian 只
search-all halo <关键词>         # 博客只
search-all config <关键词>       # 配置只
search-all help                  # 帮助
```

### Agent 补充搜索（我负责）

CLI 搜不到的文件级源需要我手动查：

1. **session DB** → `session_search(query="xxx")`
2. **fact_store** → `fact_store(action="search", query="xxx")`
3. **memory** → 查看 target='memory' 和 target='user' 的现有条目

### 最佳实践

1. 用户问 xxx 相关 → 先 `search-all xxx` 快速覆盖文件级源
2. 再补 `session_search` + `fact_store` 覆盖 Agent 源
3. 合成结果后给用户一个「从哪找到的」摘要

## 配置

脚本支持通过环境变量自定义路径：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SEARCH_ALL_OBSIDIAN` | `D:\1-obsidian` | Obsidian Vault 路径 |
| `SEARCH_ALL_HALO_API` | `https://jia.baoyu2023.top/...` | Halo API 地址 |
| `SEARCH_ALL_HERMES` | `%LOCALAPPDATA%\hermes` | Hermes 数据目录 |

示例：
```bash
export SEARCH_ALL_OBSIDIAN="D:/MyVault"
export SEARCH_ALL_HALO_API="https://blog.example.com/apis/api.content.halo.run/v1alpha1/posts"
```

## 注意事项

- **Windows 路径**：Python subprocess 用 cmd.exe 不认识正斜杠（`D:/`），所以脚本用反斜杠（`D:\`）
- **grep 限制**：每文件最多返回 3 行匹配，避免输出爆炸
- **Halo API**：使用公开 API，无需鉴权，但关键词已做 URL 编码（支持中文/特殊字符）
- **Agent 专属源**：session DB / memory / fact_store 只能由 Agent 在对话中搜索，不可通过 CLI 直接访问
