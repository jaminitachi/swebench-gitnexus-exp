#!/usr/bin/env python3
"""
Run SWE-bench evaluation on experiment results.

Uses swebench harness to apply patches and run tests in Docker containers.
Evaluates all 3 conditions (A/B/C) and generates resolve rate report.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CONDITIONS = ["condition_a", "condition_b", "condition_c"]
CONDITION_LABELS = {
    "condition_a": "A (Baseline)",
    "condition_b": "B (GitNexus Context)",
    "condition_c": "C (GitNexus Forced)",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run SWE-bench evaluation")
    p.add_argument("--condition", choices=["a", "b", "c", "all"], default="all")
    p.add_argument("--max-workers", type=int, default=2,
                    help="Max parallel Docker containers")
    p.add_argument("--timeout", type=int, default=900,
                    help="Timeout per instance in seconds")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def run_swebench_eval(condition: str, max_workers: int, timeout: int) -> dict:
    """Run swebench evaluation for one condition."""
    preds_file = ROOT / "results" / condition / "preds.json"
    output_dir = ROOT / "evaluation" / condition

    if not preds_file.exists():
        print(f"  SKIP: {preds_file} not found")
        return {}

    output_dir.mkdir(parents=True, exist_ok=True)

    # swebench expects predictions in specific format
    # Convert our format to swebench format if needed
    preds = json.loads(preds_file.read_text())

    # Ensure correct format
    swebench_preds = []
    for p in preds:
        swebench_preds.append({
            "instance_id": p["instance_id"],
            "model_patch": p.get("model_patch", ""),
            "model_name_or_path": p.get("model_name_or_path", "claude-sonnet"),
        })

    # Write swebench-format predictions
    swebench_preds_file = output_dir / "predictions.json"
    swebench_preds_file.write_text(
        json.dumps(swebench_preds, indent=2) + "\n"
    )

    # Run evaluation
    cmd = [
        sys.executable, "-m", "swebench.harness.run_evaluation",
        "--predictions_path", str(swebench_preds_file),
        "--max_workers", str(max_workers),
        "--timeout", str(timeout),
        "--run_id", condition,
    ]

    print(f"  Running: {' '.join(cmd)}")

    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout * 60
    )

    if proc.returncode != 0:
        print(f"  STDERR: {proc.stderr[:500]}")

    # Parse results
    results = {}
    # swebench outputs results to a specific location
    # Check for results file
    for results_file in [
        output_dir / f"{condition}.json",
        Path(f"results_{condition}.json"),
        ROOT / f"results_{condition}.json",
    ]:
        if results_file.exists():
            results = json.loads(results_file.read_text())
            break

    # Also check stdout for results summary
    if proc.stdout:
        print(f"  Output: {proc.stdout[:1000]}")
        (output_dir / "eval_stdout.txt").write_text(proc.stdout)

    if proc.stderr:
        (output_dir / "eval_stderr.txt").write_text(proc.stderr)

    return results


def main() -> int:
    args = parse_args()

    if args.condition == "all":
        to_eval = CONDITIONS
    else:
        to_eval = [f"condition_{args.condition}"]

    print(f"SWE-bench Evaluation")
    print(f"Conditions: {', '.join(to_eval)}")
    print(f"Max workers: {args.max_workers}")
    print(f"Timeout: {args.timeout}s per instance\n")

    all_results = {}

    for cond in to_eval:
        label = CONDITION_LABELS.get(cond, cond)
        print(f"\n{'='*50}")
        print(f"Evaluating {label}")
        print(f"{'='*50}")

        if args.dry_run:
            print("  DRY RUN — skipping")
            continue

        results = run_swebench_eval(cond, args.max_workers, args.timeout)
        all_results[cond] = results

    # Generate summary
    if all_results:
        print(f"\n{'='*50}")
        print("EVALUATION SUMMARY")
        print(f"{'='*50}")
        for cond, results in all_results.items():
            label = CONDITION_LABELS.get(cond, cond)
            if isinstance(results, dict) and "resolved" in results:
                resolved = results["resolved"]
                total = results.get("total", 50)
                print(f"  {label}: {len(resolved)}/{total} resolved ({len(resolved)/total*100:.1f}%)")
            else:
                print(f"  {label}: results pending (check evaluation/{cond}/)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
