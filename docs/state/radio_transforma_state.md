# radio_transforma_state.md

> Ponto de restauro consolidado. Última actualização: 2026-10-07.
> Colar como primeira mensagem em qualquer sessão de retoma.
> Guardado em `docs/state/` — versionado com o código.
>
> **Living document.** Este ficheiro reflecte o último commit verde em `main`.
> Se está desactualizado, é bug. Actualiza antes de continuar.

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

### 1.3 Modularização Extrema & regras operacionais

- One module per responsibility. One commit per logical unit.
- **No "big bang" commits.** Every commit is small, verifiable, passes CI.
- Each module is testable in isolation before integration.
- No module advances before the previous one has green tests.

**Regras operacionais (codificadas após incidentes reais):**

- **Convenção de testes:** unit tests em `tests/unit/`. Integration tests
  (rede real, SDKs live, LLMs) em `tests/integration/` com marcador
  `@pytest.mark.integration`, não correm em CI por omissão. Evals em `evals/`
  na raiz, geridos pelo Promptfoo — não são pytest.
- **Cobertura 100% por módulo é critério de bloco, não de sorte.** Cada ramo
  defensivo (`try/except`, validações, fallbacks) tem pelo menos um teste.
- **Antes de qualquer `git commit --amend`:** correr `git status`. Se o commit
  alvo já está em `origin/main`, **não se emenda** — faz-se commit novo por
  cima. `--amend` só é permitido no commit ainda não pusheado da sessão actual.
- **Nunca `git push --force`.** Apenas `--force-with-lease`, e só com razão
  documentada (ex.: amend local antes de push).
- **Editar ficheiros grandes:** preferir substituição integral do ficheiro a
  "substituir a secção X". Menos margem para falhas parciais silenciosas.
- **Pager do Git em Windows:** `git config --global core.pager ""` ou usar
  `git --no-pager <cmd>` para evitar ficar preso no `less`.
- **`ruff check --fix` antes de `ruff check`.** `ruff format` normaliza
  formatação; **não** reordena imports. Erros `I001` persistem após
  `ruff format` e só são resolvidos com `ruff check --fix`. Aplicar o `--fix`
  no início da cadeia de verificação evita falsos alarmes no CI.
- **Verificação mecânica de números:** sempre que este ficheiro citar
  contagens de testes, SHAs, ou totais de commits, o número é lido do output
  real do `pytest`/`git log` — não copiado de mensagens de commit.

**Comando de verificação canónico (correr antes de cada commit):**

```bash
ruff check --fix src tests; ruff format src tests; ruff check src tests; ruff format --check src tests; pytest tests/unit --cov=src/radio_transforma --cov-report=term-missing
```

Só commitar se: `All checks passed!`, `NN files already formatted`, `N passed`,
`TOTAL 100%`.

### 1.4 Four-phase structure

| Phase | Responsibility | Stack |
|---|---|---|
| 0 | EDD & contracts — golden dataset, eval harness, data schemas | Promptfoo, Langfuse, Pydantic |
| 1 | Ingestion — audio capture, transcription, storage | Modal, faster-whisper, Supabase |
| 2 | Orchestration — extraction, retrieval, agents | PydanticAI, LangGraph, FastAPI, pgvector |
| 3 | Business automation — deliverables | n8n, webhooks |

---

## 2. PHASE 0 — COMPLETE

### 2.1 Repository

- **URL:** https://github.com/Arthur-Medeiros-C/radio-transforma-pipeline
- **Visibility:** Public
- **Local path:** `C:\Users\arthu\Projects\radio-transforma-pipeline`
- **Branch:** `main`
- **Último commit verde:** `7cae8b9` — `feat(cli): JSON stdout, 3rd-party noise isolation, --dry-run Null Objects`

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

**Phase 1 (18–28):**

