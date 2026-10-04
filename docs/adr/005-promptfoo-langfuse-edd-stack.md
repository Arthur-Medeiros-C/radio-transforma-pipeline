# ADR-005: Use Promptfoo and Langfuse for Eval-Driven Development

- **Status:** Accepted
- **Date:** 2026-10-04
- **Deciders:** Arthur Medeiros Conceição
- **Tags:** evaluation, observability, llmops, edd

---

## Context

The project's methodology (see `docs/methodology.md`) places **Eval-Driven 
Development (EDD)** as the central principle. The evaluation harness is 
built before the orchestration logic. This is not a stylistic preference — 
it is a structural constraint that the project's value proposition depends on.

Two distinct problems must be solved:

1. **Evaluation** — before shipping a prompt, model, or agent change, we must 
   know whether it improves or regresses quality, measured against a golden 
   dataset with ground truth.
2. **Observability** — once in production, every LLM call must be traceable 
   (cost, latency, tokens, inputs, outputs) so that failures, regressions, 
   and costs are visible rather than discovered by accident.

These are related but distinct. Evaluation is offline, deterministic, and 
CI-driven. Observability is online, real-time, and exploratory. A single 
tool rarely serves both well.

Constraints:

- **Open-source or self-hostable** — no exclusive SaaS lock-in
- **Python-native** — the pipeline is Python; the tooling must not require a 
  separate stack
- **CI-compatible** — evaluations must run automatically on every push
- **Priced for a solo developer** — free tiers must be usable
- **Proven** — tools used in production by serious teams, not experimental

---

## Decision

Adopt a **two-tool stack**:

- **Promptfoo** — for offline evaluation (prompt testing, regression 
  detection, comparison across models and prompt variants)
- **Langfuse** — for online observability (tracing, cost tracking, latency, 
  token accounting, production feedback loops)

These tools are complementary, not alternatives. Promptfoo answers "does 
this change make quality better or worse?" Langfuse answers "what is 
happening in production right now?"

---

## Alternatives Considered

### Alternative 1: Single-tool approach (Promptfoo only)

**Description:** Use Promptfoo for evaluations and skip observability, or 
use it as a crude production logger.

**Pros:**
- Simpler stack
- Less to learn
- One tool, one mental model

**Cons:**
- **No production tracing** — Promptfoo runs offline against a fixed 
  dataset; it does not instrument live calls
- **No cost/latency tracking in production** — the metrics that matter for 
  operations are not captured
- **No user feedback loop** — production queries cannot easily become 
  evaluation cases

**Why rejected:** observability and evaluation answer different questions. 
Skipping either creates a blind spot.

### Alternative 2: Single-tool approach (Langfuse only)

**Description:** Use Langfuse for everything, including evaluations.

**Pros:**
- One tool
- Langfuse has eval features (scores, datasets, LLM-as-judge)

**Cons:**
- **Evaluation is not the primary focus** — Langfuse is designed for 
  observability first
- **CI integration is less mature** — Promptfoo is built for CI/CD pipelines
- **Local-first evaluation is weaker** — Promptfoo can run fully offline 
  and produce shareable outputs
- **Golden dataset management** — Promptfoo's YAML-based approach is more 
  ergonomic for version-controlled evaluation suites

**Why rejected:** Langfuse's eval features are a nice complement, not a 
replacement for a tool designed from the ground up for evaluation.

### Alternative 3: Custom evaluation harness (pure pytest)

**Description:** Write evaluations as pytest tests, no dedicated tooling.

**Pros:**
- Full control
- No new tool
- Integration with existing test infrastructure

**Cons:**
- **No standard format** — everything is bespoke
- **No comparison UI** — comparing prompt variants requires custom tooling
- **No LLM-as-judge primitives** — must be implemented from scratch
- **Slower iteration** — adding a new test case requires writing Python code, 
  not adding YAML

**Why rejected:** custom harnesses tend toward fragile, undocumented, 
hard-to-extend code. The problem is common enough that mature tooling exists.

### Alternative 4: Promptfoo + Langfuse (chosen)

**Description:** Two specialised tools, each solving its own problem, integrated 
via shared data flow.

**Pros:**
- **Clear separation of concerns** — offline eval (Promptfoo) and online 
  trace (Langfuse)
- **CI-native** — Promptfoo runs in GitHub Actions with structured output
- **Production-native** — Langfuse records every LLM call automatically
- **Feedback loop** — production traces can become evaluation cases 
  (Langfuse → Promptfoo)
- **Open-source** — Langfuse is self-hostable, Promptfoo is MIT-licensed
- **Proven** — both tools are used in production by teams ranging from 
  startups to enterprises

**Cons:**
- **Two tools to learn** — combined learning curve is higher than either alone
- **Integration effort** — the feedback loop requires glue code
- **Cost** — Langfuse has a free tier, but at scale becomes paid (self-hosting 
  is available)

**Why chosen:** the tools are complementary and each is best-in-class for 
its role. The combined stack directly implements the project's EDD principle.

---

## Consequences

### Positive
- **EDD is enforceable** — the eval harness runs in CI and blocks regressions
- **Observability is default** — every LLM call is traced automatically
- **Cost visibility** — per-query, per-model, and per-user cost tracking
- **Latency tracking** — p50, p95, p99 per endpoint
- **Feedback loop** — production failures can become evaluation cases
- **Portable** — Langfuse can be self-hosted; Promptfoo runs anywhere Node runs
- **Version-controlled** — evaluation datasets and configs live in the repo

### Negative
- **Two-tool cognitive load** — onboarding requires understanding both
- **Setup complexity** — API keys, self-host option, CI integration
- **Storage** — Langfuse traces accumulate; retention policy required
- **Cost at scale** — free tier of Langfuse Cloud caps monthly traces

### Neutral
- **Promptfoo uses Node** — the CI job runs Node 22 for this step
- **Langfuse can be self-hosted later** — the code uses the standard SDK, 
  so switching hosts is a config change
- **Golden dataset format is Promptfoo-native** — it lives in `evals/golden_dataset.json`

### Follow-up actions
- [ ] Create Promptfoo configuration for each evaluation type as phases land
- [ ] Wire Langfuse SDK into the FastAPI layer and LangGraph nodes
- [ ] Document the "from trace to test case" workflow in `docs/methodology.md`
- [ ] Define retention policy for Langfuse traces (30, 90, 365 days?)
- [ ] Benchmark the cost of running full eval suite per push

---

## References

- [Promptfoo documentation](https://www.promptfoo.dev/docs/)
- [Langfuse documentation](https://langfuse.com/docs)
- [Evaluation-Driven Development (external reference)](https://hamel.dev/blog/posts/evals/)
- `docs/methodology.md` — EDD is the first principle of this project
- ADR-004 — LangGraph (integrates with Langfuse for node-level tracing)