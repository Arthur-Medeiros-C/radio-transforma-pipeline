# Data Contracts

> Every inter-module data flow in the pipeline is defined by a Pydantic 
> model in `src/radio_transforma/models/`. This directory documents what 
> those contracts mean, why they are shaped the way they are, and how they 
> move through the system.

**Status:** Phase 0 — contracts defined, pipeline implementation pending.
**Source of truth:** [`src/radio_transforma/models/`](../../src/radio_transforma/models/)

---

## 1. Why data contracts come first

In an Eval-Driven Development workflow (see [`../methodology.md`](../methodology.md)), 
the measuring apparatus is built before the pipeline code. Data contracts 
are part of that apparatus.

They exist so that:

1. **Modules can be tested in isolation.** A transcription module can be 
   tested by asserting the shape of its output without running the full 
   pipeline.
2. **Integration does not silently break.** If a module's output stops 
   matching the next module's expected input, the failure is caught at the 
   boundary — not three phases later.
3. **The pipeline has a stable interface.** We can swap the underlying 
   implementation (e.g., change transcription model) without rewriting 
   everything downstream.
4. **Documentation is executable.** The Pydantic models *are* the 
   specification. Tests validate that specification.

The rule: **no module accepts or returns raw dicts at its public boundary.** 
Every inter-module interaction uses one of the models defined below.

---

## 2. The four contracts

### 2.1 `AudioSegment` — Input to the pipeline

**Location:** [`src/radio_transforma/models/audio.py`](../../src/radio_transforma/models/audio.py)
**Used in:** Phase 1 (ingestion)
**Represents:** a single audio file (reel, interview clip, program excerpt) 
to be processed.

**Key invariants:**
- `duration_seconds > 0`
- Language follows BCP-47 (e.g., `pt-PT`)
- At least one of `audio_path` or `audio_url` must be provided
- Immutable (frozen) once created

**Traceability fields:**
- `id` — stable identifier, referenced by everything downstream
- `checksum_sha256` — optional content hash for integrity verification
- `ingested_at` — timestamp with timezone

**Source enum:** `AudioSource` distinguishes between `instagram_reel`, 
`interview`, `program`, `manual_upload`, `other`.

---

### 2.2 `Transcript` / `TranscriptSegment` — Output of transcription

**Location:** [`src/radio_transforma/models/transcript.py`](../../src/radio_transforma/models/transcript.py)
**Used in:** Phase 1 (transcription) → Phase 2 (extraction, retrieval)
**Represents:** the textual representation of an audio segment, with 
timestamps.

**Structure:**
- A `Transcript` is a collection of `TranscriptSegment`s.
- Each segment has `start`, `end` (seconds), `text`, and optional `speaker` 
  and `confidence`.

**Key invariants:**
- `end > start` on every segment (validated on construction)
- `audio_id` references the `AudioSegment.id` this transcript belongs to
- `wer` (Word Error Rate) is optional — populated only when the transcript 
  is evaluated against a golden dataset
- `full_text` property concatenates all segment texts

**Why segments and not one big string:** segment boundaries are needed 
for citation (`transcript_id::segment_id`), for timestamped retrieval, and 
for alignment with the source audio.

---

### 2.3 `ExtractedData` — Structured semantics from a transcript

**Location:** [`src/radio_transforma/models/extraction.py`](../../src/radio_transforma/models/extraction.py)
**Used in:** Phase 2 (extraction)
**Represents:** the semantic structure extracted from a transcript.

**Composition:**
- `topics` — list of `Topic(name, confidence)`
- `entities` — list of `Entity(name, type, mentions)`, where `type` is one 
  of `EntityType` values
- `quotes` — list of `Quote(text, position, start, end)`
- `sentiment` — free-text label (e.g., `"neutral_analytical"`)

**Key invariants:**
- `transcript_id` references the source transcript
- `model` records which LLM produced the extraction (for reproducibility)
- All collections default to empty lists

**Why the schema is minimal:** V0.1 extraction must be provably correct 
against a small golden dataset. Fields will be added only when a real 
downstream need demands them. Adding fields to the schema before they are 
used is speculation, not design.

