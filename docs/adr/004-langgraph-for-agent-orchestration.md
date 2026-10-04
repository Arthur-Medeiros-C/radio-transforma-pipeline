# ADR-004: Use LangGraph for stateful agent orchestration

- **Status:** Accepted
- **Date:** 2026-10-04
- **Deciders:** Arthur Medeiros Conceição
- **Tags:** agents, orchestration, llm, framework

---

## Context

The pipeline's Phase 2 requires agents that can:

- Answer queries against the knowledge base with citations
- Compose multi-step workflows (retrieve → rerank → extract → synthesise)
- Maintain state across steps (accumulated context, retries, branching)
- Support tool calling (query the database, fetch a transcript, retrieve a quote)

This is not a chatbot. It is a **stateful workflow** with deterministic and 
non-deterministic steps interleaved. Some steps are LLM calls; others are 
SQL queries, embedding lookups, or API calls. The orchestration layer must 
model this explicitly.

Additional requirements:

- **Observability:** every step must be traceable (see ADR-005)
- **Testability:** workflows must be runnable in isolation with mocked LLM outputs
- **Retry semantics:** individual steps may fail and need retry logic
- **Portability:** should not be tied to a single LLM provider
- **Predictability:** the same input should produce a reproducible execution 
  path (even if individual LLM outputs differ)

---

## Decision

Use **LangGraph** as the orchestration framework for stateful, multi-step 
agent workflows.

LangGraph models workflows as directed graphs of nodes and edges, with 
explicit state passed between nodes. Agents, chains, and tool-calling logic 
live inside nodes; the graph defines how they connect.

---

## Alternatives Considered

### Alternative 1: Plain Python functions calling the LLM SDK directly

**Description:** Write orchestration as a sequence of Python functions 
calling OpenAI/OpenRouter directly.

**Pros:**
- Zero framework overhead
- Full control over every step
- No learning curve

**Cons:**
- **No state management** — every step must thread context manually
- **No retry semantics** — error handling becomes ad-hoc
- **No checkpoints** — a failing step mid-workflow requires starting over
- **No observability hooks** — Langfuse integration must be built by hand
- **No cyclic graphs** — iterative agents (retry, reflection) are awkward

**Why rejected:** the workflow has enough complexity (multi-step, tool-calling, 
conditional branches, retries) that manual orchestration becomes fragile 
quickly. The framework earns its keep.

### Alternative 2: LangChain sequential chains

**Description:** Use LangChain's `LLMChain` and `SequentialChain` primitives.

**Pros:**
- Mature ecosystem
- Many pre-built integrations
- Familiar to most Python developers working with LLMs

**Cons:**
- **No true state** — chains pass outputs linearly; complex branching is unnatural
- **No cycles** — cannot implement "retry if insufficient" without workarounds
- **Abstraction leakage** — debugging often requires understanding deep internal machinery
- **Deprecated direction** — LangChain itself has shifted toward LangGraph for 
  complex workflows

**Why rejected:** chains are the wrong abstraction for stateful workflows. 
LangGraph was created precisely to address this limitation.

### Alternative 3: LlamaIndex agents

**Description:** Use LlamaIndex's agent framework with query engines.

**Pros:**
- Strong document-retrieval focus (which fits RAG)
- Good defaults for common patterns
- Actively maintained

**Cons:**
- **Retrieval-first design** — assumes the workflow is query → retrieve → answer; 
  less natural for custom multi-step workflows
- **Less control over state topology**
- **Smaller ecosystem** for tool-calling and agentic patterns compared to LangGraph
- **Tighter coupling** — LlamaIndex abstractions are harder to peel away

**Why rejected:** LangGraph provides a more explicit, lower-level abstraction 
that fits a workflow where retrieval is one of several steps, not the whole 
pattern.

### Alternative 4: LangGraph (chosen)

**Description:** Graph-based orchestration for stateful, tool-using LLM workflows.

**Pros:**
- **Explicit state model** — the graph state is a typed dict, visible and testable
- **Cycles and conditions** — supports iterative and branching workflows natively
- **Checkpointing** — workflows can pause, resume, and be inspected
- **Langfuse integration** — first-class, automatic tracing of every node
- **Provider-agnostic** — nodes call whatever LLM or tool they want; no lock-in
- **Streaming support** — outputs stream to clients during execution
- **Human-in-the-loop** — native support for approval gates if needed
- **Active development** — the framework is evolving rapidly and aligned 
  with where the agent ecosystem is heading

**Cons:**
- **Learning curve** — the graph model takes time to internalise
- **Verbose for simple cases** — a 2-step workflow is overkill
- **Ecosystem churn** — LangGraph's API surface has evolved significantly
- **Documentation gaps** — some advanced patterns are under-documented

**Why chosen:** it models the workflow as what it is — a state machine with 
typed state, conditional branches, and tool calls. The verbosity is a 
feature, not a bug, for a project where the orchestration is the artefact.

---

## Consequences

### Positive
- **Explicit state** — every workflow has a typed state schema, visible and testable
- **Composable** — sub-graphs allow independent development of retrieval, 
  extraction, and synthesis components
- **Observable** — Langfuse traces show exactly which node ran, in what order, 
  with what inputs and outputs
- **Debuggable** — workflows can be replayed from a checkpoint
- **Streamable** — responses can stream to clients as they are generated
- **Testable** — nodes can be tested in isolation with mocked LLM calls

### Negative
- **Framework dependency** — the workflow is expressed in LangGraph's DSL
- **API churn risk** — LangGraph is evolving; minor version bumps may require changes
- **Complexity for simple tasks** — trivial workflows become verbose
- **Debugging** — errors inside nodes may be obscured by framework layers

### Neutral
- **Version pinning:** LangGraph is pinned to a range (`>=0.2.30`) and reviewed 
  at every minor bump
- **Not used for:** data ingestion (Phase 1), which is plain Python + Modal
- **Complementary to:** PydanticAI (used inside LangGraph nodes for structured 
  LLM outputs)

### Follow-up actions
- [ ] Define the first agent graph in `src/agents/query_agent.py`
- [ ] Wire Langfuse callbacks into the graph execution
- [ ] Write integration tests with mocked LLM providers
- [ ] Document the node/graph conventions in `docs/methodology.md`
- [ ] Benchmark end-to-end latency of the retrieval agent

---

## References

- [LangGraph documentation](https://langchain-ai.github.io/langgraph/)
- [LangGraph concepts: state, nodes, edges](https://langchain-ai.github.io/langgraph/concepts/)
- [PydanticAI](https://ai.pydantic.dev/) — used for structured outputs inside nodes
- ADR-005 — Promptfoo and Langfuse for EDD (observability integration)