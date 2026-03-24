#!/usr/bin/env python3
"""
Pre-build GitNexus indexes for all SWE-bench task commits.

For each unique base_commit in the task list:
1. Clone Django repo at that commit
2. Run gitnexus analyze
3. Save .gitnexus/ directory by commit hash

This avoids running gitnexus analyze during the experiment (saves time + memory).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Pre-build GitNexus indexes per commit")
    p.add_argument("--tasks", type=Path, default=ROOT / "data" / "tasks.jsonl")
    p.add_argument("--output", type=Path, default=ROOT / "indexes")
    p.add_argument("--skip-existing", action="store_true", default=True,
                    help="Skip commits that already have an index")
    p.add_argument("--no-embeddings", action="store_true", default=True,
                    help="Skip embeddings (saves RAM and avoids ONNX issues)")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    # Load tasks
    tasks = []
    with args.tasks.open() as f:
        for line in f:
            if line.strip():
                tasks.append(json.loads(line))

    # Get unique commits
    commits = {}
    for t in tasks:
        commit = t.get("base_commit", "")
        if commit and commit not in commits:
            commits[commit] = {
                "repo": t["repo"],
                "instance_id": t["instance_id"],
            }

    print(f"Found {len(commits)} unique commits from {len(tasks)} tasks")

    success = 0
    failed = 0

    for i, (commit, info) in enumerate(commits.items()):
        short = commit[:8]
        index_dir = args.output / commit / ".gitnexus"

        if args.skip_existing and index_dir.exists():
            print(f"[{i+1}/{len(commits)}] {short} SKIP (exists)")
            success += 1
            continue

        print(f"[{i+1}/{len(commits)}] {short} ({info['instance_id']})...", end=" ", flush=True)

        tmpdir = Path(tempfile.mkdtemp(prefix=f"gn-{short}-"))
        try:
            # Clone at specific commit
            repo_url = f"https://github.com/{info['repo']}.git"
            subprocess.run(
                ["git", "clone", "--depth", "50", repo_url, str(tmpdir / "repo")],
                capture_output=True, timeout=120,
            )
            subprocess.run(
                ["git", "checkout", commit],
                cwd=tmpdir / "repo",
                capture_output=True, timeout=30,
            )

            # Run gitnexus analyze
            start = time.time()
            cmd = ["gitnexus", "analyze", ".", "--force"]
            if args.no_embeddings:
                # Don't pass --embeddings (skip by default)
                pass
            else:
                cmd.append("--embeddings")

            proc = subprocess.run(
                cmd,
                cwd=tmpdir / "repo",
                capture_output=True,
                text=True,
                timeout=300,  # 5 min max
            )

            duration = time.time() - start

            if proc.returncode == 0 and (tmpdir / "repo" / ".gitnexus").exists():
                # Copy index to output
                dest = args.output / commit
                dest.mkdir(parents=True, exist_ok=True)
                if (dest / ".gitnexus").exists():
                    shutil.rmtree(dest / ".gitnexus")
                shutil.copytree(tmpdir / "repo" / ".gitnexus", dest / ".gitnexus")
                print(f"OK ({duration:.0f}s)")
                success += 1
            else:
                print(f"FAIL (exit={proc.returncode})")
                if proc.stderr:
                    print(f"  stderr: {proc.stderr[:200]}")
                failed += 1

        except subprocess.TimeoutExpired:
            print("TIMEOUT")
            failed += 1
        except Exception as e:
            print(f"ERROR: {e}")
            failed += 1
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    print(f"\nDone: {success} success, {failed} failed, {len(commits)} total")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
