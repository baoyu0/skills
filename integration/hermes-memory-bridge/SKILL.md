---
name: hermes-memory-bridge
description: >
  Bridges Hermes Agent Desktop's rich memory system into other AI coding agents
  (pi, Claude Code, Codex, Cline, etc.). Hermes maintains THREE memory layers
  across sessions: MEMORY.md (system/tool memory), USER.md (user profile),
  and memory_store.db (structured facts with FTS5 search).
  Other agents typically only read ~/Memory.md, missing the USER.md profile
  and structured fact store. This skill fills that gap: loads what other agents
  don't see, and provides bidirectional sync so all agents stay in sync.
  Triggers on: "memory bridge", "Hermes memory", "cross-agent memory",
  "同步记忆", "记忆桥接", "hermes-memory-bridge".
compatibility: >
  Hermes Agent Desktop installed. sqlite3 CLI in PATH for DB queries.
  Graceful degradation if Hermes is not installed.
---

# Hermes Memory Bridge

Cross-agent memory integration — make every AI agent benefit from Hermes Desktop's continuous learning.

## Hermes Memory Architecture

```
~/.local/share/hermes/ (Linux)    ← primary path
%LOCALAPPDATA%/hermes/ (Windows)
~/Library/Application Support/hermes/ (macOS)
├── memories/
│   ├── MEMORY.md        ← System/tool/environment memory
│   └── USER.md          ← User profile, preferences, personality
├── memory_store.db       ← Structured facts with FTS5 full-text search
│   (tables: facts, entities, fact_entities, memory_banks)
└── hermes-agent/
    └── skills/           ← Hermes' own installed skill library
```

### What Most Agents Already Get

- **`~/Memory.md`** — Hermes writes its merged memory here; most agents (pi, Claude Code via CLAUDE.md, Codex) read it at startup

### What This Skill Adds

| Source | Content | Size | Previously Missed By |
|--------|---------|------|---------------------|
| `USER.md` | Communication style, personality, do's/don'ts | ~130 lines | All non-Hermes agents |
| `memory_store.db` | Structured facts with trust scores, categories, FTS5 search | ~60+ facts | All non-Hermes agents |

## Locating Hermes Data

Auto-detect the Hermes data directory:

```bash
# Best-effort auto-detect (returns first found)
if [ -d "$HOME/.local/share/hermes" ]; then
  HERMES_DIR="$HOME/.local/share/hermes"
elif [ -n "$LOCALAPPDATA" ] && [ -d "$LOCALAPPDATA/hermes" ]; then
  HERMES_DIR="$LOCALAPPDATA/hermes"
elif [ -d "$HOME/Library/Application Support/hermes" ]; then
  HERMES_DIR="$HOME/Library/Application Support/hermes"
else
  echo "Hermes not found"
  HERMES_DIR=""
fi
```

## Loading User Profile

Read USER.md to understand the user's interaction patterns:

```bash
USER_MD="${HERMES_DIR}/memories/USER.md"
[ -f "$USER_MD" ] && cat "$USER_MD"
```

Key insights typically found in USER.md:
- Communication style (concise/verbose, Chinese-first vs English)
- Decision-making patterns (root-cause-first, propose-confirm-execute)
- Technical environment (GPU, proxy, cloud accounts)
- Work preferences (tool reuse priority, upstream fix over workaround)
- Do's and don'ts

## Querying the Fact Store

```bash
# Recent high-value facts (sorted by helpfulness)
sqlite3 "${HERMES_DIR}/memory_store.db" -readonly "
SELECT content FROM facts
WHERE trust_score >= 0.5
ORDER BY helpful_count DESC, trust_score DESC
LIMIT 15;
"

# Facts by category
sqlite3 "${HERMES_DIR}/memory_store.db" -readonly "
SELECT content FROM facts WHERE category = 'user_pref' ORDER BY updated_at DESC LIMIT 20;
"
sqlite3 "${HERMES_DIR}/memory_store.db" -readonly "
SELECT content FROM facts WHERE category = 'tool' ORDER BY updated_at DESC LIMIT 20;
"

# Full-text search
sqlite3 "${HERMES_DIR}/memory_store.db" -readonly "
SELECT content, rank FROM facts_fts
WHERE facts_fts MATCH '\"<keyword>\"'
ORDER BY rank LIMIT 10;
"
```

## Bidirectional Sync

### Reading from Hermes (into current agent)

When this skill loads, it should:
1. Read `USER.md` and inject user preferences into context
2. Query `memory_store.db` for recent high-value facts
3. Use FTS5 search when the user asks about topics Hermes may have learned

### Writing back to Hermes (from current agent)

When the current agent learns something durable, keep Hermes in sync:

```bash
# Write a structured fact
sqlite3 "${HERMES_DIR}/memory_store.db" "
INSERT OR IGNORE INTO facts (content, category, tags, trust_score)
VALUES ('<fact content>', '<category>', '<tags>', 0.5);
"

# Append to USER.md for a lasting preference
echo "<preference>" >> "${HERMES_DIR}/memories/USER.md"
```

### Keep ~/Memory.md in Sync

```bash
echo "<new fact>" >> "$HOME/Memory.md"
```

### Helper Script

A one-shot sync script is provided at `scripts/hermes-sync.sh`:

```bash
# Load all Hermes memory into context
bash scripts/hermes-sync.sh load

# Save a new fact to Hermes
bash scripts/hermes-sync.sh save "content" "category" "tag1,tag2"

# Search Hermes memory
bash scripts/hermes-sync.sh search "keyword"
```

## Cross-Platform Notes

| Platform | Hermes Data Path | Notes |
|----------|-----------------|-------|
| Windows | `%LOCALAPPDATA%\hermes\` | Use `$LOCALAPPDATA` in git-bash/MSYS2 |
| Linux | `~/.local/share/hermes/` | Standard XDG path |
| macOS | `~/Library/Application Support/hermes/` | Standard macOS path |

The `memory_store.db` uses WAL mode — concurrent reads are safe as long as Hermes
is not in the middle of a write transaction. Use `-readonly` flag with sqlite3.

## Integration per Agent

### pi
Auto-discovered from `~/.pi/agent/skills/`. Load with `/skill:hermes-memory-bridge`.

### Claude Code
Load from `~/.claude/skills/` via `npx skills add baoyu0/skills -g -y`.

### Codex / Cline / OpenCode
Standard skill loading per the Agent Skills specification.
You can target the skill path as `integration/hermes-memory-bridge`.
