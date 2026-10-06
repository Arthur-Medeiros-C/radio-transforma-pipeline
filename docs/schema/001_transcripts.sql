-- Schema for transcript persistence. Apply manually in Supabase SQL editor.
-- ADR-003: single Postgres (Supabase) for relational + vector data.

create table if not exists public.transcripts (
    id          text primary key,
    audio_id    text not null,
    language    text not null,
    model       text not null,
    wer         double precision,
    created_at  timestamptz not null default now()
);

create index if not exists transcripts_audio_id_idx
    on public.transcripts (audio_id);

create table if not exists public.transcript_segments (
    id            text primary key,
    transcript_id text not null references public.transcripts(id) on delete cascade,
    position      integer not null,
    start_s       double precision not null,
    end_s         double precision not null,
    text          text not null,
    confidence    double precision,
    unique (transcript_id, position),
    check (end_s > start_s)
);

create index if not exists transcript_segments_transcript_id_idx
    on public.transcript_segments (transcript_id);
