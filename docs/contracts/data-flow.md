# Data Flow

> How the four contracts move through the four phases of the pipeline.
> This document is the map; the models themselves are the territory.

---

## 1. End-to-end flow

```mermaid
flowchart LR
    subgraph Phase1["Phase 1 — Ingestion"]
        A1[Audio file]
        A2[AudioSegment]
        A3[faster-whisper]
        A4[Transcript]
    end

    subgraph Phase2["Phase 2 — Orchestration"]
        B1[PydanticAI]
        B2[ExtractedData]
        B3[Embeddings]
        B4[pgvector]
        B5[Query]
        B6[RetrievalResult]
        B7[LangGraph Agent]
        B8[AgentResponse]
    end

    subgraph Phase3["Phase 3 — Automation"]
        C1[n8n]
        C2[Deliverable]
    end

    A1 --> A2
    A2 --> A3
    A3 --> A4
    A4 --> B1
    B1 --> B2
    B2 --> B3
    B3 --> B4
    B4 --> B6
    B5 --> B6
    B6 --> B7
    B7 --> B8
    B8 --> C1
    C1 --> C2