---

### 2.4 `Query` / `RetrievalResult` / `AgentResponse` — Output side

**Location:** [`src/radio_transforma/models/query.py`](../../src/radio_transforma/models/query.py)
**Used in:** Phase 2 (retrieval, agents)
**Represents:** the request-response cycle for the knowledge base.

**Three distinct contracts, three distinct concerns:**

| Contract | Role |
|---|---|
| `Query` | Input — what the caller asks for |
| `RetrievalResult` | Intermediate — a single retrieved chunk with its score |
| `AgentResponse` | Output — the synthesised answer, with citations and metrics |

**Key invariants:**
- `Query.top_k` is bounded between 1 and 50
- `RetrievalResult.score` is bounded between 0.0 and 1.0
- `AgentResponse.latency_ms` is always recorded (production observability)
- `AgentResponse.cost_usd` is optional (populated when Langfuse returns cost)
- `Citation.source_id` uses the format `transcript_id::segment_id`

**Why three models and not one:** the pipeline has three distinct 
consumers — the API caller (Query), the retrieval layer (RetrievalResult), 
and the client (AgentResponse). Conflating them would force every consumer 
to carry fields it does not use.

---

## 3. Contract rules

**Rule 1 — Immutability.** All contracts use `model_config = ConfigDict(frozen=True)`. 
Once a model is created, its fields cannot be mutated. Changes produce new 
instances. This eliminates a class of bugs where a shared object is 
silently modified across module boundaries.

**Rule 2 — Strictness.** All contracts use `extra="forbid"`. Passing an 
unknown field raises `ValidationError`. This catches typos and schema drift 
early.

**Rule 3 — Validation at boundaries.** Numeric fields carry `gt`, `ge`, `lt`, 
`le` constraints. String fields carry `min_length` or regex `pattern` where 
format matters (language tags, SHA-256 hashes). Validation errors surface 
at the point where bad data enters the system, not downstream.

**Rule 4 — Timezone-aware timestamps.** All `created_at` and `ingested_at` 
fields use `datetime.now(UTC)`. Naive datetimes are rejected by convention 
(no field accepts them).

**Rule 5 — Reference, don't embed.** Contracts reference other entities by 
`id` (e.g., `Transcript.audio_id`), not by embedding full objects. The full 
object is retrieved when needed. This keeps contracts small, makes 
serialisation predictable, and avoids deep object graphs.

---

## 4. What is deliberately *not* in the contracts

- **File bytes or audio content.** Contracts reference audio by path or URL; 
  they never carry binary payloads.
- **Embeddings.** Embeddings are generated and stored in the vector column 
  of the corresponding Postgres row; they are not part of any Pydantic model.
- **Secrets or credentials.** No contract carries API keys, tokens, or 
  connection strings. Configuration lives in `src/radio_transforma/config.py`.
- **Internal implementation details.** Contracts describe *what* data flows, 
  not *how* it is produced.

---

## 5. Adding a new contract

Before adding a model to `src/radio_transforma/models/`:

1. **Confirm it is needed.** A new contract is justified only when an 
   inter-module boundary requires it. Internal data structures within a 
   single module do not need to be contracts.
2. **Name it precisely.** `AudioSegment`, not `Audio`. `AgentResponse`, not 
   `Response`. The name should be unambiguous without context.
3. **Define invariants first.** Before writing fields, write the tests that 
   assert what "valid" and "invalid" mean.
4. **Add a section here.** This document is the index — a contract that is 
   not documented here does not exist.
5. **Update the diagram.** [`data-flow.md`](data-flow.md) shows how the new 
   contract fits.

---

## 6. Related documents

- [`data-flow.md`](data-flow.md) — how contracts move between phases
- [`../architecture.md`](../architecture.md) — full system design
- [`../methodology.md`](../methodology.md) — EDD principles
- [`../../src/radio_transforma/models/`](../../src/radio_transforma/models/) — the models themselves

---

*Contracts are the interface. Everything else is implementation.*