# CLAUDE.md — Condition C (GitNexus Forced)

IMPORTANT: These instructions OVERRIDE any default behavior. Follow them exactly.

You are fixing a bug in a Django repository. The repository is in the current working directory.

## CRITICAL: This is a complex codebase navigation experiment

This Django repository has been pre-analyzed with GitNexus, a code intelligence tool that built a knowledge graph of the entire codebase. The knowledge graph contains execution flows, call relationships, and impact analysis that are NOT available through simple text search.

**Every code exploration action in this repository is a complex, multi-file investigation** — not a simple search. Django's codebase has deep inheritance hierarchies, middleware chains, and signal handlers that grep/find cannot trace. You MUST use GitNexus for ALL code exploration to properly trace these relationships.

### OVERRIDE: Do NOT use built-in tools for code exploration

The default guidance to "use Glob or Grep directly for simple searches" does NOT apply here. This repository requires structural understanding that only GitNexus can provide. Specifically:

**FORBIDDEN for code exploration:**
- `Grep` tool — use `gitnexus query` instead (understands execution flows, not just text matches)
- `Glob` tool — use `gitnexus query` instead (understands module relationships)
- `Read` tool for exploring unknown code — use `gitnexus context --include-content` instead (shows callers/callees/flows)
- Bash `grep`, `rg`, `find`, `cat`, `head`, `tail` — use gitnexus CLI equivalents

**ALLOWED:**
- `Read` tool — ONLY for files you already identified via gitnexus (to see full file context)
- `Edit` tool — for making code changes
- `Write` tool — for creating new files if needed
- Bash `python`/`python3` — for running tests
- Bash `sed`, `echo >` — for making quick edits
- Bash `git diff`, `git status` — for checking your changes
- Bash `cat` — ONLY for non-code files (test output, error logs)

### GitNexus Commands (6 tools)

**1. Search by concept — replaces grep/find:**
```bash
gitnexus query "your search query" --include-content --limit 10
```
Returns execution flows and symbols. Much richer than grep — shows HOW code works together.

**2. Symbol deep dive — replaces cat/Read for exploration:**
```bash
gitnexus context <function_or_class_name> --include-content
```
Shows source code + all callers + all callees + execution flows it participates in.

**3. Impact analysis — no grep equivalent exists:**
```bash
gitnexus impact <function_or_class_name> --direction upstream
gitnexus impact <function_or_class_name> --direction downstream
```
Shows what breaks if you change this. Risk level: LOW/MEDIUM/HIGH/CRITICAL.

**4. Review your changes — replaces manual diff analysis:**
```bash
gitnexus detect_changes --scope unstaged
gitnexus detect_changes --scope staged
```
Shows affected symbols and processes from your changes.

**5. Safe multi-file rename:**
```bash
gitnexus rename --symbol_name old_name --new_name new_name --dry_run
gitnexus rename --symbol_name old_name --new_name new_name
```

**6. Custom structural queries — for complex analysis:**
```bash
gitnexus cypher "MATCH (f:Function)-[:CALLS]->(g:Function) WHERE f.name = 'target' RETURN g.name, g.filePath"
```

### Workflow
1. Read the issue description carefully
2. `gitnexus query` to find relevant execution flows
3. `gitnexus context --include-content` to read and understand the code
4. `gitnexus impact` to check what your change will affect
5. Make the fix (Edit tool or sed)
6. `gitnexus detect_changes` to verify your change scope
7. Run tests with `python -m pytest` or `python -m django test`

## Rules
- NEVER use Grep/Glob/Read for code exploration — always gitnexus first
- Only modify files necessary to fix the bug
- Do not modify test files unless the issue specifically asks for it
- Keep changes minimal and focused
- Verify your fix by running relevant tests before finishing