18. `test(config): make defaults tests hermetic against local .env`
19. `feat(storage): add Supabase client factory with typed settings` — **Block 1 ✅**
20. `docs(state): add consolidated state document to repository`
21. `docs: add consulting services and contact links to README`
22. `docs: fix python badge image link`
23. `feat(storage): add AudioRepository for Supabase Storage` — **Block 2 ✅**
24. `feat(storage): add TranscriptRepository for Postgres (Supabase)` — **Block 3 ✅**
25. `docs(state): record Phase 1 blocks 2 and 3 as done`
26. `feat(transcription): add TranscriptionService with faster-whisper` — **Block 4 ✅**
27. `feat(ingestion): add IngestionOrchestrator (audio → transcript)` — **Block 5 ✅**
28. `feat(cli): JSON stdout, 3rd-party noise isolation, --dry-run Null Objects` — **Block 6 ✅**

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

**Status:** Green on `7cae8b9`.

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

**Field notes:**
- `Transcript` requires: `id`, `audio_id`, `language`, `model`, `created_at`,
  `segments` (tuple). Optional: `wer`.
- `TranscriptSegment` requires: `id`, `start`, `end`, `text`. Optional: `confidence`.

**Test coverage:** 210 unit tests, all green in CI, `TOTAL 100%`.

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
- **CLI entrypoints são testados por contrato de stdout.** O stdout é
  machine-readable (JSON puro); texto humano vai para stderr. Testes usam
  `capsys` e validam `json.loads(captured.out)` — nunca `in` sobre texto.

### 2.9 Database schema

Location: `docs/schema/`

- `001_transcripts.sql` — `transcripts` + `transcript_segments`, FK cascade,
  `UNIQUE (transcript_id, position)`, `CHECK (end_s > start_s)`. Aplicação
  manual na consola Supabase (sem migrações automáticas nesta fase).

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
- Lê config via `get_settings()`.
- Preferência de chave: `service_role` → fallback `anon`.
- `SecretStr.get_secret_value().strip()` para extracção segura.
- `SupabaseClientError(RuntimeError)` como excepção de domínio.
- `reset_supabase_client()` para isolamento de testes.
- **7 testes unitários, 100% de cobertura.**
- CI verde.

### Block 2 — `src/radio_transforma/storage/audio_repository.py` ✅ DONE

- Commit: `c36ca3a` — `feat(storage): add AudioRepository for Supabase Storage`
- Interface: `upload`, `download`, `create_signed_url`, `exists`, `delete`.
- `AudioRepositoryError(RuntimeError)` como excepção de domínio.
- Validação estrita de path (relativo, sem `..`, não vazio).
- Compatível com múltiplas formas de resposta de signed URL
  (`signedURL` / `signed_url` / `signedUrl`).
- **36 testes unitários, 100% de cobertura no módulo.**
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
- **24 testes unitários, 100% de cobertura no módulo.**
- **Fora do escopo:** embeddings (Fase 2), lógica de transcrição
  (`TranscriptionService`), audio blobs (`AudioRepository`).
- CI verde.

### Block 4 — `src/radio_transforma/transcription/service.py` ✅ DONE

- Commit: `858db6c` — `feat(transcription): add TranscriptionService with faster-whisper`
- API: `transcribe(audio_id, audio_path, *, language='pt-PT') -> Transcript`.
- **Dependency Injection:** `model_factory: Callable[[], WhisperModel]` é
  injectável; default usa `faster_whisper.WhisperModel` com import lazy.
- **Lazy Loading:** modelo carregado só na primeira chamada, reutilizado
  em chamadas subsequentes via `self._model`.
- `model_name` property exposta para o orquestrador usar na idempotência.
- Confiança derivada de `avg_logprob` via `exp()`, cortada a [0, 1].
- Segmentos com texto vazio são descartados; resultado vazio levanta
  `TranscriptionServiceError`.
- `TranscriptionServiceError(RuntimeError)` como excepção de domínio.
- **29 testes unitários, 100% de cobertura no módulo.**
- **Fora do escopo:** download de áudio (`AudioRepository`), persistência
  (`TranscriptRepository`), Modal wrapper (Block 6).
- CI verde.

### Block 5 — `src/radio_transforma/ingestion/orchestrator.py` ✅ DONE

