# Order Enrichment Agent Evaluation

## Executive Summary

| Variant | Verdict | Failed Executions | Main Reason |
|---|---|---:|---|
| `baseline` | **SHIP** | 0/200 (0.0%) | No failures detected |
| `variant_a` | **DON'T SHIP** | 53/200 (26.5%) | Missing required fields in 53/200 executions |
| `variant_b` | **DON'T SHIP** | 200/200 (100.0%) | Risk scoring is bypassed; fallback risk returned too often |
| `variant_c` | **DON'T SHIP** | 200/200 (100.0%) | Summary is too long and boilerplate-heavy |

Evaluated **4 variants** on **20 orders**, with **10 runs per order** (**200 executions per variant**). Seed: `42`. Runtime: `60.53s`.

## Methodology

The harness uses deterministic checks because the key risks are measurable: missing fields, pricing consistency, shipping validation, risk assessment quality, and summary verbosity.

Critical failures block shipping. Advisory failures are quality issues; high advisory failure rates can also block shipping. Each order is evaluated multiple times because the agent has random pricing, random summaries, and transient risk service failures.

## Findings

### `baseline` — SHIP

No failures detected.

### `variant_a` — DON'T SHIP

**Hard blocks:**

- Critical failures detected in 53/200 executions.

| Check | Severity | Failures | Total | Rate |
|---|---|---:|---:|---:|
| `required_fields` | critical | 53 | 200 | 26.5% |
| `risk` | critical | 53 | 200 | 26.5% |

Sample failures:

- `ORD-001#2` / `required_fields`: Missing fields: ['risk_assessment']
- `ORD-001#2` / `risk`: risk_assessment is missing.
- `ORD-001#4` / `required_fields`: Missing fields: ['risk_assessment']
- `ORD-001#4` / `risk`: risk_assessment is missing.
- `ORD-001#5` / `required_fields`: Missing fields: ['risk_assessment']
- `ORD-001#5` / `risk`: risk_assessment is missing.
- `ORD-001#9` / `required_fields`: Missing fields: ['risk_assessment']
- `ORD-001#9` / `risk`: risk_assessment is missing.

### `variant_b` — DON'T SHIP

**Hard blocks:**

- Risk fallback rate is too high: 200/200 (100.0%).

| Check | Severity | Failures | Total | Rate |
|---|---|---:|---:|---:|
| `risk_fallback` | advisory | 200 | 200 | 100.0% |

Sample failures:

- `ORD-001#1` / `risk_fallback`: Risk fell back to unknown/manual_review.
- `ORD-001#2` / `risk_fallback`: Risk fell back to unknown/manual_review.
- `ORD-001#3` / `risk_fallback`: Risk fell back to unknown/manual_review.
- `ORD-001#4` / `risk_fallback`: Risk fell back to unknown/manual_review.
- `ORD-001#5` / `risk_fallback`: Risk fell back to unknown/manual_review.
- `ORD-001#6` / `risk_fallback`: Risk fell back to unknown/manual_review.
- `ORD-001#7` / `risk_fallback`: Risk fell back to unknown/manual_review.
- `ORD-001#8` / `risk_fallback`: Risk fell back to unknown/manual_review.

### `variant_c` — DON'T SHIP

**Hard blocks:**

- Boilerplate summary rate is too high: 200/200 (100.0%).
- Long summary rate is too high: 200/200 (100.0%).

| Check | Severity | Failures | Total | Rate |
|---|---|---:|---:|---:|
| `summary_boilerplate` | advisory | 200 | 200 | 100.0% |
| `summary_length` | advisory | 200 | 200 | 100.0% |

Sample failures:

- `ORD-001#1` / `summary_length`: Summary too long: 559 chars.
- `ORD-001#1` / `summary_boilerplate`: Boilerplate detected: ['rapidly evolving landscape', 'operational excellence', 'valued stakeholders', 'state-of-the-art', 'best-in-class', 'industry-leading']
- `ORD-001#2` / `summary_length`: Summary too long: 535 chars.
- `ORD-001#2` / `summary_boilerplate`: Boilerplate detected: ['rapidly evolving landscape', 'operational excellence', 'valued stakeholders', 'state-of-the-art', 'best-in-class', 'industry-leading']
- `ORD-001#3` / `summary_length`: Summary too long: 532 chars.
- `ORD-001#3` / `summary_boilerplate`: Boilerplate detected: ['rapidly evolving landscape', 'operational excellence', 'valued stakeholders', 'state-of-the-art', 'best-in-class', 'industry-leading']
- `ORD-001#4` / `summary_length`: Summary too long: 556 chars.
- `ORD-001#4` / `summary_boilerplate`: Boilerplate detected: ['rapidly evolving landscape', 'operational excellence', 'valued stakeholders', 'state-of-the-art', 'best-in-class', 'industry-leading']


## Recommendations
- `variant_a`: Do not ship.
- `variant_b`: Do not ship.
- `variant_c`: Do not ship.

## Limitations

This eval checks observable output quality and contract stability. It would not catch every semantic issue, such as a valid-looking but business-wrong fraud recommendation. For production, I would add golden cases, latency percentiles, and possibly an LLM judge for summary faithfulness.
