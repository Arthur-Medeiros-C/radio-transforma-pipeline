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

**Regras operacionais (adicionadas 2026-10-06 após incidentes):**

- **Convenção de testes:** unit tests vivem em `tests/unit/`. Integration tests
  (rede real, SDKs live, LLMs) vivem em `tests/integration/` com marcador
  `@pytest.mark.integration` e não correm em CI por omissão. Evals vivem em
  `evals/` na raiz, geridos pelo Promptfoo — não são pytest.
- **Cobertura 100% por módulo é critério de bloco, não de sorte.** Cada ramo
  defensivo (`try/except`, validações, fallbacks) tem pelo menos um teste.
- **Antes de qualquer `git commit --amend`:** correr `git status`. Se o commit
  alvo já está em `origin/main`, **não se emenda** — faz-se um commit novo por
  cima. `--amend` só é permitido no commit ainda não pusheado da sessão atual.
- **Nunca `git push --force`.** Apenas `--force-with-lease`, e só se houver
  razão documentada (ex.: amend local antes de push).
- **Comando de verificação canónico (correr antes de cada commit):**

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

### 2.8 Test & coverage conventions

- **Localização:** todos os unit tests em `tests/unit/`.
- **Cobertura exigida:** 100% por módulo antes do commit.
- **Mocking:** preferir `MagicMock` sobre `pytest-mock`. Fixtures locais por
  ficheiro de teste; sem conftest global até haver duplicação real.
- **Ficheiros de teste acompanham o módulo:** `audio_repository.py` ↔
  `tests/unit/test_audio_repository.py`.
- **Supabase SDK compatibility:** o cliente `supabase-py` já devolveu
  respostas como `dict` e como objeto em versões diferentes. Testes cobrem
  ambos os ramos em `_data()` (ver `transcript_repository.py`).

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

### Block 2 — `src/radio_transforma/storage/audio_repository.py` ✅ DONE

- Commit: `c36ca3a` — `feat(storage): add AudioRepository for Supabase Storage`
- Interface: `upload`, `download`, `create_signed_url`, `exists`, `delete`.
- `AudioRepositoryError(RuntimeError)` como excepção de domínio.
- Validação estrita de path (relativo, sem `..`, não vazio).
- Compatível com múltiplas formas de resposta de signed URL
  (`signedURL` / `signed_url` / `signedUrl`).
- **32 testes unitários, 100% de cobertura no módulo.**
- **Fora do escopo:** bucket provisioning, validação de conteúdo,
  metadata em Postgres. Bucket `audio` é criado manualmente na consola Supabase.
- CI verde.

### Block 3 — `src/radio_transforma/storage/transcript_repository.py` ✅ DONE

- Commit: `3d6b3d0` — `feat(storage): add TranscriptRepository for Postgres (Supabase)`
- Esquema relacional **normalizado** (decisão B):
  - `transcripts` (id, audio_id, language, model, wer, created_at)
  - `transcript_segments` (id, transcript_id, position, start_s, end_s, text, confidence)
  - FK `transcript_id` com `ON DELETE CASCADE`; `UNIQUE (transcript_id, position)`;
    `CHECK (end_s > start_s)`.
- Esquema versionado em `docs/schema/001_transcripts.sql`. Aplicação manual
  na consola Supabase (sem migrações automáticas nesta fase).
- Interface: `save`, `get`, `list_for_audio`, `delete`.
- `TranscriptRepositoryError(RuntimeError)` como excepção de domínio.
- **Rollback best-effort:** se o batch insert de segmentos falhar, o
  transcript-pai é removido. Não há transação cross-request no `supabase-py`.
- **26 testes unitários, 100% de cobertura no módulo.**
- **Fora do escopo:** embeddings (Fase 2), lógica de transcrição
  (`TranscriptionService`), audio blobs (`AudioRepository`).
- CI verde.

### Block 4 — `src/radio_transforma/transcription/service.py` (NEXT)

- **Responsabilidade:** transcrever `AudioSegment` → `Transcript` usando
  faster-whisper (`large-v3`), com isolamento do modelo (lazy loading) e
  injeção de dependência para testabilidade.
- **Fora do escopo:** download do áudio (usa `AudioRepository`),
  persistência (usa `TranscriptRepository`), Modal wrapper (Block 5).
- **Interface pública (aproximada):**

  ```python
  class TranscriptionService:
      def __init__(self, model_factory: Callable[[], WhisperModel] | None = None): ...
      def transcribe(self, audio_path: Path, *, language: str = "pt-PT") -> Transcript: ...
