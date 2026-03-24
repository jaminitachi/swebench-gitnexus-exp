#!/usr/bin/env python3
"""Prepare SWE-bench Django 50-task dataset for the experiment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from datasets import load_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare Django 50 SWE-bench tasks")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "data",
        help="Output directory for dataset files",
    )
    parser.add_argument(
        "--num-tasks",
        type=int,
        default=50,
        help="Number of Django tasks to select",
    )
    parser.add_argument(
        "--repo-filter",
        default="django/django",
        help="Filter tasks by repo",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    print("Loading SWE-bench Lite dataset...")
    ds = load_dataset("princeton-nlp/SWE-bench_Lite", split="test")

    # Filter Django tasks
    django_tasks = [t for t in ds if t["repo"] == args.repo_filter]
    print(f"Found {len(django_tasks)} Django tasks in SWE-bench Lite")

    # Select first N tasks (deterministic ordering)
    selected = django_tasks[: args.num_tasks]
    print(f"Selected {len(selected)} tasks")

    # Save as JSONL for mini-swe-agent
    for condition in ["condition_a", "condition_b", "condition_c"]:
        condition_dir = args.output_dir / condition
        condition_dir.mkdir(parents=True, exist_ok=True)
        output_path = condition_dir / "test.jsonl"

        with output_path.open("w", encoding="utf-8") as f:
            for task in selected:
                f.write(json.dumps(dict(task), ensure_ascii=False) + "\n")

        print(f"  {condition}: {output_path} ({len(selected)} tasks)")

    # Also save task list for reference
    task_ids = [t["instance_id"] for t in selected]
    (args.output_dir / "task_ids.json").write_text(
        json.dumps(task_ids, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\nTask IDs saved to {args.output_dir / 'task_ids.json'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
