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
- **Verificação mecânica de números:** sempre que este ficheiro citar
  contagens de testes, SHAs, ou totais de commits, o número é lido do output
  real do `pytest`/`git log` — não copiado de mensagens de commit.
- **`ruff check --fix` antes de `ruff check`.** `ruff format` normaliza
  formatação; **não** reordena imports. Erros `I001` persistem após
  `ruff format` e só são resolvidos com `ruff check --fix`. Aplicar o `--fix`
  no início da cadeia de verificação evita falsos alarmes no CI.

**Comando de verificação canónico (correr antes de cada commit):**

```bash
ruff check --fix src tests; ruff format src tests; ruff check src tests; ruff format --check src tests; pytest tests/unit --cov=src/radio_transforma --cov-report=term-missing
