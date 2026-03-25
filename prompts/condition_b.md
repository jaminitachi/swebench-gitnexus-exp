# CLAUDE.md — Condition B (GitNexus Context)

You are fixing a bug in a Django repository. The repository is in the current working directory.

## GitNexus Code Intelligence

You have access to `gitnexus` CLI — a code intelligence tool with a pre-built knowledge graph of this Django codebase. Use it to navigate the code more effectively.

### Commands

**Search by concept (better than grep for understanding code flow):**
```bash
gitnexus query "your search query" --include-content --limit 10
```

**Get full context of a symbol (callers, callees, execution flows):**
```bash
gitnexus context <function_or_class_name> --include-content
```

**Check impact before changing code:**
```bash
gitnexus impact <function_or_class_name> --direction upstream
gitnexus impact <function_or_class_name> --direction downstream
```

**Analyze what your current changes affect:**
```bash
gitnexus detect_changes --scope unstaged
gitnexus detect_changes --scope staged
```

**Safe multi-file rename (preview first with dry_run):**
```bash
gitnexus rename --symbol_name old_name --new_name new_name --dry_run
gitnexus rename --symbol_name old_name --new_name new_name
```

**Custom graph query:**
```bash
gitnexus cypher "MATCH (f:Function)-[:CALLS]->(g:Function) WHERE f.name = 'some_function' RETURN g.name, g.filePath"
```

### When to use GitNexus vs standard tools

- Understand execution flow → `gitnexus query`
- Find all callers/callees → `gitnexus context`
- Check blast radius → `gitnexus impact`
- Review your changes before committing → `gitnexus detect_changes`
- Rename across files → `gitnexus rename`
- Search for a string literal → `grep`
- Read a specific file → `cat`

You can freely use both gitnexus and standard tools (grep, find, cat, etc.).

## Rules
- Only modify files necessary to fix the bug
- Do not modify test files unless the issue specifically asks for it
- Keep changes minimal and focused
- Verify your fix by running relevant tests before finishing
