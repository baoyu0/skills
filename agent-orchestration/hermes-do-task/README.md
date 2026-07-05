# hermes-do-task-skill

> One-shot task runner for Hermes Agent: **plan → execute → verify → handoff**.

A lightweight orchestration skill that chains four existing Hermes skills into a single workflow:

- [`plan`](https://hermes-agent.nousresearch.com) / `writing-plans` — write implementation plans
- `subagent-driven-development` — execute via delegate_task subagents with 2-stage review
- `handoff` — save cross-session continuity doc

## How It Works

When you give a non-trivial task (multi-step, multi-file, needs verification), this skill automatically:

1. **Plan** — Breaks down into bite-sized tasks, writes to `.hermes/plans/`
2. **Execute** — Dispatches fresh subagents per task with spec + quality review gates
3. **Verify** — Final validation and test run
4. **Handoff** — Generates handoff doc for next session

Simple tasks (single file edit, typo fix) skip the workflow and execute directly.

## Install

```bash
npx skills add baoyu0/hermes-do-task-skill -g -y
```

Or clone into your Hermes skills directory:

```bash
git clone https://github.com/baoyu0/hermes-do-task-skill.git \
  ~/AppData/Local/hermes/skills/software-development/do-task
```

## Requirements

- Hermes Agent (any provider — works with opencode-go, Anthropic, OpenAI, etc.)
- Skills already loaded: `plan`, `writing-plans`, `subagent-driven-development`, `handoff`

All four are included with the standard Hermes Agent installation under `software-development/`.

## Compatibility

| Agent | Support |
|-------|---------|
| Hermes Agent | ✅ Native (SKILL.md) |
| Claude Code | Via CLAUDE.md |
| Codex | Via AGENTS.md |

## License

MIT
