#!/usr/bin/env python
"""Script to run evaluations.

Usage:
    python scripts/run_eval.py --type board_classification
    python scripts/run_eval.py --type topic_merge --limit 10
    python scripts/run_eval.py --all
"""

import argparse
import json
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, ".")

from app.evaluation.runner import EvaluationRunner
from app.evaluation.schemas import EvaluationConfigDTO, EvaluationType


def print_run_result(run):
    """Print evaluation run result."""
    print(f"\n{'=' * 60}")
    print(f"Evaluation: {run.evaluation_type.value}")
    print(f"Run ID: {run.id}")
    print(f"Status: {run.status.value}")
    print(f"Duration: {run.duration_seconds:.2f}s")
    print(f"{'=' * 60}")

    if run.metrics:
        print("\nMetrics:")
        for metric in run.metrics:
            status = "✓" if metric.value >= 0.7 else "✗" if metric.value < 0.5 else "~"
            print(f"  {status} {metric.name}: {metric.value:.4f}")
            if metric.details:
                for key, value in metric.details.items():
                    if not isinstance(value, (dict, list)):
                        print(f"      {key}: {value}")

    if run.summary:
        print(f"\nPassed: {'Yes' if run.summary.get('passed') else 'No'}")
        if run.summary.get("failed_metrics"):
            print("Failed metrics:")
            for fm in run.summary["failed_metrics"]:
                print(f"  - {fm['name']}: {fm['value']:.4f} < {fm['threshold']}")

    if run.errors:
        print("\nErrors:")
        for error in run.errors:
            print(f"  - {error}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run evaluation tasks"
    )
    parser.add_argument(
        "--type",
        type=str,
        choices=[e.value for e in EvaluationType],
        help="Evaluation type to run",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all available evaluations",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of samples",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file for results (JSON)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    if not args.type and not args.all:
        parser.error("Either --type or --all must be specified")

    runner = EvaluationRunner()
    results = []

    print(f"Starting evaluation at {datetime.now().isoformat()}")

    if args.all:
        print("\nRunning all evaluations...")
        runs = runner.run_all(sample_limit=args.limit)
        results.extend(runs)
        for run in runs:
            print_run_result(run)
    else:
        eval_type = EvaluationType(args.type)
        print(f"\nRunning {eval_type.value} evaluation...")

        config = EvaluationConfigDTO(
            evaluation_type=eval_type,
            sample_limit=args.limit,
            include_details=args.verbose,
        )
        run = runner.run(config)
        results.append(run)
        print_run_result(run)

    # Summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    total = len(results)
    passed = sum(1 for r in results if r.summary.get("passed", False))
    failed = total - passed

    print(f"Total evaluations: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    # Output to file if requested
    if args.output:
        output_data = {
            "timestamp": datetime.now().isoformat(),
            "runs": [
                {
                    "id": r.id,
                    "type": r.evaluation_type.value,
                    "status": r.status.value,
                    "duration_seconds": r.duration_seconds,
                    "metrics": {m.name: m.value for m in r.metrics},
                    "passed": r.summary.get("passed", False),
                    "errors": r.errors,
                }
                for r in results
            ],
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
            },
        }

        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"\nResults saved to {args.output}")

    # Exit with error if any failed
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
