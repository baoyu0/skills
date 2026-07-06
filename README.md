# 宝藏技能 · baoyu0's skills

个人 AI Agent 技能合集。每个 skill 封装一个可复用的工作流，供 Hermes、Claude Code、Codex、OpenCode 等 AI 编程 agent 加载使用。

## 分类

### 方法论 (methodology)
| Skill | 说明 |
|---|---|
| [code-assembly](methodology/code-assembly/) | **拼好码** — AI 编程的整合者心态。能复用时不重造，能编排时不发明。 |

### Agent 编排 (agent-orchestration)
| Skill | 说明 |
|---|---|
| [hermes-do-task](agent-orchestration/hermes-do-task/) | 一键任务执行：plan → subagent execute → verify → handoff |

### 内容发布 (content-publishing)
| Skill | 说明 |
|---|---|
| [obsidian-halo](content-publishing/obsidian-halo/) | Obsidian → Halo 博客发布，含 AI 优化排版流水线 |

### 媒体处理 (media)
| Skill | 说明 |
|------|------|
| [subtitle-edit](media/subtitle-edit/) | Subtitle Edit CLI 操作：格式转换、时间偏移、帧率修正 |

### 跨 Agent 集成 (integration)
| Skill | 说明 |
|---|---|
| [hermes-memory-bridge](integration/hermes-memory-bridge/) | 桥接 Hermes 桌面端记忆系统到其他 AI Agent。让 pi / Claude Code / Codex 也能读取 Hermes 的 USER.md 用户画像和结构化事实库，实现双向记忆同步 |

### 网络代理 (network)
| Skill | 说明 |
|------|------|
| [karing-routing](network/karing-routing/) | Karing 路由规则管理 — 添加直连域名、诊断代理故障、重启服务。`karing-route add <路由组> <域名>` |

### 工具 (tools)
| Skill | 说明 |
|------|------|
| [search-all](tools/search-all/) | **全源检索** — 一次搜索 Obsidian + Halo 博客 + Hermes 配置，破数据孤岛 |

## 使用方式

### Hermes Agent

```bash
skill_view(name='code-assembly')
skill_view(name='hermes-do-task')
skill_view(name='content-publishing/obsidian-halo')
```

### Claude Code / Codex

```bash
# 在项目根目录放 CLAUDE.md / AGENTS.md，或在对话中引用
```

### pi

```bash
# Auto-discovered from ~/.pi/agent/skills/
/skill:hermes-memory-bridge
```

## License

MIT
