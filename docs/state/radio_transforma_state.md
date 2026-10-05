# radio_transforma_state.md

> Ponto de restauro consolidado. Última actualização: 2026-10-05.
> Colar como primeira mensagem em qualquer sessão de retoma.
> Guardado em `docs/state/` — versionado com o código.

---

## 1. OBJECTIVE & METHODOLOGY

### 1.1 Macro objective

Build a **production-grade AI content intelligence pipeline** for
Rádio Transforma.pt (Portuguese independent online radio). The system
must transform hundreds of hours of unstructured audio into a semantically
searchable, reusable knowledge base — with **measurable, defensible quality**.

This project is also the **flagship portfolio case** for positioning as
AI Automation Engineer. The quality bar is not "works in a demo" — it is
"works in production, with metrics published".

### 1.2 Central methodology — Eval-Driven Development (EDD)

**The evaluation harness is built before the orchestration logic.**

- The golden dataset is created in Phase 0, before any pipeline code.
- The eval harness (Promptfoo + Langfuse) is wired up in Phase 0.
- Every subsequent change (prompt, model, tool, retrieval) is validated
  against the harness. If it does not improve the metric, it does not ship.
- Metrics are published in the README — not hidden in a notebook.

### 1.3 Modularização Extrema

- One module per responsibility. One commit per logical unit.
- **No "big bang" commits.** Every commit is small, verifiable, and passes CI.
- Each module is testable in isolation before integration.
- No module advances before the previous one has green tests.

### 1.4 Four-phase structure

| Phase | Responsibility | Stack |
|---|---|---|
| 0 | EDD & contracts — golden dataset, eval harness, data schemas | Promptfoo, Langfuse, Pydantic |
| 1 | Ingestion — audio capture, transcription, storage | Modal, faster-whisper, Supabase |
| 2 | Orchestration — extraction, retrieval, agents | PydanticAI, LangGraph, FastAPI, pgvector |
| 3 | Business automation — deliverables | n8n, webhooks |

---

## 2. PHASE 0 — COMPLETE (17 COMMITS)

### 2.1 Repository

- **URL:** https://github.com/Arthur-Medeiros-C/radio-transforma-pipeline
- **Visibility:** Public
- **Local path:** `C:\Users\arthu\Projects\radio-transforma-pipeline`
- **Branch:** `main`

### 2.2 Commit log (chronological)

**Phase 0 (1–17):**

1. `chore: initial project structure and methodology`
2. `docs: add project README with EDD-first structure`
3. `docs: add system architecture and initial ADRs`
4. `feat: add centralised configuration with typed settings`
5. `chore: migrate to dependency-groups syntax (uv)`
6. `ci: add GitHub Actions workflow for lint, test and eval`
7. `ci: fix workflow configuration and commit lockfile`
8. `style: apply ruff formatting to config and tests`
9. `feat(evals): add golden dataset skeleton and promptfoo config`
10. `feat(models): add data contracts for audio, transcript, extraction and query`
11. `fix: unblock src models package from gitignore`
12. `style: modernise type annotations and enums in models`
13. `style: apply ruff format to models and tests`
14. `docs(adr): add Modal and Supabase decision records`
15. `docs(adr): add LangGraph and EDD stack decision records`
16. `docs(contracts): add data contracts documentation and flow map`
17. `docs: add case study skeleton`

**Phase 1 (18–19):**

18. `test(config): make defaults tests hermetic against local .env`
19. `feat(storage): add Supabase client factory with typed settings` — **Block 1 ✅**

**Historical failures are preserved intentionally** — they document real
problem-solving. They are part of the engineering narrative.

### 2.3 CI/CD — green

`.github/workflows/ci.yml` runs on every push to `main`:

**Job 1 — Lint & Test:**
- `uv sync --all-extras`
- `ruff check src tests`
- `ruff format --check src tests`
- `mypy src` (continue-on-error)
- `pytest -v --cov=src/radio_transforma`

**Job 2 — Eval Harness (main only):**
- Runs only if `evals/config/promptfoo.yaml` exists
- Currently runs the sanity test

**Status:** Green on commit `47ceb66` (last).

### 2.4 Stack (locked)

**Languages & backend:**
- Python 3.11.9
- FastAPI, Pydantic 2, pydantic-settings

**AI / LLM:**
- LangGraph, PydanticAI
- OpenRouter (remote), Ollama (local)

**Data & storage:**
- Supabase (PostgreSQL + pgvector + Storage)
- Baserow (planned)
- Pandas

**Media:**
- faster-whisper, Docling, FFmpeg

**Infrastructure:**
- Modal (serverless GPU)
- Docker, Git, GitHub Actions
- Vercel (future)

