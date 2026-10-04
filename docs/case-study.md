# Case Study — Rádio Transforma AI Content Intelligence Pipeline

> A solo engineering project applying Eval-Driven Development to a real 
> content problem in Portuguese independent media.

**Status:** In progress — Phase 0 complete, pipeline implementation pending.
**Last updated:** 2026-10-04
**Author:** Arthur Medeiros Conceição

---

## 1. Executive Summary

*To be written when the pipeline reaches V0.1. This section will summarise 
the problem, the approach, the measured results, and the business impact — 
in that order — in fewer than 200 words. No results will be claimed before 
they are measured.*

---

## 2. The Problem

### 2.1 Context

**Rádio Transforma.pt** is a Portuguese online radio station producing 
editorial content across shows, interviews, and short-form political 
commentary. The archive has accumulated **hundreds of hours of audio** that 
is currently:

- **Inaccessible for search** — finding a past comment requires listening 
  through entire programs
- **Not reusable** — a strong quote or a recurring theme cannot be easily 
  extracted for editorial repurposing
- **Not measurable** — there is no way to know which topics dominate, which 
  themes recur, or how the editorial line has evolved over time

### 2.2 Constraints

- **No dedicated engineering team.** The station operates with minimal 
  technical overhead.
- **Portuguese (PT-PT) content.** Most off-the-shelf speech tools are 
  optimised for PT-BR or English. European Portuguese requires careful 
  model selection.
- **Privacy-sensitive.** Some content is unpublished and should not be 
  processed by third-party services without explicit consent.
- **Cost-conscious.** The project must remain economically viable at scale.

### 2.3 The question this project answers

*Can a solo engineer, using an open-source stack and evaluation-driven 
development, build a production-grade content intelligence pipeline for a 
real media organisation — with measurable, defensible quality — in a 
bounded timeframe?*

---

## 3. The Approach

### 3.1 Guiding principle: Eval-Driven Development

The pipeline is built around a single principle: **the evaluation harness 
is constructed before the orchestration logic** (see 
[`methodology.md`](methodology.md)). Every component — transcription, 
extraction, retrieval, agent — is measured against a golden dataset with 
ground truth before it is considered complete.

This is not stylistic. It is the mechanism by which the project's central 
claim — "quality is measured, not assumed" — becomes verifiable rather 
than rhetorical.

### 3.2 The four phases

| Phase | Responsibility | Stack |
|---|---|---|
| **0** | EDD & contracts — golden dataset, eval harness, data schemas | Promptfoo, Langfuse, Pydantic |
| **1** | Ingestion — audio capture, transcription, storage | Modal, faster-whisper, Supabase |
| **2** | Orchestration — extraction, retrieval, agents | PydanticAI, LangGraph, FastAPI, pgvector |
| **3** | Business automation — deliverables | n8n, webhooks |

Full architecture: [`architecture.md`](architecture.md).

### 3.3 Non-negotiable practices

- **No pipeline code before the eval harness exists.**
- **One contract per inter-module boundary** (see [`contracts/`](contracts/)).
- **Every structural decision recorded as an ADR** (see [`adr/`](adr/)).
- **CI runs linters, tests, and evals on every push.**
- **No invented metrics.** Numbers are reproducible from the harness in `evals/`.

---

## 4. Results

> **Nothing to declare yet.** The pipeline is in Phase 0. Results will be 
> populated as each phase lands and its metrics are measured against the 
> golden dataset.

### 4.1 Planned metrics

| Metric | Target | Method | Status |
|---|---|---|---|
| Transcription accuracy (WER, PT-PT) | < 10% | Golden dataset with manual transcripts | pending |
| Extraction precision (topics, entities) | > 0.85 | Golden dataset with expected JSON | pending |
| RAG context precision | > 0.85 | Ragas-style eval over Q&A pairs | pending |
| RAG context recall | > 0.80 | Same as above | pending |
| Agent latency (p95) | < 5s | Langfuse traces | pending |
| Cost per 1k queries | < $1.00 | Langfuse cost tracking | pending |
| End-to-end task completion rate | > 0.80 | Golden dataset with expected deliverables | pending |

### 4.2 Business-level outcomes (to be measured)

- **Time saved** in editorial research (hours/week)
- **Content repurposed** from archive (new deliverables/month)
- **Cost per deliverable** vs. manual baseline

---

## 5. Technical Decisions

Every structural decision is recorded as an Architecture Decision Record. 
The current set:

| ADR | Decision | Status |
|---|---|---|
| [ADR-001](adr/001-whisper-for-transcription.md) | faster-whisper for transcription | Accepted |
| [ADR-002](adr/002-modal-for-serverless-batch.md) | Modal for serverless batch processing | Accepted |
| [ADR-003](adr/003-supabase-pgvector-unified-storage.md) | Supabase + pgvector for unified storage | Accepted |
| [ADR-004](adr/004-langgraph-for-agent-orchestration.md) | LangGraph for agent orchestration | Accepted |
| [ADR-005](adr/005-promptfoo-langfuse-edd-stack.md) | Promptfoo + Langfuse for EDD | Accepted |

These decisions are not just technical — they carry trade-offs. Each ADR 
documents the alternatives that were considered and rejected, and why.

---

## 6. What Was Learned

*To be written at V0.1. This section will capture:*

- *What the EDD approach actually changed in engineering practice*
- *Where the golden dataset was hardest to build (and why)*
- *Which architectural bets paid off and which did not*
- *The gap between "runs locally" and "runs in CI" for LLM systems*
- *Honest retrospective on what would be done differently*

---

## 7. Timeline

| Milestone | Date | Status |
|---|---|---|
| Phase 0 — EDD foundations complete | 2026-10-04 | done |
| Phase 1 — Ingestion working end-to-end | TBD | pending |
| Phase 2 — Retrieval + agent with measured precision | TBD | pending |
| Phase 3 — First automated deliverable | TBD | pending |
| V0.1 public release | TBD | pending |

---

## 8. Artifacts

- **Repository:** [github.com/Arthur-Medeiros-C/radio-transforma-pipeline](https://github.com/Arthur-Medeiros-C/radio-transforma-pipeline)
- **Golden dataset:** [`evals/golden_dataset.json`](../evals/golden_dataset.json)
- **Evaluation config:** [`evals/config/promptfoo.yaml`](../evals/config/promptfoo.yaml)
- **Architecture:** [`architecture.md`](architecture.md)
- **Methodology:** [`methodology.md`](methodology.md)
- **ADRs:** [`adr/`](adr/)
- **Data contracts:** [`contracts/`](contracts/)

---

## 9. Related Documents

- [`methodology.md`](methodology.md) — process and principles
- [`architecture.md`](architecture.md) — system design
- [`contracts/`](contracts/) — data contracts and data flow
- [`adr/`](adr/) — decision records

---

*This case study will be rewritten once real results exist. It is a 
skeleton, not a claim.*