- Commit: `d236f40` — `feat(ingestion): add IngestionOrchestrator (audio → transcript)`
- **Walking skeleton da Fase 1.**
- Fluxo end-to-end: `idempotency check → upload (if missing) → transcribe → persist`.
- Idempotente em `(audio_id, language, transcriber.model_name)`: chamada
  repetida devolve o transcript existente sem refazer trabalho. Transcripts
  órfãos (0 segmentos) são ignorados e recriados.
- `IngestionError(RuntimeError)` carrega `.stage ∈ {validate, idempotency,
  upload, transcribe, persist}` e `.audio_id`. **Sem retry automático** — a
  política de retry é do caller (n8n, Modal, CLI). Não é uma saga: não há
  compensação de passos anteriores, apenas classificação da falha.
- `IngestionError.__str__` devolve `"[stage] audio_id: message"` — testes
  do CLI verificam este contrato, não assumem a `message` crua.
- **Sem cleanup em falha:** objecto no bucket e ficheiro local preservados
  para retry. Único cleanup é o rollback best-effort já existente no
  `TranscriptRepository.save`.
- Content-type inferido pelo sufixo; sufixos desconhecidos caem para
  `application/octet-stream`.
- **27 testes unitários, 100% de cobertura no módulo.**
- **Fora do escopo:** retry policy (tenacity), checkpoint persistente,
  Modal wrapper (Block 6), tracing Langfuse (Block 7).
- CI verde.

### Block 6 — `src/radio_transforma/cli.py` + `dry_run.py` ✅ DONE

- Commit: `7cae8b9` — `feat(cli): JSON stdout, 3rd-party noise isolation, --dry-run Null Objects`
- **Primeira execução real end-to-end da Fase 1.** `python -m radio_transforma ingest <file> [--audio-id ID] [--language LANG] [--dry-run]`.
- **`--dry-run` com Null Object Pattern** (não `MagicMock`):
  - `src/radio_transforma/dry_run.py` — `NullAudioRepository`,
    `NullTranscriptRepository`, `NullTranscriptionService`.
  - `exists()` devolve `False` (força ramo upload); `get()` devolve `None`
    (força ramo transcribe+persist); `transcribe()` valida existência do
    ficheiro mas devolve `Transcript` sintético de 1 segmento.
  - `NullTranscriptionService.model_name = "dry-run"` — chave de
    idempotência deliberadamente divergente da real.
  - `_build_orchestrator(*, dry_run)` selecciona o ramo; em dry-run,
    `get_supabase_client()` **nunca é chamado** (testado por guard).
- **Contrato de stdout: JSON puro.**
  - Sucesso: `{"status": "success", "audio_id": ..., "segments_count": ..., "dry_run": bool}`.
  - Erro (`IngestionError`): `{"status": "error", "stage": ..., "audio_id": ..., "message": ...}`.
  - Erro inesperado: `{"status": "error", "stage": "unexpected", "audio_id": ..., "message": ...}`.
  - Texto humano (logging, mensagens `ERROR`) vai exclusivamente para `sys.stderr`.
  - Pipeable para `jq`.
- **Isolamento de stdout de terceiros:** context manager
  `_redirect_stdout_to_stderr()` faz `sys.stdout = sys.stderr` durante
  `orchestrator.ingest()`, restaura no `finally`. Cobre faster-whisper,
  tqdm, FFmpeg wrappers.
- **`--audio-id` opcional** com fallback para `Path(file).stem`.
- `logging.basicConfig(stream=sys.stderr)` explícito; logger `faster_whisper`
  fixado em `WARNING` independente do nível global.
- **20 testes unitários** (17 em `test_cli.py`, 12 em `test_dry_run.py`,
  1 em `test___main__.py`), 100% de cobertura nos módulos.
- CI verde.

### Block 7 — NEXT (a decidir)

Candidatos, em ordem de recomendação:

1. **Eval harness com dados reais** — expandir `evals/golden_dataset.json`
   com transcrições reais da Rádio Transforma. Correr `promptfoo` contra o
   `TranscriptionService`. **Primeira medição publicável** — fecha o ciclo
   do EDD prometido em §1.2. Sem isto, o projecto ainda não é "eval-driven"
   em produção.
