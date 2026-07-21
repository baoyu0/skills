# AGENTS.md — search-all 全源检索

一次搜索 Obsidian Vault + Halo 博客 + Hermes 配置。当用户说「帮我找xxx」「搜一下xxx」「xxx在哪」「之前我们聊过xxx」时触发。

## 前置

- Python 脚本 `scripts/search-all.py`，部署到 `~/bin/search-all`
- 覆盖三个文件级知识源，Agent 专属源由对话补齐

---

## CLI 使用

```bash
search-all <关键词>               # 所有源
search-all obsidian <关键词>      # Obsidian 只
search-all halo <关键词>          # 博客只
search-all config <关键词>        # 配置只
search-all help                   # 帮助
```

## 检索覆盖

| 源 | 范围 | 方式 |
|----|------|------|
| Obsidian Vault | `D:\1-obsidian` 全部 `.md` | `grep -rn` |
| Halo 博客 | jia.baoyu2023.top 已发布文章 | `curl` 公开 API |
| Hermes 配置 | `~/.hermes/`, `%LOCALAPPDATA%/hermes/`, `.bashrc` | `grep -rn` |

## Agent 补充搜索（对话中手工补）

CLI 搜不到的 Agent 专属源：

1. Session DB → `session_search(query="关键词")`
2. fact_store → `fact_store(action="search", query="关键词")`
3. memory → 查看现有条目

## 最佳实践工作流

1. 用户问 xxx → 先 `search-all xxx` 快速覆盖文件级源
2. 再补 `session_search` + `fact_store` 覆盖 Agent 源
3. 合成结果给用户「从哪找到的」摘要

## 注意事项

- Windows 路径用反斜杠（`D:\`），非正斜杠
- grep 每文件最多 3 行匹配，避免输出爆炸
- Halo API 公开无需鉴权，关键词自动 URL 编码
- Session DB / memory / fact_store 只能由 Agent 在对话中搜索，不可通过 CLI 直接访问
