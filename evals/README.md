# Golden Dataset — Contract & Data Governance

> **Living document.** This file is the contract for every entry in
> `evals/golden_dataset.json`. If the JSON diverges from this document,
> the JSON is wrong. Fix it in a dedicated commit before adding cases.

## Scope

Defines (a) the annotation philosophy for the ground truth, (b) the JSON
Schema for the four eval types — transcription, extraction, retrieval,
agent — and (c) the inclusion/exclusion criteria for audio clips.

**Non-goals:** pipeline design (`docs/adr/`), eval runner configuration
(`evals/config/promptfoo.yaml`), metric thresholds (published in the root
`README.md` once the first real run exists).

**Audience:** anyone adding a case. If you cannot answer a question with
this document, the document is incomplete — extend it in the same commit
that adds the case.

---

## 1. Annotation Philosophy

The transcription ground truth feeds the WER computation for
`TranscriptionService` (faster-whisper `large-v3`, PT-PT). It is the
reference every model change is measured against. Ambiguity in the
reference is a bug that propagates into every metric downstream.

### 1.1 General principles

1. **Verbatim.** Transcribe what was said, not what should have been
   said. Do not correct grammar, do not normalise register.
2. **Minimal editorialising.** Punctuation is a concession to
   readability, not a rewrite. When in doubt, use fewer marks, not more.
3. **PT-PT only.** Reject any clip whose speaker uses PT-BR syntax,
   vocabulary, or prosody as the primary register. Code-switching into
   English inside a PT-PT clip is fine (see §1.5); mixed PT-PT/PT-BR is not.
4. **Single-pass annotation.** Annotation is done in one pass; a random
   20 % subsample is re-reviewed after ≥24 h with fresh eyes. The
   `reviewer` field uses the same handle as `annotator`; the ≥24 h gap
   is the control. If two separate people annotate the same clip and
   disagree on any segment, the clip is excluded from the golden set and
   moved to `evals/scratch/` for calibration.

### 1.2 Disfluencies

Transcribe verbatim, using a **closed canonical set**:

| Spoken sound        | Canonical spelling |
|---|---|
| Short hesitation    | `eh`               |
| Long hesitation     | `hum`              |
| Realisation / pause | `ah`               |
| Open hesitation     | `ãh`               |

- Do **not** extend the spelling for duration (`hummm`, `ehhh` are
  wrong). Duration is a prosodic feature, not an orthographic one.
- False starts are preserved: `eu acho… eu penso que sim`.
- Repetitions are preserved: `muito, muito bom`.
- Filler words with lexical content (`tipo`, `pronto`, `ora bem`,
  `sabes`) are transcribed as normal words — they are not disfluencies
  in the canonical sense, they are register markers.

### 1.3 Background noise & non-speech events

Use bracketed uppercase tags, and only when the event **overlaps or
interrupts speech**:

| Tag | Meaning |
|---|---|
| `[MÚSICA]` | Music under or over speech |
| `[RUÍDO]` | Sustained non-speech noise |
| `[INAUDÍVEL]` | Unintelligible span ≥ 0.5 s |
| `[SOBREPOSIÇÃO]` | Overlapping speakers |
| `[RISO]` | Laughter |
| `[TOSSE]` | Cough |

- Below 0.5 s unintelligible, drop the token entirely — do not guess.
- Do not tag clean background ambience (room tone, distant traffic).
- Never invent a word to smooth over an unintelligible span.

### 1.4 Numbers, dates, currency

Always **spelled out** in PT-PT orthography (Acordo Ortográfico de 1990):

- Cardinals: `vinte e três`, `cento e quarenta`, `dois mil e vinte e cinco`.
- Ordinals: `primeiro`, `segundo`, `décimo terceiro`.
- Years: `dois mil e vinte e cinco` (not `2025`).
- Decimals: `três vírgula catorze` (not `3,14`).
- Currency: `cinquenta euros`, `quinze cêntimos` (never `50€`).
- Phone numbers / codes read digit-by-digit: transcribe digit-by-digit
  with hyphens: `dois-zero-dois-cinco`.

Exception: if the speaker explicitly reads a string (e.g. an email or a
postal code spelled letter-by-letter), transcribe exactly as read,
preserving the spelling strategy the speaker used.

### 1.5 Acronyms & initialisms

Transcribe the **surface form the speaker produced**, not the expanded
meaning:

| Speaker said | Canonical form |
|---|---|
| "érre-tê-pê" | `RTP` |
| "R-T-P" (letters) | `R-T-P` |
| "Nasa" (as a word) | `NASA` |
| "Organização Mundial de Saúde" | `Organização Mundial de Saúde` |

