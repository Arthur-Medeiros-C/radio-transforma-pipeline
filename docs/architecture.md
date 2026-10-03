# Architecture

> System design for the Rádio Transforma content intelligence pipeline.
> For methodology and process, see [`methodology.md`](methodology.md).

**Status:** Phase 0 — definitions in progress. This document evolves with 
the system; decisions are recorded as ADRs in [`adr/`](adr/).

---

## 1. Business Context

**Client:** Rádio Transforma.pt (Portuguese online radio)
**Problem owner:** editorial team producing commentary content from reels 
and interviews
**Core pain:** hundreds of hours of audio content are inaccessible for 
search, reuse, or editorial repurposing

**What "solved" looks like:**

1. Any piece of past content can be found by semantic query
2. The editorial team can generate new derived content (digests, 
   newsletters, quotes, timelines) without listening to raw audio
3. The system measures its own quality — no "looks good" validation

---

## 2. System Overview

```mermaid
graph TD
    A[Raw Audio Sources] -->|n8n trigger| B[Ingestion Layer]
    B -->|batch job| C[Modal Serverless GPU]
    C -->|faster-whisper| D[Transcripts]
    D -->|PydanticAI| E[Structured Data]
    E -->|upsert| F[(Supabase + pgvector)]
    F -->|hybrid retrieval| G[LangGraph Agents]
    G -->|FastAPI| H[Public API]
    H -->|webhook| I[n8n Automations]
    I --> J[Deliverables]

    K[Promptfoo] -.->|eval| G
    L[Langfuse] -.->|trace| C
    L -.->|trace| G
    