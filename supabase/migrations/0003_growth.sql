-- «Конкуренты» (growth manager), owner idea 2026-10-18.
-- competitor_item: a video or channel the owner liked (+ own thumbnails/screens and a comment), with the AI breakdown.
-- growth_report: playbook synthesis runs (proposed doc changes + what to film) and Q&A with the agent.
create table if not exists competitor_item (
  id          uuid primary key default gen_random_uuid(),
  kind        text not null default 'video' check (kind in ('video', 'channel', 'image')),
  url         text,
  title       text not null default '',
  channel     text,
  views       bigint,
  duration_s  int,
  published   date,
  notes       text not null default '',          -- owner: why it is good
  images      jsonb not null default '[]',        -- relative paths under data/growth/
  info        jsonb not null default '{}',        -- yt-dlp facts (top videos of a channel, tags, chapters…)
  status      text not null default 'pending' check (status in ('pending', 'running', 'done', 'failed')),
  error       text,
  analysis    jsonb,                              -- AI breakdown (see backend/ai/growth.py)
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create table if not exists growth_report (
  id          uuid primary key default gen_random_uuid(),
  kind        text not null check (kind in ('synthesis', 'question')),
  question    text,
  status      text not null default 'pending' check (status in ('pending', 'running', 'done', 'failed')),
  error       text,
  data        jsonb,                              -- synthesis: summary, film_next, doc_changes; question: answer
  applied_at  timestamptz,                        -- doc changes written to disk
  created_at  timestamptz not null default now()
);
create index if not exists growth_report_kind_idx on growth_report (kind, created_at desc);
