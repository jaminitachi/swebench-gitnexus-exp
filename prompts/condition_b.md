# CLAUDE.md — Condition B (GitNexus Context)

You are fixing a bug in a Django repository. The repository is in the current working directory.

## GitNexus Code Intelligence

This Django repository has been pre-analyzed with GitNexus, a code intelligence tool that built a knowledge graph of the entire codebase. The knowledge graph maps execution flows, call relationships, inheritance hierarchies, and module boundaries.

GitNexus is especially useful for Django because Django has deep inheritance chains, middleware pipelines, signal handlers, and manager/queryset delegation that are hard to trace with simple grep. Use GitNexus when you need to understand HOW code flows, not just WHERE a string appears.

### Commands (6 tools)

**1. Search by concept (better than grep for understanding code flow):**
```bash
gitnexus query "your search query" --include-content --limit 10
```
Returns execution flows and symbols. Shows HOW code works together.

**2. Symbol deep dive (callers, callees, execution flows):**
```bash
gitnexus context <function_or_class_name> --include-content
```
360-degree view: source code + all callers + all callees + related types.

**3. Impact analysis (check before changing code):**
```bash
gitnexus impact <function_or_class_name> --direction upstream
gitnexus impact <function_or_class_name> --direction downstream
```
Shows what depends on this (upstream) or what this depends on (downstream). Risk: LOW/MEDIUM/HIGH/CRITICAL.

**4. Review your changes:**
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

**6. Custom structural queries:**
```bash
gitnexus cypher "MATCH (f:Function)-[:CALLS]->(g:Function) WHERE f.name = 'some_function' RETURN g.name, g.filePath"
```

### When to use GitNexus vs standard tools

| Need | Best tool |
|------|-----------|
| Understand execution flow / how code works | `gitnexus query` |
| Find all callers/callees of a function | `gitnexus context` |
| Check blast radius before changing code | `gitnexus impact` |
| Review what your changes affect | `gitnexus detect_changes` |
| Rename across multiple files | `gitnexus rename` |
| Search for an exact string literal | `grep` |
| Read a specific file you already know | `cat` or Read tool |

You can freely use both gitnexus and standard tools (grep, find, cat, etc.) as you see fit.

## Rules
- Only modify files necessary to fix the bug
- Do not modify test files unless the issue specifically asks for it
- Keep changes minimal and focused
- Verify your fix by running relevant tests before finishing
