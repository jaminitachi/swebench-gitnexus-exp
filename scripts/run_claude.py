#!/usr/bin/env python3
"""
SWE-bench experiment runner using Claude Code CLI (OAuth, no API key).

Spawns `claude -p` for each task, with condition-specific CLAUDE.md.
Saves full agent trace via --output-format stream-json.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CONDITIONS = {
    "a": {
        "name": "baseline",
        "prompt_file": ROOT / "prompts" / "condition_a.md",
        "gitnexus": False,
        "description": "Baseline: no GitNexus, standard tools only",
    },
    "b": {
        "name": "gitnexus-context",
        "prompt_file": ROOT / "prompts" / "condition_b.md",
        "gitnexus": True,
        "description": "GitNexus available + usage guide in CLAUDE.md",
    },
    "c": {
        "name": "gitnexus-forced",
        "prompt_file": ROOT / "prompts" / "condition_c.md",
        "gitnexus": True,
        "disable_builtin_search": True,
        "description": "GitNexus only — Grep/Glob disabled, must use gitnexus CLI",
    },
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run SWE-bench with Claude Code CLI")
    p.add_argument("--condition", choices=["a", "b", "c", "all"], default="all")
    p.add_argument("--tasks", type=Path, default=ROOT / "data" / "tasks.jsonl",
                    help="JSONL file with SWE-bench tasks")
    p.add_argument("--indexes-dir", type=Path, default=ROOT / "indexes",
                    help="Pre-built GitNexus indexes by commit hash")
    p.add_argument("--model", default="sonnet", help="Claude model (sonnet/opus/haiku)")
    p.add_argument("--max-turns", type=int, default=30, help="Max Claude turns per task")
    p.add_argument("--timeout", type=int, default=600, help="Timeout per task in seconds")
    p.add_argument("--start-from", type=int, default=0, help="Start from task index N")
    p.add_argument("--limit", type=int, default=0, help="Limit to N tasks (0=all)")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def load_tasks(path: Path) -> list[dict]:
    tasks = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))
    return tasks


def setup_workdir(task: dict, condition: dict, indexes_dir: Path) -> Path:
    """Create a temporary working directory for one task.

    Uses a local full clone of Django (at ROOT/django_repo) as the source,
    creating a git worktree for each task to avoid re-cloning.
    """
    instance_id = task["instance_id"]
    base_commit = task.get("base_commit", "")

    workdir = Path(tempfile.mkdtemp(prefix=f"swe-{instance_id}-"))
    repo_dir = workdir / "repo"

    # Use local Django repo as source (must be full-cloned beforehand)
    source_repo = ROOT / "django_repo"
    if not source_repo.exists():
        raise RuntimeError(
            f"Django repo not found at {source_repo}. "
            "Run: git clone https://github.com/django/django.git django_repo"
        )

    # Create a worktree at the specific commit (fast, no network)
    subprocess.run(
        ["git", "worktree", "add", "--detach", str(repo_dir), base_commit],
        cwd=source_repo, capture_output=True, timeout=30,
    )

    # Fallback: if worktree fails, do a local clone
    if not repo_dir.exists():
        subprocess.run(
            ["git", "clone", "--local", str(source_repo), str(repo_dir)],
            capture_output=True, timeout=60,
        )
        if base_commit:
            subprocess.run(
                ["git", "checkout", base_commit],
                cwd=repo_dir, capture_output=True, timeout=30,
            )

    # Build GitNexus index if condition needs it
    if condition["gitnexus"]:
        subprocess.run(
            ["gitnexus", "analyze", ".", "--force"],
            cwd=repo_dir, capture_output=True, timeout=120,
        )

    # Write CLAUDE.md for this condition
    system_prompt = condition["prompt_file"].read_text()
    (repo_dir / "CLAUDE.md").write_text(system_prompt)

    return workdir


def run_claude_on_task(
    task: dict,
    condition: dict,
    workdir: Path,
    model: str,
    max_turns: int,
    timeout: int,
    trace_dir: Path,
) -> dict:
    """Spawn claude -p for one task, collect results + full trace."""
    instance_id = task["instance_id"]
    repo_dir = workdir / "repo"
    problem = task["problem_statement"]

    prompt = f"""Fix this Django issue. The repository is in the current directory.

## Issue: {instance_id}

{problem}

