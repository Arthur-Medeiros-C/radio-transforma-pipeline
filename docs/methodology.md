# Methodology

> The system of work behind every project in this studio.
> Practical, not bureaucratic. Rigorous, not heavy.

---

## 1. Core Principle: Eval-Driven Development (EDD)

**The evaluation harness is built before the orchestration logic.**

This is the single most important rule in this methodology. It is what 
separates a prototype from a production system, and it is non-negotiable.

The reasoning is simple:

- A system without measurement is an opinion, not an engineering artifact.
- Prompt changes, model swaps and architecture decisions made without a 
  golden dataset are guesses dressed as progress.
- Regressions are invisible until they hit production — unless you measure.

**Consequences for every project:**

1. The **Golden Dataset** (curated, versioned, with ground truth) is created 
   in Phase 0 — before any pipeline code.
2. The **Eval Harness** (Promptfoo for prompt/agent eval, Langfuse for 
   tracing and observability) is wired up in Phase 0 — before the first 
   LLM call is written.
3. Every subsequent change (prompt, model, tool, retrieval strategy) is 
   validated against the harness. If it does not improve the metric, it 
   does not ship.
4. Metrics are published in the `README.md` — not buried in a notebook.

---

## 2. The Four Phases

Every project follows the same phased structure. Phases are sequential in 
their foundation, but overlapping in execution.
