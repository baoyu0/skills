# obsidian-halo-skill

> 多 agent 工作流：将 Obsidian 剪藏文章发布到 Halo 博客，含 AI 排版优化。

## 文件结构

```
├── SKILL.md            # 完整工作流（6 阶段）
├── CLAUDE.md           # Claude Code 精简指令
├── AGENTS.md           # Codex / OpenCode 精简指令
├── scripts/
│   ├── auto-number.py      # 自动编号 H2/H3 标题
│   ├── halo-publish.py     # 核心脚本（detect/cleanup/verify）
│   ├── halo-migrate-images.py  # 外部图片迁移
│   └── verify-article.py   # 文章完整性验证
├── references/         # 24 个参考文档
└── evals/
    └── results.tsv     # 历史基线评估
```

## 前置

- `@halo-dev/cli` v1.3.0+（`npm install -g @halo-dev/cli`）
- 配置文件 `~/.hermes/halo-config.json`（PAT + site URL）

## 快速开始

完整工作流见 `SKILL.md`。核心流程：

1. **上传原始文件** → `halo post import-markdown --file "path.md" --force`
2. **拉回 frontmatter** → `halo post export-markdown <UUID> --output "path.md"`
3. **内容处理** → cleanup + auto-number + AI 排版
4. **更新发布** → `halo post import-markdown --file "path.md" --force` + `halo post update <UUID> --publish true`

> ⚠️ **禁止用 `halo post update --content`** — 会吞掉 heading 级别。

## Agent 兼容性

| Agent | 入口文件 | 说明 |
|-------|---------|------|
| Hermes Agent | `SKILL.md` | `skill_view(name='content-publishing/obsidian-halo')` |
| Claude Code | `CLAUDE.md` | 项目级指令 |
| Codex CLI | `AGENTS.md` | 自动读取 |
| OpenCode | `AGENTS.md` | 兼容 |

## 许可

MIT