**LLMOps / Evaluation:**
- Langfuse (observability)
- Promptfoo (evaluation)
- pytest, pytest-asyncio, pytest-cov
- ruff, mypy

**Package manager:** `uv` 0.12.16

### 2.5 Data contracts (implemented + tested)

Location: `src/radio_transforma/models/`

| Model | File | Responsibility |
|---|---|---|
| `AudioSegment`, `AudioSource` | `audio.py` | Input to pipeline |
| `Transcript`, `TranscriptSegment` | `transcript.py` | Transcription output |
| `ExtractedData`, `Topic`, `Entity`, `EntityType`, `Quote` | `extraction.py` | Semantic extraction output |
| `Query`, `RetrievalResult`, `Citation`, `AgentResponse` | `query.py` | Query and agent I/O |

**All contracts:** frozen (immutable), `extra="forbid"`, validated at
construction, timezone-aware timestamps.

**Test coverage:** 64 unit tests, all green in CI.

### 2.6 Golden dataset (skeleton)

Location: `evals/golden_dataset.json`

- 8 seed cases (6 synthetic + 2 placeholders)
- 2 per eval type: transcription, extraction, retrieval, agent
- Target: 20 cases (5 per type) — grows with real audio
- Schema ready for all 4 types

### 2.7 Eval harness (skeleton)

Location: `evals/config/promptfoo.yaml`

- Minimal valid config
- Runs in CI as sanity check
- Will expand per phase

---

## 3. ARCHITECTURAL DECISIONS (5 ADRs)

Full detail in `docs/adr/`.

### ADR-001 — faster-whisper for transcription

- **Decision:** Use faster-whisper (`large-v3`) for PT-PT audio transcription
- **Rejected:** OpenAI Whisper API (cost, privacy), local `openai-whisper`
  (4x slower), cloud speech APIs (PT-PT quality, lock-in)
- **Why:** cost control, privacy, PT-PT quality, full control

### ADR-002 — Modal for serverless batch

- **Decision:** Use Modal for batch transcription and heavy workloads
- **Rejected:** persistent GPU worker (idle cost), RunPod/Vast.ai
  (ops overhead), Cloud Run/Fargate (no GPU or immature)
- **Why:** pay-per-use, native parallelism, zero infrastructure

### ADR-003 — Supabase + pgvector unified storage

- **Decision:** Single Postgres instance for relational + vector data
- **Rejected:** separate vector DB (sync complexity, cost), local Postgres
  (backup risk), pure cloud DBs (lock-in)
- **Why:** single source of truth, SQL-native hybrid retrieval, zero ops

### ADR-004 — LangGraph for agents

- **Decision:** LangGraph for stateful multi-step workflows
- **Rejected:** plain Python functions (no state/retry), LangChain
  sequential chains (wrong abstraction), LlamaIndex agents
  (retrieval-first bias)
- **Why:** explicit state, cycles, checkpoints, Langfuse integration

### ADR-005 — Promptfoo + Langfuse for EDD

- **Decision:** Two-tool stack — Promptfoo (offline eval), Langfuse (online tracing)
- **Rejected:** Promptfoo only (no prod tracing), Langfuse only (weak CI),
  custom pytest harness (bespoke, fragile)
- **Why:** separation of concerns, both best-in-class, open-source

---

## 4. PHASE 1 — IN PROGRESS

**Rule:** Each block is one commit. Each block passes tests before the next begins.

### Block 1 — `src/radio_transforma/storage/supabase_client.py` ✅ DONE

- Commit: `47ceb66` — `feat(storage): add Supabase client factory with typed settings`
- Factory memoizada com `@lru_cache(maxsize=1)`.
- Lê config via `get_settings()` (já existente desde Phase 0).
- Preferência de chave: `service_role` → fallback `anon`.
- `SecretStr.get_secret_value().strip()` para extracção segura.
- `SupabaseClientError(RuntimeError)` como excepção de domínio.
- `reset_supabase_client()` para isolamento de testes.
- **7 testes unitários, todos com mocks, cobertura 100%.**
- CI verde.

### Block 2 — `src/radio_transforma/storage/audio_repository.py`

- **Responsabilidade:** upload/download de áudio para Supabase Storage; signed URLs.
- **Fora do escopo:** tabelas Postgres, validação de conteúdo, bucket creation (setup manual).
- **Interface pública (aproximada):**

  ```python
  class AudioRepository:
      def __init__(self, client: Client, bucket: str = "audio"): ...
      def upload(self, path: str, data: bytes, *, content_type: str) -> str: ...
      def download(self, path: str) -> bytes: ...
      def create_signed_url(self, path: str, *, expires_in: int = 3600) -> str: ...
      def exists(self, path: str) -> bool: ...
      def delete(self, path: str) -> None: ...
