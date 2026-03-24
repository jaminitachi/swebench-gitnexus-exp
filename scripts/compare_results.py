#!/usr/bin/env python3
"""Compare A/B/C experiment results and generate report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

CONDITION_LABELS = {
    "condition_a": "A (Baseline)",
    "condition_b": "B (GitNexus Context)",
    "condition_c": "C (GitNexus Forced)",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare A/B/C experiment results")
    parser.add_argument("--root", type=Path, default=ROOT)
    return parser.parse_args()


def load_preds(results_dir: Path) -> dict[str, dict[str, Any]]:
    """Load predictions from all JSON files in results directory."""
    preds = {}

    # Try preds.json first
    preds_file = results_dir / "preds.json"
    if preds_file.exists():
        raw = json.loads(preds_file.read_text())
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict) and "instance_id" in item:
                    preds[item["instance_id"]] = item
        elif isinstance(raw, dict):
            preds = raw

    # Also check for individual prediction files
    for f in sorted(results_dir.glob("*.json")):
        if f.name == "preds.json":
            continue
        try:
            data = json.loads(f.read_text())
            if isinstance(data, dict) and "instance_id" in data:
                preds[data["instance_id"]] = data
        except (json.JSONDecodeError, KeyError):
            pass

    return preds


def load_trajectories(results_dir: Path) -> dict[str, dict[str, Any]]:
    """Load trajectory files for step/cost analysis."""
    trajs = {}
    for f in sorted(results_dir.rglob("*.traj.json")):
        instance_id = f.name.removesuffix(".traj.json")
        try:
            trajs[instance_id] = json.loads(f.read_text())
        except json.JSONDecodeError:
            pass
    return trajs


def count_steps(traj: dict[str, Any]) -> int | None:
    for key in ("num_steps", "steps", "n_steps"):
        val = traj.get(key)
        if isinstance(val, int):
            return val
        if isinstance(val, list):
            return len(val)
    for key in ("trajectory", "messages", "events", "history"):
        val = traj.get(key)
        if isinstance(val, list):
            return len(val)
    return None


def main() -> int:
    args = parse_args()
    root = args.root

    conditions = {}
    for cond_key, label in CONDITION_LABELS.items():
        results_dir = root / "results" / cond_key
        if not results_dir.exists():
            print(f"[SKIP] {label}: no results directory")
            continue

        preds = load_preds(results_dir)
        trajs = load_trajectories(results_dir)
        conditions[cond_key] = {
            "label": label,
            "preds": preds,
            "trajs": trajs,
        }

    if not conditions:
        print("No results found. Run the experiment first.")
        return 1

    # Collect all instance IDs
    all_ids = set()
    for cond in conditions.values():
        all_ids |= set(cond["preds"].keys())
    all_ids = sorted(all_ids)

    print(f"\n{'='*70}")
    print("SWE-bench GitNexus Experiment — Results Comparison")
    print(f"{'='*70}")
    print(f"\nTotal unique instances: {len(all_ids)}")

    # Summary per condition
    report_lines = ["# SWE-bench GitNexus Experiment Results\n"]

    report_lines.append("## Summary\n")
    report_lines.append("| Condition | Tasks | Patches | Has Patch % | Avg Steps |")
    report_lines.append("|-----------|-------|---------|-------------|-----------|")

    for cond_key, cond in conditions.items():
        n_tasks = len(cond["preds"])
        n_patches = sum(
            1 for p in cond["preds"].values()
            if p.get("model_patch") and len(str(p["model_patch"])) > 10
        )
        patch_pct = (n_patches / n_tasks * 100) if n_tasks > 0 else 0

        steps_list = [
            count_steps(t)
            for t in cond["trajs"].values()
            if count_steps(t) is not None
        ]
        avg_steps = sum(steps_list) / len(steps_list) if steps_list else 0

        line = f"| {cond['label']} | {n_tasks} | {n_patches} | {patch_pct:.1f}% | {avg_steps:.1f} |"
        report_lines.append(line)
        print(f"\n{cond['label']}:")
        print(f"  Tasks: {n_tasks}")
        print(f"  Generated patches: {n_patches} ({patch_pct:.1f}%)")
        print(f"  Avg steps: {avg_steps:.1f}")

    # Per-instance comparison
    report_lines.append("\n## Per-Instance Comparison\n")

    header = "| Instance ID |"
    sep = "|---|"
    for cond in conditions.values():
        header += f" {cond['label']} |"
        sep += "---|"
    report_lines.append(header)
    report_lines.append(sep)

    for iid in all_ids:
        row = f"| `{iid}` |"
        for cond in conditions.values():
            pred = cond["preds"].get(iid, {})
            has_patch = bool(pred.get("model_patch") and len(str(pred["model_patch"])) > 10)
            status = pred.get("exit_status", "")
            traj = cond["trajs"].get(iid, {})
            steps = count_steps(traj)
            cell = f"{'PATCH' if has_patch else 'EMPTY'}"
            if steps:
                cell += f" ({steps}s)"
            if status:
                cell += f" [{status}]"
            row += f" {cell} |"
        report_lines.append(row)

    # Save report
    eval_dir = root / "evaluation"
    eval_dir.mkdir(parents=True, exist_ok=True)

    report_md = "\n".join(report_lines) + "\n"
    (eval_dir / "comparison_report.md").write_text(report_md, encoding="utf-8")

    # Also save raw JSON
    json_report = {
        "conditions": {
            k: {
                "label": v["label"],
                "n_tasks": len(v["preds"]),
                "n_patches": sum(1 for p in v["preds"].values() if p.get("model_patch")),
            }
            for k, v in conditions.items()
        },
        "instance_ids": all_ids,
    }
    (eval_dir / "comparison_report.json").write_text(
        json.dumps(json_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"\nReport saved to: {eval_dir / 'comparison_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