2. **Modal wrapper** (`src/radio_transforma/transcription/modal_app.py`) —
   serverless GPU conforme ADR-002. Envelopa o CLI/`IngestionOrchestrator`
   já existente. Bloqueado por: bucket Supabase provisionado e credenciais
   configuradas em produção.
3. **Tracing Langfuse** no `IngestionOrchestrator` — emitir spans por stage
   para observar latência real por etapa. Faz mais sentido depois de haver
   execuções reais em Modal (Block 7.2).

**Primeira execução real end-to-end** (fora de dry-run) ainda não ocorreu.
Requer: bucket `audio` criado na consola Supabase + `docs/schema/001_transcripts.sql`
aplicado + credenciais no `.env`. Não é um bloco de código — é setup de
infra. Fica registado como pré-requisito do Block 7.2.
---

## 5. BACKLOG (fora da Fase 1, registado para não esquecer)

- **Retry automático** com `tenacity` sobre `stage="transcribe"` (3 tentativas,
  backoff exponencial). Commit curto, quando doer.
- **Tabela `ingestion_jobs`** para checkpoint persistente — evita re-transcrição
  quando o `persist` falha após transcrição bem-sucedida. Não vale o custo
  até o pipeline correr em volume.
- **Migrações automáticas** (Alembic ou Supabase migrations) quando o número
  de ficheiros em `docs/schema/` passar de 3.
- **Tracing Langfuse** no `IngestionOrchestrator` (Block 7) — emitir spans
  por stage para observar latência real por etapa em produção.
- **Compensação real (Saga)** — se o volume crescer ao ponto de a re-transcrição
  ser proibitiva, introduzir compensação explícita (rollback de upload). Hoje
  não vale; a idempotência cobre 90% dos casos de retry.
- **Protocol classes** para `AudioRepository` e `TranscriptRepository` —
  actualmente os Null Objects usam `*args, **kwargs` porque as assinaturas
  não estão formalizadas. `typing.Protocol` fecha esta lacuna e permite
  `isinstance` estático.

---

## 6. LESSONS LEARNED (narrativa de engenharia)

Registo das dores reais, para o documento evoluir com o projecto:

- **Amend em commit já pusheado** → aprendeu-se a regra `git status` antes de
  qualquer `--amend`. Commit `f61c40d` documenta o incidente.
- **`ruff format` faz parte da escrita do bloco**, não da verificação. Depois
  de emitir código, correr `ruff format src tests` **antes** de `ruff check`.
- **`ruff format` não reordena imports.** Erros `I001` persistem após
  `ruff format` e só são resolvidos com `ruff check --fix`. A cadeia canónica
  começa por `ruff check --fix` para eliminar este falso alarme.
- **Cobertura 100% é critério de bloco**, não de sorte. Cada ramo defensivo
  (`try/except`, validações, fallbacks) tem pelo menos um teste. O `_data()`
  do `transcript_repository.py` teve 3 ramos e inicialmente só 1 estava coberto.
- **Ficheiros de estado devem ser substituídos inteiros**, não editados por
  secção. Um bloco multi-secção editado parcialmente deixa o documento
  inconsistente sem aviso.
- **Números num documento de estado são lidos do output real**, não copiados
  de mensagens de commit. Uma mensagem de commit com "26 testes" não prova
  que o pytest correu 26.
- **Assinaturas de excepções de domínio não se adivinham.** O `IngestionError`
  recebe `(stage, audio_id, message)` posicionais e a sua `__str__` devolve
  `"[stage] audio_id: message"`. Um teste que assuma `message` crua falha
  mesmo com o código correcto. Ler o módulo antes de escrever o teste.
- **CLI para automação ≠ CLI para humanos.** stdout é JSON puro, pipeable
  para `jq`; stderr é para humanos e bibliotecas terceiras. Sem esta
  separação, a CLI não é composable em pipelines n8n/Airflow/cron.
