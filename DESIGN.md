# Order Enrichment Agent Evaluation Harness

Scope: Evaluation harness for order enrichment agent variants

---

## 1. Problem Statement

The repository contains a baseline order enrichment agent and three candidate variants. Each variant exposes the same interface:

```python
result = variant.enrich_order(order)
````

The main question this harness answers is:

> Is this variant safe to ship in place of the baseline?

Manual inspection is not enough because the agent has randomized behavior and some regressions only appear across repeated runs. This harness provides a reproducible way to evaluate each variant and produce a clear ship/no-ship decision.

---

## 2. Goals and Non-Goals

### Goals

* Detect missing or invalid output fields.
* Detect pricing, shipping, and risk-assessment regressions.
* Detect probabilistic failures by running each order multiple times.
* Detect user-facing quality issues such as verbose or boilerplate summaries.
* Produce `report.md` for review and `results.jsonl` for audit/history.
* Give each variant one verdict: `SHIP`, `SHIP WITH CAUTION`, or `DON'T SHIP`.

### Non-Goals

* Fixing the agent implementation.
* Replacing the pricing, address, or risk tools.
* Load testing or concurrency testing.
* Using an LLM judge for semantic evaluation.
* Testing against live external services.

---

## 3. Architecture

The evaluation code is separate from production code in `app/`.

```text
eval.py
  |
  |-- loads fixture orders
  |-- runs each variant
  |-- prints terminal summary
  |-- writes report.md and results.jsonl
  |
evaluation/
  |
  |-- base.py      # Severity, CheckResult, BaseCheck
  |-- checks.py    # reusable deterministic checks
  |-- runner.py    # EvalRunner and VariantResult
  |-- report.py    # Markdown report writer
  |-- audit.py     # JSONL audit writer
```

Data flow:

```text
fixtures/orders.jsonl
        |
        v
EvalRunner
        |
        v
baseline / variant_a / variant_b / variant_c
        |
        v
checks.py
        |
        v
VariantResult
        |
        v
report.md + results.jsonl
```

---

## 4. Module Responsibilities

### `eval.py`

CLI entry point. It loads orders, sets the random seed, registers variants, runs the evaluation, prints terminal output, and writes the final report/audit files.

### `evaluation/base.py`

Contains shared OOP abstractions:

* `Severity`
* `CheckResult`
* `BaseCheck`

Each check follows the same interface:

```python
check.run(order, output)
```

### `evaluation/checks.py`

Contains reusable deterministic checks for:

* output type
* required fields
* order ID preservation
* format validation
* pricing math
* shipping validation
* risk-assessment structure
* risk fallback detection
* country mismatch signal
* summary length and boilerplate
* processing time

### `evaluation/runner.py`

Runs each variant against all orders multiple times and aggregates check results into a `VariantResult`.

It calculates:

* failed executions
* critical failure count
* advisory failure count
* hard blocks
* final verdict
* sample failures

### `evaluation/report.py`

Writes the human-readable `report.md`.

### `evaluation/audit.py`

Writes machine-readable `results.jsonl`, useful for comparing runs or integrating with CI.

---

## 5. Key Design Decisions

### 5.1 Keep evaluation separate from `app/`

The `app/` folder contains production tools. The evaluation harness lives in `evaluation/` so it can test behavior without modifying production code.

### 5.2 Use deterministic checks instead of an LLM judge

The important risks in this task are structural and measurable:

* missing `risk_assessment`
* invalid pricing math
* malformed shipping output
* risk service bypass
* boilerplate-heavy summaries

Code-based checks are cheaper, faster, easier to debug, and reproducible. An LLM judge could be added later for semantic summary quality, but it is not necessary for these variants.

### 5.3 Run each order multiple times

The agent has randomness in pricing, summary templates, risk-service failures, and some variant behavior. The default run is:

```text
20 orders × 10 runs per order = 200 executions per variant
```

This helps catch probabilistic regressions like Variant A, which only fails on some runs.

### 5.4 Separate critical and advisory failures

Critical failures block shipping because they break the output contract or business behavior.

Examples:

* missing required fields
* mismatched `order_id`
* invalid pricing
* missing risk assessment

Advisory failures indicate quality or reliability concerns.

Examples:

* risk fallback
* long summary
* boilerplate summary
* unusual processing time

### 5.5 Use aggregate hard blocks

Some failures are acceptable occasionally but unsafe when frequent. The harness escalates these patterns:

* any critical failure
* risk fallback rate above 20%
* boilerplate summary rate above 10%
* long summary rate above 50%

---

## 6. Verdict System

A failed execution means one agent run had at least one failed evaluation check.

A variant is marked `DON'T SHIP` if:

* any critical failure occurs
* risk fallback rate is above 20%
* boilerplate summary rate is above 10%
* long summary rate is above 50%

A variant is marked `SHIP WITH CAUTION` if:

* only non-blocking advisory issues occur

A variant is marked `SHIP` if:

* all checks pass

---

## 7. Expected Findings

### Baseline

Expected verdict: `SHIP`

Reason: It preserves the expected output contract and business behavior.

### Variant A

Expected verdict: `DON'T SHIP`

Reason: It sometimes removes `risk_assessment`, which breaks the required output contract.

### Variant B

Expected verdict: `DON'T SHIP`

Reason: It bypasses the real risk service and always returns fallback risk output.

### Variant C

Expected verdict: `DON'T SHIP`

Reason: It adds long boilerplate text to every summary.

---

## 8. Reproducibility

The harness uses a fixed random seed.

Default:

```bash
python eval.py --seed 42 --runs 10
```

The seed, number of runs, number of orders, and runtime are recorded in both `report.md` and `results.jsonl`.

---

## 9. Cost and Runtime

The harness uses local deterministic Python checks only.

Cost: `$0`

Default workload:

```text
4 variants × 20 orders × 10 runs = 800 agent executions
```

Runtime depends on the simulated latency inside the variants.

---

## 10. Extensibility

### Adding a new check

Create a new class in `evaluation/checks.py`:

```python
class NewCheck(BaseCheck):
    name = "new_check"
    severity = Severity.CRITICAL

    def run(self, order, output):
        ...
```

Then add it to `DEFAULT_CHECKS`.

### Adding a new variant

Import the new variant in `eval.py` and add it to the `VARIANTS` dictionary.

### Adding a new hard block

Add the aggregate rule inside `VariantResult._hard_blocks()` in `evaluation/runner.py`.

---

## 11. Known Gaps and Future Work

This harness checks observable structure, consistency, and simple quality signals. It would not catch every semantic issue, such as:

* a valid-looking but business-wrong fraud recommendation
* stale pricing data
* concise but misleading summaries
* production-only concurrency issues

Future improvements:

* add golden test cases
* compare variant distributions against baseline
* add p50/p95 latency checks
* add more edge-case fixtures
* optionally add an LLM judge for summary faithfulness

---

## 12. How to Run

```bash
python eval.py
```

With custom options:

```bash
python eval.py --runs 20 --seed 123
```

Outputs:

```text
report.md
results.jsonl
```

