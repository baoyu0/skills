When the user gives a non-trivial task (multi-step, multi-file, needs verification), use this workflow:

1. **Phase 1 — Inform**: Briefly tell the user "I'll plan → execute → verify → handoff"
2. **Phase 2 — Plan**: Break into bite-sized tasks (2-5 min each), save to `.hermes/plans/`
3. **Phase 3 — Execute**: Dispatch subagents per task with spec + quality reviews
4. **Phase 4 — Verify**: Run tests, check completeness
5. **Phase 5 — Handoff**: Save handoff doc for cross-session continuity

Simple tasks (single file edit, typo fix) execute directly without the workflow.