## Instructions
1. Understand the issue
2. Find the relevant code
3. Implement a minimal fix
4. Verify with tests if possible
"""

    # Full trace file
    trace_file = trace_dir / f"{instance_id}.stream.jsonl"

    # Spawn claude -p with stream-json for full trace
    cmd = [
        "claude",
        "-p", prompt,
        "--model", model,
        "--max-turns", str(max_turns),
        "--permission-mode", "bypassPermissions",
        "--output-format", "stream-json",
        "--verbose",
    ]

    # Condition C: disable Grep/Glob/Read to force gitnexus usage
    if condition.get("disable_builtin_search"):
        cmd.extend(["--disallowed-tools", "Grep,Glob"])

    start = time.time()
    result = {
        "instance_id": instance_id,
        "condition": condition["name"],
        "model": model,
        "start_time": dt.datetime.now().isoformat(),
        "exit_code": None,
        "model_patch": None,
        "duration_s": None,
        "error": None,
        "trace_file": str(trace_file),
    }

    try:
        env = {**os.environ}
        env.pop("CLAUDECODE", None)
        env.pop("CLAUDE_CODE", None)
        env.pop("CLAUDE_CODE_RUNNING", None)

        # Stream output to trace file
        with trace_file.open("w") as trace_f:
            proc = subprocess.run(
                cmd,
                cwd=repo_dir,
                stdout=trace_f,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
                env=env,
            )
        result["exit_code"] = proc.returncode

        # Parse final result from stream (last line with type=result)
        try:
            with trace_file.open() as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            obj = json.loads(line)
                            if obj.get("type") == "result":
                                result["claude_result"] = obj
                        except json.JSONDecodeError:
                            pass
        except Exception:
            pass

        # Collect git diff as patch
        diff_proc = subprocess.run(
            ["git", "diff"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        patch = diff_proc.stdout.strip()
        result["model_patch"] = patch if patch else None

    except subprocess.TimeoutExpired:
        result["error"] = f"Timeout after {timeout}s"
        result["exit_code"] = -1

        # Still try to collect partial patch
        try:
            diff_proc = subprocess.run(
                ["git", "diff"], cwd=repo_dir,
                capture_output=True, text=True, timeout=10,
            )
            result["model_patch"] = diff_proc.stdout.strip() or None
        except Exception:
            pass

    except Exception as e:
        result["error"] = str(e)
        result["exit_code"] = -2

    result["duration_s"] = round(time.time() - start, 1)
    return result


def main() -> int:
    args = parse_args()

    tasks = load_tasks(args.tasks)
    print(f"Loaded {len(tasks)} tasks from {args.tasks}")

    if args.start_from > 0:
        tasks = tasks[args.start_from:]
        print(f"Starting from index {args.start_from}, {len(tasks)} remaining")

    if args.limit > 0:
        tasks = tasks[:args.limit]
        print(f"Limited to {args.limit} tasks")

    conditions_to_run = (
        list(CONDITIONS.keys()) if args.condition == "all"
        else [args.condition]
    )

    for cond_key in conditions_to_run:
        cond = CONDITIONS[cond_key]
        results_dir = ROOT / "results" / f"condition_{cond_key}"
        results_dir.mkdir(parents=True, exist_ok=True)
        trace_dir = ROOT / "traces" / f"condition_{cond_key}"
        trace_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*60}")
        print(f"Condition {cond_key.upper()}: {cond['description']}")
        print(f"Model: {args.model}, Max turns: {args.max_turns}")
        print(f"Tasks: {len(tasks)}")
        print(f"{'='*60}")

        all_results = []
        for i, task in enumerate(tasks):
            iid = task["instance_id"]
            print(f"\n[{i+1}/{len(tasks)}] {iid}...", end=" ", flush=True)

            # Skip if already done
            result_file = results_dir / f"{iid}.json"
            if result_file.exists():
                print("SKIP (already done)")
                existing = json.loads(result_file.read_text())
                all_results.append(existing)
                continue

            if args.dry_run:
                print("DRY RUN")
                continue

            # Setup workdir
            workdir = setup_workdir(task, cond, args.indexes_dir)

            try:
                result = run_claude_on_task(
                    task, cond, workdir,
                    model=args.model,
                    max_turns=args.max_turns,
                    timeout=args.timeout,
                    trace_dir=trace_dir,
                )

                # Save individual result
                result_file.write_text(
                    json.dumps(result, indent=2, ensure_ascii=False) + "\n"
                )
                all_results.append(result)

                has_patch = bool(result.get("model_patch"))
                status = "PATCH" if has_patch else "EMPTY"
                print(f"{status} ({result['duration_s']}s)")

            finally:
                # Cleanup worktree first, then workdir
                source_repo = ROOT / "django_repo"
                try:
                    subprocess.run(
                        ["git", "worktree", "remove", "--force", str(workdir / "repo")],
                        cwd=source_repo, capture_output=True, timeout=30,
                    )
                except Exception:
                    pass
                shutil.rmtree(workdir, ignore_errors=True)

        # Save aggregated predictions (SWE-bench format)
        preds = []
        for r in all_results:
            preds.append({
                "instance_id": r["instance_id"],
                "model_patch": r.get("model_patch", ""),
                "model_name_or_path": f"claude-{args.model}",
            })

        preds_file = results_dir / "preds.json"
        preds_file.write_text(
            json.dumps(preds, indent=2, ensure_ascii=False) + "\n"
        )

        # Summary
        n_patches = sum(1 for r in all_results if r.get("model_patch"))
        n_errors = sum(1 for r in all_results if r.get("error"))
        avg_dur = (
            sum(r.get("duration_s", 0) for r in all_results) / len(all_results)
            if all_results else 0
        )
        print(f"\n--- Condition {cond_key.upper()} Summary ---")
        print(f"  Total: {len(all_results)}")
        print(f"  Patches: {n_patches} ({n_patches/max(len(all_results),1)*100:.0f}%)")
        print(f"  Errors: {n_errors}")
        print(f"  Avg duration: {avg_dur:.0f}s")
        print(f"  Preds saved: {preds_file}")
        print(f"  Traces saved: {trace_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
