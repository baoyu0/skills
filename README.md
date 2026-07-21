# 宝藏技能 · baoyu0's skills

个人 AI Agent 技能合集。每个 skill 封装一个可复用的工作流，供 **Hermes Agent**、**Claude Code**、**Codex**、**OpenCode**、**pi** 等 AI 编程 agent 加载使用。

📦 **9 skills** · 8 个分类 · 配套 CLI 工具 · MIT 许可

---

## 快速安装

```bash
# Hermes — skill 已预装在本地，直接用 skill_view()
skill_view(name='tools/search-all')

# npx skills CLI（Claude Code / Codex / OpenCode 通用）
npx skills add baoyu0/skills@tools/search-all -g -y
npx skills add baoyu0/skills@network/karing-routing -g -y
npx skills add baoyu0/skills@content-publishing/x-clip-purify -g -y
```

---

## 分类

### 方法论 (methodology)

| Skill | 说明 | 加载 |
|-------|------|------|
| [code-assembly](methodology/code-assembly/) | **拼好码** — AI 编程的整合者心态。能复用时不重造，能编排时不发明。 | `skill_view(name='code-assembly')` |

### Agent 编排 (agent-orchestration)

| Skill | 说明 | 加载 |
|-------|------|------|
| [hermes-do-task](agent-orchestration/hermes-do-task/) | 一键任务执行：plan → subagent execute → verify → handoff | `skill_view(name='hermes-do-task')` |

### 内容发布 (content-publishing)

| Skill | 说明 | CLI | 加载 |
|-------|------|-----|------|
| [obsidian-halo](content-publishing/obsidian-halo/) | Obsidian → Halo 博客发布，含 AI 优化排版六阶段流水线 | `halo post import-markdown` | `skill_view(name='content-publishing/obsidian-halo')` |
| [x-clip-purify](content-publishing/x-clip-purify/) | **X 剪藏标准化** — 剥离元数据、清理自介、检测结构化 prompt | `x-clip-purify clean <file>` | `skill_view(name='content-publishing/x-clip-purify')` |

### 媒体处理 (media)

| Skill | 说明 | 加载 |
|-------|------|------|
| [subtitle-edit](media/subtitle-edit/) | Subtitle Edit CLI 操作：格式转换、时间偏移、帧率修正 | `skill_view(name='media/subtitle-edit')` |

### 网络代理 (network)

| Skill | 说明 | CLI | 加载 |
|-------|------|-----|------|
| [karing-routing](network/karing-routing/) | Karing 路由规则管理 — 添加直连域名、诊断代理故障、重启服务 | `karing-route add <路由组> <域名>` | `skill_view(name='network/karing-routing')` |

### 跨 Agent 集成 (integration)

| Skill | 说明 | 加载 |
|-------|------|------|
| [hermes-memory-bridge](integration/hermes-memory-bridge/) | 桥接 Hermes 桌面端记忆系统到其他 AI Agent。让 pi / Claude Code / Codex 也能读取 Hermes 的 USER.md 用户画像和结构化事实库。 | `skill_view(name='integration/hermes-memory-bridge')` |

### 工具 (tools)

| Skill | 说明 | CLI | 加载 |
|-------|------|-----|------|
| [search-all](tools/search-all/) | **全源检索** — 一次搜索 Obsidian + Halo 博客 + Hermes 配置，破数据孤岛 | `search-all <关键词>` | `skill_view(name='tools/search-all')` |

### 开发环境 (development)

| Skill | 说明 | 加载 |
|-------|------|------|
| [windows-triage](development/windows-triage/) | **Windows 故障诊断** — Insider 25H2 错误码速查、诊断决策树、已知回归清单 | `skill_view(name='development/windows-triage')` |

---

## 使用方式

### Hermes Agent

所有 skill 已预装在本地的 `%LOCALAPPDATA%/hermes/skills/`。

```bash
# 在对话中加载
skill_view(name='tools/search-all')
skill_view(name='network/karing-routing')
skill_view(name='content-publishing/x-clip-purify')
skill_view(name='development/windows-triage')

# CLI 工具（Python 脚本 + shell wrapper）
search-all "AI Agent"
karing-route list
x-clip-purify clean "文章.md" --dry-run
```

### Claude Code / Codex / OpenCode

```bash
# 方法一：通过 npx skills CLI 安装
npx skills add baoyu0/skills@tools/search-all -g -y
npx skills add baoyu0/skills@network/karing-routing -g -y

# 方法二：在项目根目录放 CLAUDE.md / AGENTS.md 引用
# 文件内容示例：
# > 加载 baoyu0/code-assembly 方法论 skill
```

### pi

```bash
# 自动发现 ~/.pi/agent/skills/
/skill:hermes-memory-bridge
```

### 开发者：将 skill 加入你的项目

```bash
git clone https://github.com/baoyu0/skills.git
cp -r skills/path/to/skill-name /path/to/your/agent/skills/
```

---

## 仓库结构

```
baoyu0/skills/
├── methodology/              → code-assembly
├── agent-orchestration/      → hermes-do-task
├── content-publishing/       → obsidian-halo, x-clip-purify
├── media/                    → subtitle-edit
├── network/                  → karing-routing
├── integration/              → hermes-memory-bridge
├── tools/                    → search-all
├── development/              → windows-triage
├── README.md
├── LICENSE
├── AGENTS.md
└── CLAUDE.md
```

每个 skill 目录包含：
- `SKILL.md` — Hermes Agent 格式的技能说明书
- `scripts/` — CLI 配套脚本（Python + shell wrapper）
- `references/` — 参考文档与陷阱记录（大型 skill 可选）

---

## License

MIT
