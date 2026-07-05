#!/usr/bin/env bash
# Hermes Memory Sync — load/save/search Hermes memory from any AI agent
# Usage:
#   ./hermes-sync.sh load              # Print all Hermes memory sources
#   ./hermes-sync.sh save "content" "cat" "tags"  # Save a fact
#   ./hermes-sync.sh search "keyword"   # Full-text search facts
#   ./hermes-sync.sh status            # Show memory status

set -euo pipefail

detect_hermes_dir() {
  if [ -n "${HERMES_DIR:-}" ] && [ -d "$HERMES_DIR" ]; then
    echo "$HERMES_DIR"; return 0
  fi
  [ -d "$HOME/.local/share/hermes" ] && echo "$HOME/.local/share/hermes" && return 0
  [ -n "${LOCALAPPDATA:-}" ] && [ -d "$LOCALAPPDATA/hermes" ] && echo "$LOCALAPPDATA/hermes" && return 0
  [ -d "$HOME/Library/Application Support/hermes" ] && echo "$HOME/Library/Application Support/hermes" && return 0
  [ -d "$HOME/.hermes" ] && echo "$HOME/.hermes" && return 0
  echo ""; return 1
}

HERMES_DIR=$(detect_hermes_dir)

cmd_load() {
  [ -z "$HERMES_DIR" ] && echo "Hermes not found." && exit 1
  echo "=== Hermes Memory Bridge ==="
  echo "Source: $HERMES_DIR"

  USER_MD="$HERMES_DIR/memories/USER.md"
  [ -f "$USER_MD" ] && echo "" && echo "-- USER.md --" && wc -l < "$USER_MD" | xargs printf "  %s lines\n" && cat "$USER_MD"

  DB="$HERMES_DIR/memory_store.db"
  if [ -f "$DB" ]; then
    echo "" && echo "-- Fact Store (top 15) --"
    sqlite3 "$DB" -readonly "SELECT printf('  [%s] %s', category, substr(content,1,120)) FROM facts ORDER BY helpful_count DESC, trust_score DESC LIMIT 15;" 2>/dev/null || echo "  (unable to query)"
  fi
}

cmd_save() {
  [ -z "$HERMES_DIR" ] && echo "Hermes not found." && exit 1
  local content="${1:?content required}"
  local category="${2:-general}"
  local tags="${3:-}"
  DB="$HERMES_DIR/memory_store.db"
  [ ! -f "$DB" ] && echo "No memory_store.db" && exit 1
  sqlite3 "$DB" "INSERT OR IGNORE INTO facts (content, category, tags, trust_score) VALUES ('$(echo "$content" | sed "s/'/''/g")', '$category', '$tags', 0.5);"
  echo "Saved: ${content:0:60}..."
  if [ "$category" = "user_pref" ]; then
    USER_MD="$HERMES_DIR/memories/USER.md"
    [ -f "$USER_MD" ] && echo "" >> "$USER_MD" && echo "$content" >> "$USER_MD" && echo "Also appended to USER.md"
  fi
  [ -f "$HOME/Memory.md" ] && ! grep -Fq "$content" "$HOME/Memory.md" 2>/dev/null && echo "" >> "$HOME/Memory.md" && echo "$content" >> "$HOME/Memory.md" && echo "Also synced to ~/Memory.md"
}

cmd_search() {
  [ -z "$HERMES_DIR" ] && echo "Hermes not found." && exit 1
  local query="${1:?search query required}"
  DB="$HERMES_DIR/memory_store.db"
  [ ! -f "$DB" ] && echo "No memory_store.db" && exit 1
  sqlite3 "$DB" -readonly "SELECT printf('  [%.2f] %s', rank, substr(content,1,120)) FROM facts_fts WHERE facts_fts MATCH '\"$query\"' ORDER BY rank LIMIT 10;" 2>/dev/null
}

cmd_status() {
  [ -z "$HERMES_DIR" ] && echo "Hermes not found." && exit 1
  echo "Hermes Memory Status"
  echo "Directory: $HERMES_DIR"
  for f in "memories/MEMORY.md" "memories/USER.md"; do
    [ -f "$HERMES_DIR/$f" ] && printf "  %-20s %d lines\n" "$f" "$(wc -l < "$HERMES_DIR/$f")" || printf "  %-20s not found\n" "$f"
  done
  DB="$HERMES_DIR/memory_store.db"
  if [ -f "$DB" ]; then
    echo "  memory_store.db     present"
    sqlite3 "$DB" -readonly "SELECT printf('    %s: %d', category, count(*)) FROM facts GROUP BY category;" 2>/dev/null
  fi
}

case "${1:-help}" in
  load)    cmd_load ;;
  save)    shift; cmd_save "$@" ;;
  search)  shift; cmd_search "$@" ;;
  status)  cmd_status ;;
  *)       echo "Usage: hermes-sync.sh <load|save|search|status>" ;;
esac