- Never expand an acronym the speaker pronounced as letters.
- Never letter-space an acronym the speaker pronounced as a word.

### 1.6 Proper nouns & technical jargon

- Guest names, place names, brand names: spell per the **official
  source**, verified against a public reference (Wikipedia, the
  organisation's own site). Do not guess diacritics.
- If a name is genuinely ambiguous (two plausible spellings), flag it in
  the case's `notes` field and exclude from the golden set — a coin flip
  in the ground truth is worse than a smaller dataset.
- Technical jargon in English inside PT-PT speech is transcribed in
  English: `machine learning`, `deploy`, `pipeline`. Do not translate.

### 1.7 Punctuation & casing

Light and consistent:

- `,` for short pauses with continuing prosody.
- `.` for sentence-final falling intonation.
- `?` only when interrogative prosody is unambiguous.
- No `!`, no `…`, no quotation marks unless the speaker is explicitly
  reading a quotation aloud.
- No en/em-dashes.
- Sentence-initial capitalisation.
- Proper nouns capitalised.
- Everything else lowercase.

### 1.8 Segment boundaries

- Do not re-segment audio to match ground truth. Instead, ground truth
  follows the ASR's segment boundaries when they are reasonable, and
  merges when the model is clearly under-segmenting.
- Any merge/split decision is recorded in the case's `notes`.
- `start` and `end` are always present, monotonic, and non-overlapping
  within a case's `segments` array.

---

## 2. JSON Schema

`evals/golden_dataset.json` is a single object with a `cases` array.
Every case shares a header and adds type-specific fields. The schema
below is a **contract**, not a runnable validator; a `jsonschema`-based
validator lives in `evals/validate.py` once real cases exist.

### 2.1 Envelope

```json
{
  "version": "1.0",
  "cases": [
    { "id": "t-001", "type": "transcription", "...": "..." }
  ]
}
```

### 2.2 `transcription`

Ground truth for WER.

```json
{
  "id": "t-001",
  "type": "transcription",
  "audio_id": "rt-2025-03-14-joao-silva",
  "language": "pt-PT",
  "duration_s": 184.5,
  "segments": [
    { "start": 0.0, "end": 3.2, "text": "Bom dia, estamos aqui hoje com o João Silva." }
  ],
  "annotator": "am",
  "notes": "Speaker uses Porto register; two [INAUDÍVEL] spans at 41s and 88s."
}
```

- `segments[].text` follows §1.1–1.7 **verbatim**.
- `duration_s` is the audio duration, not the last segment end.

### 2.3 `extraction`

Ground truth for the semantic extractor. The `expected` block is a
**subset** of `ExtractedData` (`src/radio_transforma/models/extraction.py`)
— it contains only the fields the eval checks (topics, entities, quotes),
not the envelope fields (`transcript_id`, `model`, `sentiment`,
`created_at`). Field names, types, and enum values must match the Pydantic
contract exactly; if this document and the model diverge, **the model wins**.

```json
{
  "id": "x-001",
  "type": "extraction",
  "transcript_id": "t-001",
  "expected": {
    "topics": [
      { "name": "fado", "confidence": 0.9 }
    ],
    "entities": [
      { "name": "João Silva", "type": "person", "mentions": 3 }
    ],
    "quotes": [
      { "text": "…", "position": "middle", "start": 12.0, "end": 34.5 }
    ]
  },
  "annotator": "am"
}
```

- `expected.topics[].name` — at least one, at most five, ordered by salience.
- `expected.topics[].confidence` — float in [0, 1]; defaults to 1.0.
- `expected.entities[].type` — closed vocabulary `EntityType`:
  `person`, `location`, `organization`, `policy`, `geopolitical_entity`,
  `event`, `other`. Values are **lowercase**. Adding a new type is a
  schema change, not a case change.
- `expected.entities[].mentions` — **count** of mentions in the transcript,
  not a list of positions. Integer ≥ 1; defaults to 1.
- `expected.quotes[].text` — verbatim, per §1.1–1.7.
- `expected.quotes[].position` — one of `"start"`, `"middle"`, `"end"`;
  defaults to `"middle"`.
- `expected.quotes[].start` / `end` — **seconds** (float), not segment
  indices. Both optional. `start ≥ 0`, `end > 0`.

**Known gap (Phase 2):** `Quote` has no `speaker` field, so the eval
cannot currently distinguish who said a quote. This is a deliberate V0.1
omission per the model docstring; revisit when the agent eval requires
attribution.