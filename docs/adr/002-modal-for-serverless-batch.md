# ADR-002: Use Modal for serverless batch processing

- **Status:** Accepted
- **Date:** 2026-10-04
- **Deciders:** Arthur Medeiros Conceição
- **Tags:** infrastructure, ingestion, transcription, serverless

---

## Context

The pipeline must process large batches of audio (hundreds of hours of 
Rádio Transforma archive) through faster-whisper (see ADR-001). 
Transcription workloads are spiky: bursts of activity separated by long 
idle periods. The system runs on a solo developer's local Windows machine 
with an RTX 2060 (6 GB VRAM) — enough for experimentation, not for 
production-scale batches.

Key requirements:

- **Cost control:** must be sustainable for batch workloads of hundreds of hours
- **Throughput:** must parallelize across multiple workers to process batches in minutes, not days
- **No permanent infrastructure:** no self-managed GPU servers idle 90% of the time
- **Reproducibility:** the same job must produce the same output regardless of where it runs
- **Developer experience:** a solo engineer must be able to deploy without DevOps overhead

---

## Decision

Use **Modal** as the serverless compute platform for batch transcription 
and any future heavy workloads (batch embedding generation, video frame 
processing, large-scale evaluation runs).

Modal functions are written as plain Python and deploy on-demand with GPU 
attached when needed. Cost is per-second of execution.

---

## Alternatives Considered

### Alternative 1: Persistent GPU worker (local or VPS)

**Description:** A long-running machine that polls for jobs and processes 
them sequentially.

**Pros:**
- Full control over hardware and environment
- No cold start latency
- Can be cheaper at 100% utilization

**Cons:**
- Idle time is paid for (the RTX 2060 is not suitable for production loads anyway)
- Managing a GPU VPS is expensive and complex for a solo developer
- The RTX 2060 has insufficient VRAM for Whisper large-v3 in production
- Requires OS updates, security patches, monitoring

**Why rejected:** the workload is spiky, not continuous. Paying for idle GPU 
contradicts the project's cost-consciousness constraint.

### Alternative 2: RunPod / Vast.ai (rented GPU instances)

**Description:** Rent GPU instances by the hour and shut them down when idle.

**Pros:**
- Cheaper per GPU-hour than managed serverless
- Wide selection of GPU types
- Full root access

**Cons:**
- Must manage image builds, dependencies, networking, storage
- Cold start is slower (container + model download)
- Manual start/stop workflow — easy to forget and burn money
- No native parallelization primitive

**Why rejected:** similar cost to Modal but with significantly higher 
operational overhead. The solo developer time is more valuable than the 
delta in GPU price.

### Alternative 3: Modal (chosen)

**Description:** Serverless Python platform with GPU support, pay-per-second.

**Pros:**
- Deploy Python functions directly, no Docker required
- Native parallelization primitive (`function.map()`)
- Automatic scaling from 0 to N containers
- Persistent volumes for model caching
- Generous free tier for experimentation
- Built-in scheduling, retries, observability

**Cons:**
- Vendor dependency (mitigated by portable Python code)
- Cold start on first invocation
- Pricing for sustained heavy loads is higher than dedicated hardware

**Why chosen:** the operational simplicity and pay-for-what-you-use model 
match the project's constraints. It is the only option that lets a solo 
developer deploy a batch GPU workload in minutes without infrastructure.

### Alternative 4: Google Cloud Run / AWS Fargate

**Description:** Managed container platforms with GPU support.

**Pros:**
- Enterprise-grade reliability
- Fine-grained IAM and networking
- Integration with cloud ecosystems

**Cons:**
- No native GPU support on Cloud Run (limited)
- Fargate does not support GPU
- Steep IAM and configuration overhead
- Cold starts measured in tens of seconds

**Why rejected:** GPU support is either missing or immature, and the 
configuration overhead contradicts the solo-developer constraint.

---

## Consequences

### Positive
- **Cost aligned with usage** — pay only while jobs run
- **Parallelization by default** — a batch of 200 audio files runs across 
  N containers concurrently
- **No infrastructure to maintain** — no OS, no GPU driver, no monitoring
- **Reproducible environment** — dependencies declared in Python, deployed as-is
- **Model caching** — Whisper weights cached in a persistent volume, 
  downloaded once

### Negative
- **Cold start latency** — first invocation after idle can take 10–30s
- **Vendor dependency** — Modal-specific code in `src/ingestion/` and 
  `src/transcription/` (mitigated by keeping the core logic framework-agnostic)
- **Cost predictability** — for very large batches, cost can exceed 
  equivalent rented GPU time
- **Debugging** — remote execution is harder to debug than local

### Neutral
- **Region:** Modal runs in the region closest to the caller; latency to 
  Supabase is acceptable
- **Secrets:** Modal manages its own secret store; separate from `.env` (documented)

### Follow-up actions
- [ ] Write `scripts/deploy_modal.py` to package the transcription function
- [ ] Add Modal token setup to `docs/methodology.md` onboarding section
- [ ] Benchmark cold start + throughput on a 10-file sample
- [ ] Document the Modal + Supabase Storage integration pattern

---

## References

- [Modal documentation](https://modal.com/docs)
- [Modal pricing](https://modal.com/pricing)
- [faster-whisper on Modal — official example](https://modal.com/docs/examples)
- ADR-001 — faster-whisper for transcription