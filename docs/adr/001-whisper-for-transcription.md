# ADR-001: Use faster-whisper for audio transcription

- **Status:** Accepted
- **Date:** 2026-10-04
- **Deciders:** Arthur Medeiros Conceição
- **Tags:** ingestion, transcription, llm

---

## Context

The pipeline must transcribe hundreds of hours of Portuguese (PT-PT) audio 
content from Rádio Transforma.pt — including reels, interviews, and 
political commentary. Transcription quality directly determines the quality 
of everything downstream: extraction, retrieval, and agent responses.

Key requirements:

- **Language:** European Portuguese (PT-PT), not Brazilian Portuguese (PT-BR)
- **Accuracy:** sufficient for semantic search and quote extraction
- **Cost:** must be sustainable for batch processing of large archives
- **Privacy:** audio may include unpublished content — local processing preferred
- **Timestamps:** segment-level timestamps required for citations
- **Throughput:** must handle batch jobs of hundreds of hours

---

## Decision

Use **faster-whisper** (a reimplementation of OpenAI's Whisper using CTranslate2) 
running on serverless GPU infrastructure (Modal), with the **large-v3** model.

Deployment: batch jobs, parallelized across Modal containers.

---

## Alternatives Considered

### Alternative 1: OpenAI Whisper API

**Description:** Use OpenAI's hosted Whisper API.

**Pros:**
- Zero infrastructure management
- Very high accuracy
- Simple integration

**Cons:**
- **Per-minute cost** — non-trivial for hundreds of hours
- **Audio sent to third party** — privacy concern for unpublished content
- **No control over model version**
- **Rate limits** on large batches

**Why rejected:** cost and privacy. The archive is large enough that per-minute 
pricing becomes significant, and content sensitivity makes third-party 
processing undesirable.

### Alternative 2: Local Whisper (openai-whisper)

**Description:** Run the original OpenAI Whisper implementation locally.

**Pros:**
- Free after setup
- Full privacy
- Same model weights as faster-whisper

**Cons:**
- **Significantly slower** — original implementation is not optimized
- **Higher memory usage**
- **Poor batch performance**

**Why rejected:** faster-whisper offers the same model quality at 4x+ the 
throughput on identical hardware.

### Alternative 3: Cloud speech APIs (Google, Azure, AWS)

**Description:** Use managed speech-to-text services.

**Pros:**
- Enterprise-grade reliability
- Managed scaling

**Cons:**
- **Per-minute cost** — similar issue to OpenAI
- **Third-party processing** — same privacy concern
- **PT-PT quality varies** — often optimized for PT-BR
- **Vendor lock-in**

**Why rejected:** cost, privacy, and language fit.

---

## Consequences

### Positive
- **Cost control** — only pay for GPU time actually used (serverless)
- **Privacy** — audio never leaves infrastructure we control
- **PT-PT quality** — Whisper large-v3 performs well on European Portuguese
- **Full control** — can swap models, adjust parameters, retrain if needed
- **Batch-friendly** — Modal parallelizes hundreds of hours across containers

### Negative
- **Infrastructure complexity** — must manage Modal deployment, GPU quotas
- **Cold start latency** — first job after idle has a startup cost
- **Maintenance** — responsible for dependency updates, model versions
- **GPU cost during processing** — cheaper than API but not free

### Neutral
- **Model size:** large-v3 is ~3GB — first download is slow, cached afterwards
- **Language detection:** must be explicitly set to `pt` to avoid PT-BR bias

### Follow-up actions
- [ ] Benchmark WER on a 10-hour sample of Rádio Transforma audio
- [ ] Document Modal deployment recipe in `docs/architecture.md`
- [ ] Add `faster-whisper` + `Modal` to the CI eval harness (transcription accuracy test)
- [ ] Define the golden dataset for transcription (manual transcripts as ground truth)

---

## References

- [faster-whisper on GitHub](https://github.com/SYSTRAN/faster-whisper)
- [Whisper large-v3 model card](https://huggingface.co/openai/whisper-large-v3)
- [Modal documentation](https://modal.com/docs)