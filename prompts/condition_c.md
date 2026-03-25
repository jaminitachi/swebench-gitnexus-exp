# CLAUDE.md — Condition C (GitNexus Forced)

You are fixing a bug in a Django repository. The repository is in the current working directory.

## IMPORTANT: Code Navigation Rules

For this experiment, you MUST use `gitnexus` CLI for all code exploration and navigation.

### FORBIDDEN (for code exploration):
- `grep`, `rg`, `ag` — use `gitnexus query` instead
- `find` (for code files) — use `gitnexus query` instead
- `cat`, `head`, `tail`, `less` (for reading code) — use `gitnexus context --include-content` instead
- `tree`, `ls` (for browsing structure) — use `gitnexus query` instead

### ALLOWED:
- `gitnexus query` — search for code by concept
- `gitnexus context` — get symbol details with source code
- `gitnexus impact` — analyze change impact
- `gitnexus detect_changes` — review what your changes affect
- `gitnexus rename` — safe multi-file rename
- `gitnexus cypher` — custom graph queries
- `cd`, `pwd` — navigation
- `python`, `python3` — running tests
- `sed`, `echo >`, `patch` — modifying files
- `git diff`, `git status` — checking changes
- `cat` — ONLY for non-code files (test output, logs)

### Commands

```bash
gitnexus query "search query" --include-content --limit 10
gitnexus context <function_or_class_name> --include-content
gitnexus impact <function_or_class_name> --direction upstream
gitnexus impact <function_or_class_name> --direction downstream
gitnexus detect_changes --scope unstaged
gitnexus rename --symbol_name old_name --new_name new_name --dry_run
gitnexus cypher "MATCH (f:Function) WHERE f.name CONTAINS 'validate' RETURN f.name, f.filePath LIMIT 20"
```

## Rules
- NEVER use grep/find/cat for code exploration — always gitnexus
- Only modify files necessary to fix the bug
- Do not modify test files unless the issue specifically asks for it
- Keep changes minimal and focused
- Verify your fix by running relevant tests before finishing
