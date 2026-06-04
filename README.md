# Take-home: Order Enrichment Agent

## Time budget

3–4 hours. Stop at 4 hours and note in your writeup what you would
do next.

## The situation

We run an order enrichment agent in production. We have no reliable
way to tell whether a code or prompt change makes it better or worse.
We want that.

## What you have

```
.
├── app/tools/             # tools the agent calls internally
├── variants/
│   ├── baseline.py        # the agent we run today
│   ├── variant_a.py       # a candidate change
│   ├── variant_b.py       # a candidate change
│   └── variant_c.py       # a candidate change
├── fixtures/orders.jsonl  # 20 sample orders
└── quickstart.py
```

Each variant exposes the same interface:

```python
from variants import baseline
result = baseline.enrich_order(order_dict)
```

`python quickstart.py` runs the baseline against a few orders. Start
there.

## What to build

A program and a written report that answer one question for each of
A, B, C:

> **Is this variant safe to ship in place of the baseline?**

How you decide "safe" is up to you. What you measure, how you handle
the agent's behavior, and how you present the result are part of
what we are judging.

## How to submit

1. **Fork this repository** to your own GitHub account.
2. Work on your fork — commit as you go, however you like.
3. When you're done, send us the link to your fork.

Your fork should contain:

1. `eval.py` (and any supporting code) that runs end-to-end
2. `report.md` — the output your program produces
3. `DESIGN.md` (≤ 1 page):
   - what you chose to measure, and why
   - what your eval would **not** catch
   - rough cost and runtime per run

Keep the fork public, or add us as a collaborator if private.

## What we care about

- Your harness gives a clear, defensible verdict on A, B, C
- It would also catch a **new** regression we add tomorrow that you
  have not seen — i.e. it is not narrowly tuned to these three
- It is reproducible enough that we trust the verdict
- The report is readable by a non-engineer

## What we don't care about

- UI / web / dashboards
- Whether you use an LLM judge, deterministic checks, or both —
  your call, justify it in `DESIGN.md`
- Whether you "fix" the agent — out of scope

## Notes

- You may use any libraries, any LLM SDK, any tooling
- If anything is ambiguous, write your interpretation in `DESIGN.md`
  and proceed
- We are hiring for the role of building agents like this one —
  treat the harness the way you would treat one you owned
