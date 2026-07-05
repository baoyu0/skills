# obsidian-halo-skill

> 一个兼容 Hermes / Claude Code / Codex 的多 agent 工作流，自动将 Obsidian 剪藏文章发布到 Halo 博客，含 AI 排版优化。

## 文件结构

```
├── SKILL.md            # Hermes Agent skill 格式
├── CLAUDE.md           # Claude Code 指令
├── AGENTS.md           # Codex / OpenCode 指令
├── INSTRUCTIONS.md     # 规范流程（所有 agent 通用）
├── scripts/
│   └── halo-publish.py # 核心脚本（3 模式）
└── references/
    ├── halo-api-notes.md
    ├── halo-publish-script.md
    └── hermes-docs-theme.md
```

## 配置

```bash
# 1. 创建配置文件
cat > ~/.hermes/halo-config.json << 'EOF'
{
  "pat": "你的Halo PAT",
  "site": "https://你的博客.com"
}
EOF

# 2. 安装依赖
pip install markdown-it-py requests PyYAML
```

## 使用

```bash
# Phase 1: 裸文上传（Halo 自动配封面）
python scripts/halo-publish.py create "文章.md"

# Phase 2: 拉回 Halo frontmatter
sleep 15
python scripts/halo-publish.py pull "文章.md"

# Phase 3: AI 完善（手工执行，参考 INSTRUCTIONS.md）

# Phase 4: 推送更新
python scripts/halo-publish.py update "文章.md"
```

## Agent 兼容性

| Agent | 入口文件 | 状态 |
|-------|---------|------|
| Hermes Agent | `SKILL.md` | ✅ 自动加载 |
| Claude Code | `CLAUDE.md` | ✅ 项目级指令 |
| Codex CLI | `AGENTS.md` | ✅ 自动读取 |
| OpenCode | `AGENTS.md` | ✅ 兼容 |
| Cursor | `.cursorrules` | 可手动引用 |

## 许可

MIT
