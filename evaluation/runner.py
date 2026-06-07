from collections import defaultdict

from evaluation.base import CheckResult, Severity


class EvalRunner:
    """Runs variants against fixture orders and applies evaluation checks."""

    def __init__(self, checks, runs_per_order=10):
        self.checks = checks
        self.runs_per_order = runs_per_order

    def evaluate(self, name, enrich_order, orders):
        results = []

        for order in orders:
            for run_index in range(self.runs_per_order):
                run_id = f"{order.get('order_id', '')}#{run_index + 1}"
                results.extend(self._run_once(enrich_order, order, run_id))

        return VariantResult(name, results)

    def _run_once(self, enrich_order, order, run_id):
        try:
            output = enrich_order(order)
        except Exception as exc:
            return [
                CheckResult(
                    check="runtime_exception",
                    passed=False,
                    severity=Severity.CRITICAL,
                    message=f"{type(exc).__name__}: {exc}",
                    order_id=order.get("order_id", ""),
                    run_id=run_id,
                )
            ]

        if not isinstance(output, dict):
            result = self.checks[0].run(order, output)
            return [self._with_run_id(result, run_id)]

        return [
            self._with_run_id(check.run(order, output), run_id)
            for check in self.checks
        ]

    @staticmethod
    def _with_run_id(result, run_id):
        return CheckResult(
            check=result.check,
            passed=result.passed,
            severity=result.severity,
            message=result.message,
            order_id=result.order_id,
            run_id=run_id,
        )


class VariantResult:
    """Aggregates check results and computes the final variant verdict."""

    def __init__(self, name, results):
        self.name = name
        self.results = results
        self.checks = self._summarize_checks()
        self.hard_blocks = self._hard_blocks()

    @property
    def verdict(self):
        if self.hard_blocks or self.critical_failures > 0:
            return "DON'T SHIP"

        if self.advisory_failures > 0:
            return "SHIP WITH CAUTION"

        return "SHIP"

    @property
    def failed_execution_count(self):
        return len({result.run_id for result in self.results if result.failed})

    @property
    def total_execution_count(self):
        return len({result.run_id for result in self.results})

    @property
    def failed_execution_rate(self):
        if not self.total_execution_count:
            return 0.0

        return self.failed_execution_count / self.total_execution_count

    @property
    def critical_failures(self):
        return sum(
            1
            for result in self.results
            if result.failed and result.severity == Severity.CRITICAL
        )

    @property
    def advisory_failures(self):
        return sum(
            1
            for result in self.results
            if result.failed and result.severity == Severity.ADVISORY
        )

    @property
    def main_reason(self):
        if self.name == "baseline" and not self.hard_blocks:
            return "No failures detected"

        if self.checks.get("required_fields", {}).get("failed", 0):
            failed = self.checks["required_fields"]["failed"]
            total = self.checks["required_fields"]["total"]
            return f"Missing required fields in {failed}/{total} executions"

        if self.checks.get("risk_fallback", {}).get("rate", 0) > 0.20:
            return "Risk scoring is bypassed; fallback risk returned too often"

        if self.checks.get("summary_boilerplate", {}).get("rate", 0) > 0.10:
            return "Summary is too long and boilerplate-heavy"

        if self.hard_blocks:
            return self.hard_blocks[0]

        if self.advisory_failures:
            return "Non-blocking advisory issues detected"

        return "No failures detected"

    @property
    def samples(self):
        return [result for result in self.results if result.failed][:8]

    def to_dict(self):
        return {
            "variant": self.name,
            "verdict": self.verdict,
            "failed_executions": self.failed_execution_count,
            "total_executions": self.total_execution_count,
            "failed_execution_rate": self.failed_execution_rate,
            "main_reason": self.main_reason,
            "critical_failures": self.critical_failures,
            "advisory_failures": self.advisory_failures,
            "hard_blocks": self.hard_blocks,
            "checks": self.checks,
            "samples": [
                {
                    "order_id": result.order_id,
                    "run_id": result.run_id,
                    "check": result.check,
                    "message": result.message,
                }
                for result in self.samples
            ],
        }

    def _summarize_checks(self):
        summary = defaultdict(lambda: {"failed": 0, "total": 0, "severity": ""})

        for result in self.results:
            item = summary[result.check]
            item["total"] += 1
            item["severity"] = result.severity.value

            if result.failed:
                item["failed"] += 1

        for item in summary.values():
            item["rate"] = item["failed"] / item["total"] if item["total"] else 0.0

        return dict(sorted(summary.items()))

    def _hard_blocks(self):
        blocks = []

        if self.critical_failures:
            blocks.append(
                f"Critical failures detected in "
                f"{self.failed_execution_count}/{self.total_execution_count} executions."
            )

        self._add_rate_block(blocks, "risk_fallback", 0.20, "Risk fallback rate")
        self._add_rate_block(blocks, "summary_boilerplate", 0.10, "Boilerplate summary rate")
        self._add_rate_block(blocks, "summary_length", 0.50, "Long summary rate")

        return blocks

    def _add_rate_block(self, blocks, check_name, threshold, label):
        check = self.checks.get(check_name)

        if check and check["rate"] > threshold:
            blocks.append(
                f"{label} is too high: "
                f"{check['failed']}/{check['total']} ({check['rate']:.1%})."
            )