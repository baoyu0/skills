# CLAUDE.md — baoyu0/skills

This is a monorepo of reusable AI agent skills. Each skill lives in a category subdirectory with its own `SKILL.md`.

To load a skill:

```
@skills methodology/code-assembly
@skills agent-orchestration/hermes-do-task
```

Or reference the file directly:
```
read_file skills/methodology/code-assembly/SKILL.md
```

Or the Hermes memory bridge:
```
@skills integration/hermes-memory-bridge
```
Or:
```
read_file skills/integration/hermes-memory-bridge/SKILL.md
```
