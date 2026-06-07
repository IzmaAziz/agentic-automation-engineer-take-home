import argparse
import json
import random
import time
from pathlib import Path

from evaluation.audit import AuditWriter
from evaluation.checks import DEFAULT_CHECKS
from evaluation.report import ReportWriter
from evaluation.runner import EvalRunner
from variants import baseline, variant_a, variant_b, variant_c


VARIANTS = {
    "baseline": baseline.enrich_order,
    "variant_a": variant_a.enrich_order,
    "variant_b": variant_b.enrich_order,
    "variant_c": variant_c.enrich_order,
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--fixture", default="fixtures/orders.jsonl")
    parser.add_argument("--report", default="report.md")
    parser.add_argument("--audit", default="results.jsonl")
    return parser.parse_args()


def load_orders(path):
    with path.open("r", encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def print_variant(name, result, elapsed_s):
    print()
    print("=" * 72)
    print(f"Variant: {name}")
    print("=" * 72)
    print(f"Verdict: {result['verdict']}")
    print(f"Runtime: {elapsed_s:.2f}s")
    print(
        f"Failed executions: "
        f"{result['failed_executions']}/{result['total_executions']} "
        f"({result['failed_execution_rate']:.1%})"
    )
    print(f"Main reason: {result['main_reason']}")
    print(f"Critical failures: {result['critical_failures']}")
    print(f"Advisory failures: {result['advisory_failures']}")

    if result["hard_blocks"]:
        print("\nHard blocks:")
        for block in result["hard_blocks"]:
            print(f"  - {block}")

    failures = {
        check: stats
        for check, stats in result["checks"].items()
        if stats["failed"] > 0
    }

    if not failures:
        print("\nFailures: none")
        return

    print("\nFailed checks:")
    for check, stats in failures.items():
        print(
            f"  - {check}: "
            f"{stats['failed']}/{stats['total']} failed ({stats['rate']:.1%})"
        )


def main():
    args = parse_args()
    random.seed(args.seed)

    root = Path(__file__).parent
    orders = load_orders(root / args.fixture)
    runner = EvalRunner(DEFAULT_CHECKS, runs_per_order=args.runs)

    print("=" * 72)
    print("Order Enrichment Agent Evaluation")
    print("=" * 72)
    print(f"Seed: {args.seed}")
    print(f"Orders: {len(orders)}")
    print(f"Runs per order: {args.runs}")
    print(f"Executions per variant: {len(orders) * args.runs}")
    print(f"Total variants: {len(VARIANTS)}")
    print(f"Total executions: {len(orders) * args.runs * len(VARIANTS)}")

    start = time.time()
    results = {}

    for name, enrich_order in VARIANTS.items():
        print(f"\nRunning {name}...")
        variant_start = time.time()

        result = runner.evaluate(name, enrich_order, orders).to_dict()
        results[name] = result

        print_variant(name, result, time.time() - variant_start)

    runtime_s = time.time() - start

    metadata = {
        "seed": args.seed,
        "runs": args.runs,
        "orders": len(orders),
        "runtime_s": round(runtime_s, 3),
    }

    ReportWriter(root / args.report).write(results, metadata)
    AuditWriter(root / args.audit).write(results, metadata)

    print()
    print("=" * 72)
    print("Final Ship/No-Ship Summary")
    print("=" * 72)

    for name, result in results.items():
        print(
            f"{name:<12} {result['verdict']:<18} "
            f"failed_executions={result['failed_executions']}/"
            f"{result['total_executions']} "
            f"reason={result['main_reason']}"
        )

    print()
    print(f"Wrote {args.report}")
    print(f"Wrote {args.audit}")
    print(f"Total runtime: {runtime_s:.2f}s")


if __name__ == "__main__":
    main()