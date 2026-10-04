# ADR-003: Use Supabase with pgvector for unified relational and vector storage

- **Status:** Accepted
- **Date:** 2026-10-04
- **Deciders:** Arthur Medeiros Conceição
- **Tags:** storage, database, vector, infrastructure

---

## Context

The pipeline produces two fundamentally different kinds of data:

1. **Relational data** — audio segments, transcripts, extraction records, 
   entities, topics, queries. Structured, queryable, with joins and constraints.
2. **Vector data** — embeddings for semantic retrieval (RAG), generated 
   from transcripts and extraction outputs.

These two kinds of data are tightly coupled: every vector is derived from a 
relational record, and every retrieval result must be joined back to its 
source. Storing them separately introduces:

- Synchronization complexity between two systems
- Consistency failures (a row is deleted in one system but not the other)
- Additional operational surface (two systems to back up, monitor, secure)
- Double cost and double failure modes

The project has no dedicated DevOps capacity and no budget for enterprise 
infrastructure. It requires a solution that a solo developer can operate, 
pay for reasonably, and reason about without specialised knowledge.

---

## Decision

Use **Supabase** (managed PostgreSQL) as the single storage layer for both 
relational data and vector embeddings, using the **pgvector** extension for 
semantic search.

All entities, transcripts, extractions, queries, and their embeddings live 
in the same database. Retrieval combines SQL filtering with vector 
similarity in a single query.

---

## Alternatives Considered

### Alternative 1: Separate vector database (Pinecone, Weaviate, Qdrant)

**Description:** Keep relational data in Postgres and store embeddings in 
a dedicated vector database.

**Pros:**
- Best-in-class vector performance at very large scale
- Specialised features (hybrid search, filtering, reranking)
- Horizontal scalability beyond Postgres

**Cons:**
- **Two systems to operate** — backups, monitoring, security, cost
- **Synchronization problems** — deleting a transcript must delete its 
  vectors; failure is silent
- **Latency overhead** — round-trip between systems on every query
- **Cost** — Pinecone and similar are not cheap at any serious volume
- **Overkill** — the project's expected scale is thousands of documents, 
  not billions of vectors

**Why rejected:** the operational and consistency costs outweigh the 
performance advantages at this scale. Supabase + pgvector handles the 
expected workload comfortably.

### Alternative 2: Local PostgreSQL with pgvector

**Description:** Self-hosted Postgres on the local machine or a VPS.

**Pros:**
- Zero recurring cost (beyond the VPS)
- Full control
- Can run entirely offline

**Cons:**
- **Backup responsibility** — losing the local disk means losing everything
- **Availability** — a laptop that shuts down is not a production database
- **Security** — exposing a VPS Postgres safely requires expertise
- **No managed tooling** — no automatic backups, no point-in-time recovery

**Why rejected:** the pipeline must survive the developer's machine going 
offline. Local storage is acceptable for development, not for production.

### Alternative 3: Supabase + pgvector (chosen)

**Description:** Managed PostgreSQL with pgvector extension, plus storage, 
auth, and API layers.

**Pros:**
- **One system for everything** — relational + vector + file storage + auth
- **SQL-native** — retrieval combines joins, filters, and vector similarity 
  in a single query
- **Managed** — automatic backups, monitoring, patches, point-in-time recovery
- **Free tier generous** — 500 MB database, 1 GB storage, sufficient for 
  Phase 0 and early Phase 1
- **Open source** — can self-host later if needed; no vendor lock-in on the 
  core technology (Postgres)
- **Row Level Security** — native access control if multi-tenant becomes a 
  requirement
- **Python client mature** — `supabase-py` is stable and well-documented

**Cons:**
- **Vendor platform dependency** — Supabase-specific tooling (though the 
  underlying Postgres is portable)
- **Costs scale** — beyond the free tier, pricing is per-project, not per-usage
- **Vector performance** — slower than dedicated vector DBs at very large 
  scale (mitigated by indexes: HNSW, IVFFlat)
- **Connection limits** — free tier has connection pool limits

**Why chosen:** it is the only option that unifies all storage needs, 
requires zero operational work, and keeps the technology stack portable 
(PostgreSQL is the industry standard and remains available outside Supabase).

---

## Consequences

### Positive
- **Single source of truth** — every piece of data lives in one system
- **Consistency by construction** — foreign keys, cascading deletes, and 
  transactions work as expected
- **SQL-native hybrid retrieval** — vector search and metadata filtering in 
  one query
- **Zero operational overhead** — managed backups, uptime, patching
- **Extensible** — same platform provides file storage, auth, and edge 
  functions if needed
- **Portable technology** — the schema and queries run on any Postgres with 
  pgvector

### Negative
- **Vendor dependency** — the Supabase Python client is used throughout the code
- **Free tier limits** — 500 MB DB and 1 GB storage cap the initial ingest size
- **pgvector scaling** — beyond ~1M vectors, dedicated vector databases 
  outperform pgvector
- **Connection management** — pooling is required for serverless workloads 
  (Modal functions)

### Neutral
- **Region:** chose EU (Frankfurt) for data locality and regulatory fit
- **Auth:** not used in V0.1, but available for future API authentication
- **RLS:** not enabled in V0.1 (single-user), but the schema is designed to 
  support it

### Follow-up actions
- [ ] Create Supabase project (EU region) and configure secrets
- [ ] Define initial schema migrations in `src/storage/migrations/`
- [ ] Document connection pooling strategy for Modal integrations
- [ ] Benchmark pgvector retrieval latency at expected scale
- [ ] Document backup and restore procedures in `docs/methodology.md`

---

## References

- [Supabase documentation](https://supabase.com/docs)
- [pgvector on GitHub](https://github.com/pgvector/pgvector)
- [Supabase + pgvector guide](https://supabase.com/docs/guides/ai/vector-columns)
- [PostgreSQL Row Level Security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- ADR-001 — faster-whisper for transcription (input to storage layer)