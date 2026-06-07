class ReportWriter:
    """Builds and writes the human-readable Markdown evaluation report."""

    def __init__(self, path):
        self.path = path

    def write(self, results, metadata):
        self.path.write_text(self.render(results, metadata), encoding="utf-8")

    def render(self, results, metadata):
        lines = []

        lines.append("# Order Enrichment Agent Evaluation")
        lines.append("")
        lines.extend(self._summary(results, metadata))
        lines.append("")
        lines.extend(self._methodology())
        lines.append("")
        lines.extend(self._findings(results))
        lines.append("")
        lines.extend(self._recommendations(results))
        lines.append("")
        lines.extend(self._limitations())
        lines.append("")

        return "\n".join(lines)

    def _summary(self, results, metadata):
        lines = []

        lines.append("## Executive Summary")
        lines.append("")
        lines.append("| Variant | Verdict | Failed Executions | Main Reason |")
        lines.append("|---|---|---:|---|")

        for name, result in results.items():
            lines.append(
                f"| `{name}` | **{result['verdict']}** | "
                f"{result['failed_executions']}/{result['total_executions']} "
                f"({result['failed_execution_rate']:.1%}) | "
                f"{self._escape_table_text(result['main_reason'])} |"
            )

        lines.append("")
        lines.append(
            f"Evaluated **{len(results)} variants** on **{metadata['orders']} orders**, "
            f"with **{metadata['runs']} runs per order** "
            f"(**{metadata['orders'] * metadata['runs']} executions per variant**). "
            f"Seed: `{metadata['seed']}`. Runtime: `{metadata['runtime_s']:.2f}s`."
        )

        return lines

    def _methodology(self):
        lines = []

        lines.append("## Methodology")
        lines.append("")
        lines.append(
            "The harness uses deterministic checks because the key risks are measurable: "
            "missing fields, pricing consistency, shipping validation, risk assessment "
            "quality, and summary verbosity."
        )
        lines.append("")
        lines.append(
            "Critical failures block shipping. Advisory failures are quality issues; high "
            "advisory failure rates can also block shipping. Each order is evaluated "
            "multiple times because the agent has random pricing, random summaries, and "
            "transient risk service failures."
        )

        return lines

    def _findings(self, results):
        lines = []

        lines.append("## Findings")
        lines.append("")

        for name, result in results.items():
            lines.append(f"### `{name}` — {result['verdict']}")
            lines.append("")

            if result["hard_blocks"]:
                lines.append("**Hard blocks:**")
                lines.append("")

                for block in result["hard_blocks"]:
                    lines.append(f"- {block}")

                lines.append("")

            failures = {
                check: stats
                for check, stats in result["checks"].items()
                if stats["failed"] > 0
            }

            if not failures:
                lines.append("No failures detected.")
                lines.append("")
                continue

            lines.append("| Check | Severity | Failures | Total | Rate |")
            lines.append("|---|---|---:|---:|---:|")

            for check, stats in failures.items():
                lines.append(
                    f"| `{check}` | {stats['severity']} | "
                    f"{stats['failed']} | {stats['total']} | {stats['rate']:.1%} |"
                )

            lines.append("")

            if result["samples"]:
                lines.append("Sample failures:")
                lines.append("")

                for sample in result["samples"]:
                    lines.append(
                        f"- `{sample['run_id']}` / `{sample['check']}`: "
                        f"{sample['message']}"
                    )

                lines.append("")

        return lines

    def _recommendations(self, results):
        lines = []

        lines.append("## Recommendations")

        for name, result in results.items():
            if name == "baseline":
                continue

            if result["verdict"] == "SHIP":
                lines.append(f"- `{name}`: Safe to ship.")
            elif result["verdict"] == "SHIP WITH CAUTION":
                lines.append(
                    f"- `{name}`: Ship with caution after reviewing advisory issues."
                )
            else:
                lines.append(f"- `{name}`: Do not ship.")

        return lines

    def _limitations(self):
        lines = []

        lines.append("## Limitations")
        lines.append("")
        lines.append(
            "This eval checks observable output quality and contract stability. It would "
            "not catch every semantic issue, such as a valid-looking but business-wrong "
            "fraud recommendation. For production, I would add golden cases, latency "
            "percentiles, and possibly an LLM judge for summary faithfulness."
        )

        return lines

    @staticmethod
    def _escape_table_text(value):
        return str(value).replace("|", "\\|").replace("\n", " ")