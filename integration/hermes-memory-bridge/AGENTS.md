# AGENTS.md — Hermes Memory Bridge

Cross-agent memory integration — make every AI agent benefit from Hermes Desktop's continuous learning. Bridges Hermes's three memory layers into non-Hermes agents.

## 前置

- Hermes Agent Desktop 已安装
- `sqlite3` CLI 在 PATH 中
- 无 Hermes 时优雅降级

---

## Hermes 记忆架构

```
%LOCALAPPDATA%/hermes/  (Windows) / ~/.local/share/hermes/  (Linux) / ~/Library/ (macOS)
├── memories/
│   ├── MEMORY.md         ← 系统/工具/环境记忆（大多数 Agent 已读 ~/Memory.md）
│   └── USER.md           ← 用户画像、偏好、个性（非 Hermes Agent 遗漏）
└── memory_store.db        ← 结构化事实库（FTS5 全文搜索），含 ~60+ 事实
```

## 加载用户画像（USER.md）

```bash
HERMES_DIR="${LOCALAPPDATA}/hermes"  # Windows, 其他平台见上
[ -f "${HERMES_DIR}/memories/USER.md" ] && cat "${HERMES_DIR}/memories/USER.md"
```

关键信息：沟通风格、决策模式、技术环境、工作偏好、Do's/Don'ts。

## 查询事实库

```bash
# 最近高价值事实
sqlite3 "${HERMES_DIR}/memory_store.db" -readonly "SELECT content FROM facts WHERE trust_score >= 0.5 ORDER BY helpful_count DESC LIMIT 15;"

# 按分类查询
sqlite3 "${HERMES_DIR}/memory_store.db" -readonly "SELECT content FROM facts WHERE category = 'user_pref' ORDER BY updated_at DESC LIMIT 20;"

# 全文搜索
sqlite3 "${HERMES_DIR}/memory_store.db" -readonly "SELECT content, rank FROM facts_fts WHERE facts_fts MATCH '\"<关键词>\"' ORDER BY rank LIMIT 10;"
```

## 双向同步

**加载时：** 读 USER.md 注入偏好 + 查询高价值事实 + 关键词命中时 FTS 搜索。

**写入时：** 学到新知识时同时写入 Hermes（`memory_store.db` + `USER.md`）和 `~/Memory.md`。

## 辅助脚本

```bash
bash scripts/hermes-sync.sh load              # 加载全部 Hermes 记忆
bash scripts/hermes-sync.sh save "内容" "分类" "标签1,标签2"  # 保存事实
bash scripts/hermes-sync.sh search "关键词"     # 搜索记忆
```

## 跨平台路径

| 平台 | 路径 |
|------|------|
| Windows | `%LOCALAPPDATA%\hermes\` |
| Linux | `~/.local/share/hermes/` |
| macOS | `~/Library/Application Support/hermes/` |
