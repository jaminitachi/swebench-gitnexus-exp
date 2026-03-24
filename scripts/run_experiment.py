#!/usr/bin/env python3
"""Run SWE-bench A/B/C experiment with 3 conditions."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import shlex
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CONDITIONS = {
    "condition_a": {
        "name": "baseline",
        "config": ROOT / "configs" / "condition_a.yaml",
        "description": "Baseline: no GitNexus, standard bash only",
    },
    "condition_b": {
        "name": "gitnexus-context",
        "config": ROOT / "configs" / "condition_b.yaml",
        "description": "GitNexus Context: guide in system prompt, optional use",
    },
    "condition_c": {
        "name": "gitnexus-forced",
        "config": ROOT / "configs" / "condition_c.yaml",
        "description": "GitNexus Forced: must use gitnexus CLI for exploration",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SWE-bench A/B/C experiment")
    parser.add_argument(
        "--condition",
        choices=["a", "b", "c", "all"],
        default="all",
        help="Which condition(s) to run",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel workers",
    )
    parser.add_argument(
        "--model",
        default="anthropic/claude-sonnet-4-6",
        help="Model to use (passed to mini-swe-agent)",
    )
    parser.add_argument(
        "--step-limit",
        type=int,
        default=50,
        help="Max agent steps per task",
    )
    parser.add_argument(
        "--cost-limit",
        type=float,
        default=5.0,
        help="Max API cost per task (USD)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing",
    )
    return parser.parse_args()


def now_str() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def run_condition(
    condition_key: str,
    workers: int,
    model: str,
    step_limit: int,
    cost_limit: float,
    dry_run: bool,
) -> int:
    cond = CONDITIONS[condition_key]
    data_dir = ROOT / "data" / condition_key
    results_dir = ROOT / "results" / condition_key
    logs_dir = ROOT / "logs"
    results_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    subset_path = data_dir / "test.jsonl"
    if not subset_path.exists():
        # Try directory format
        subset_path = data_dir
        if not subset_path.exists():
            print(f"[{condition_key}] ERROR: Dataset not found at {data_dir}")
            return 1

    # Read system prompt from the corresponding jinja file
    prompt_map = {
        "condition_a": ROOT / "prompts" / "system_baseline.jinja",
        "condition_b": ROOT / "prompts" / "system_gitnexus.jinja",
        "condition_c": ROOT / "prompts" / "system_forced.jinja",
    }
    system_prompt_path = prompt_map[condition_key]

    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = logs_dir / f"{condition_key}_{timestamp}.log"

    # Build mini-swe-agent command
    # Use -c to override system_template with our prompt
    cmd = [
        "mini-extra",
        "swebench",
        "--model", model,
        "--subset", str(subset_path),
        "--split", "test",
        "--output", str(results_dir),
        "--workers", str(workers),
        "-c", f"agent.step_limit={step_limit}",
        "-c", f"agent.cost_limit={cost_limit}",
        "-c", f"agent.system_template_path={system_prompt_path}",
    ]

    # For conditions B and C, ensure gitnexus is available in the container
    if condition_key in ("condition_b", "condition_c"):
        # We'll need to mount gitnexus or pre-install it
        # For now, add env var to signal gitnexus availability
        cmd.extend([
            "-c", "environment.env.GITNEXUS_AVAILABLE=1",
        ])

    print(f"\n{'='*60}")
    print(f"[{now_str()}] Starting {condition_key}: {cond['description']}")
    print(f"  Model: {model}")
    print(f"  Workers: {workers}")
    print(f"  Step limit: {step_limit}")
    print(f"  Cost limit: ${cost_limit}")
    print(f"  Log: {log_path}")
    print(f"  Command: {shlex.join(cmd)}")
    print(f"{'='*60}\n")

    if dry_run:
        print("[DRY RUN] Would execute the above command")
        return 0

    start_time = time.time()

    with log_path.open("w", encoding="utf-8") as log_file:
        log_file.write(f"[{now_str()}] START {condition_key}\n")
        log_file.write(f"Description: {cond['description']}\n")
        log_file.write(f"Command: {shlex.join(cmd)}\n\n")
        log_file.flush()

        try:
            proc = subprocess.run(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
                env={**os.environ, "MSWEA_COST_TRACKING": "default"},
            )
            exit_code = proc.returncode
        except FileNotFoundError:
            exit_code = 127
            log_file.write("ERROR: mini-extra command not found. Install mini-swe-agent.\n")

        duration = time.time() - start_time
        log_file.write(f"\n[{now_str()}] END {condition_key}\n")
        log_file.write(f"Duration: {duration:.1f}s ({duration/60:.1f}m)\n")
        log_file.write(f"Exit code: {exit_code}\n")

    status = "OK" if exit_code == 0 else f"FAIL (exit={exit_code})"
    print(f"[{condition_key}] {status} in {duration/60:.1f}m — log: {log_path}")
    return exit_code


def main() -> int:
    args = parse_args()

    if args.condition == "all":
        to_run = ["condition_a", "condition_b", "condition_c"]
    else:
        to_run = [f"condition_{args.condition}"]

    print(f"[{now_str()}] SWE-bench GitNexus Experiment")
    print(f"  Conditions: {', '.join(to_run)}")
    print(f"  Model: {args.model}")
    print(f"  Workers: {args.workers}")

    overall_start = time.time()
    results = {}

    for cond_key in to_run:
        exit_code = run_condition(
            condition_key=cond_key,
            workers=args.workers,
            model=args.model,
            step_limit=args.step_limit,
            cost_limit=args.cost_limit,
            dry_run=args.dry_run,
        )
        results[cond_key] = exit_code

    total_duration = time.time() - overall_start
    print(f"\n[{now_str()}] Experiment complete in {total_duration/60:.1f}m")
    print("Results:")
    for k, v in results.items():
        status = "OK" if v == 0 else f"FAIL (exit={v})"
        print(f"  {k}: {status}")

    return max(results.values()) if results else 0


if __name__ == "__main__":
    raise SystemExit(main())
