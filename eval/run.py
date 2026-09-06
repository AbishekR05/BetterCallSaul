# eval/run.py
"""
Main CLI Entrypoint for Phase 2.4 Retrieval Evaluation Framework.
Usage:
    python -m eval.run --mode regression
    python -m eval.run --mode open_world
"""

import sys
sys.path.append("d:/Abishek")

import argparse
from pathlib import Path
from eval.harness import run_regression, run_open_world
from eval.report_builder import build_evaluation_report


def main():
    parser = argparse.ArgumentParser(description="Phase 2.4 Retrieval Evaluation Runner")
    parser.add_argument(
        "--mode",
        type=str,
        choices=["regression", "open_world"],
        default="regression",
        help="Evaluation mode: 'regression' (1,000 pilot sample) or 'open_world' (live DB)"
    )
    args = parser.parse_args()

    output_dir = Path("d:/Abishek/benchmark/phase_2_4")

    if args.mode == "regression":
        results, manifest = run_regression(output_dir=output_dir)
        report_path = build_evaluation_report(results, manifest, output_dir=output_dir)
        print(f"\n[OK] Closed-World Regression Test Complete. Report: {report_path}")

    elif args.mode == "open_world":
        results, manifest = run_open_world(output_dir=output_dir)
        report_path = build_evaluation_report(results, manifest, output_dir=output_dir)
        print(f"\n[OK] Open-World Production Baseline Run Complete. Report: {report_path}")


if __name__ == "__main__":
    main()
