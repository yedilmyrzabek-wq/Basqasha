-- 0001_init.sql — Basqasha initial schema (plain PostgreSQL 15+; Supabase or local).
-- Single-user local app: no Supabase auth. RLS is enabled with NO policies so the Supabase
-- Data API (anon/authenticated roles) cannot read anything; the app connects as the table
-- owner via DATABASE_URL (Session pooler :5432) and therefore bypasses RLS.
-- Media never lives here: *_path columns are POSIX paths relative to DATA_DIR
-- (project assets) or LIBRARY_DIR (poses).
-- Flexible documents are jsonb validated by the app against /schemas/*.schema.json.

begin;

create table schema_migrations (
  version    text primary key,
  applied_at timestamptz not null default now()
);

create type language_code as enum ('kk', 'ru', 'en');
create type step_key as enum (
  'source', 'idea', 'facts', 'script', 'voice',
  'storyboard', 'images', 'preview', 'render', 'metadata');
create type step_status as enum ('pending', 'running', 'waiting_operator', 'done', 'failed', 'stale');
create type project_status as enum ('active', 'waiting_operator', 'failed', 'ready', 'published', 'archived');
create type hook_type as enum ('question', 'number', 'paradox', 'scene', 'myth');
create type fact_status as enum ('verified', 'unverified', 'conflicting', 'rejected');
create type image_qa_status as enum ('pending', 'passed', 'failed', 'needs_manual', 'manual_approved');
create type render_kind as enum ('preview', 'full', 'short');

create function set_updated_at() returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end $$;

-- ---------------------------------------------------------------- project
create table project (
  id             uuid primary key default gen_random_uuid(),
  title          text not null default '',
  status         project_status not null default 'active',
  language       language_code not null default 'kk',
  script         text not null default 'Cyrl' check (script in ('Cyrl', 'Latn')),
  target_seconds int not null default 240 check (target_seconds between 180 and 300),
  wpm_voice      numeric(5,1) not null default 110 check (wpm_voice between 60 and 200),
  target_words   int generated always as (round(wpm_voice * target_seconds / 60)::int) stored,
  source_url     text,
  hook_type      hook_type,                      -- set when the script is approved
  structure_id   text check (structure_id ~ '^[a-z0-9_]{3,40}$'),
  sponsored      boolean not null default false,
  sponsor_name   text,
  budget_usd     numeric(8,2) not null default 5.00,
  cost_usd       numeric(10,4) not null default 0,  -- maintained by trigger on cost_entry
  published_url  text,
  published_at   timestamptz,
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now()
);
create trigger project_updated before update on project for each row execute function set_updated_at();
create index project_created_idx on project (created_at desc);

create table project_step (
  project_id  uuid not null references project(id) on delete cascade,
  step        step_key not null,
  status      step_status not null default 'pending',
  wait_reason text,          -- choose_angle | approve_script | upload_voice | review_alignment |
                             -- manual_images | approve_preview | budget_exceeded | confirm_similar_topic
  attempts    int not null default 0,
  progress    real,          -- 0..1 for long steps (images, render)
  error       text,
  started_at  timestamptz,
  finished_at timestamptz,
  updated_at  timestamptz not null default now(),
  primary key (project_id, step)
);
create trigger project_step_updated before update on project_step for each row execute function set_updated_at();

-- ---------------------------------------------------------------- step 1 (ORIGINALITY GUARD)
-- Readable ONLY through SourceRepository, used by steps 1-2 and the originality feed.
create table source_material (
  project_id     uuid primary key references project(id) on delete cascade,
  source_url     text,
  yt_video_id    text,
  yt_title       text,
  yt_channel     text,
  yt_duration    int,          -- seconds
  yt_views       bigint,
  views_checked_at timestamptz,
  origin         text not null default 'yt_dlp' check (origin in ('yt_dlp', 'manual')),
  transcript     text not null, -- cleaned, no timestamps
  created_at     timestamptz not null default now()
);

-- ---------------------------------------------------------------- step 2
create table brief (
  project_id uuid primary key references project(id) on delete cascade,
  data       jsonb not null,   -- schemas/brief.schema.json (brief part)
  created_at timestamptz not null default now()
);

create table angle (
  id         uuid primary key default gen_random_uuid(),
  project_id uuid not null references project(id) on delete cascade,
  idx        int not null,               -- 1..3 generated, 0 = operator's own
  data       jsonb not null,             -- schemas/brief.schema.json $defs/angle
  is_custom  boolean not null default false,
  chosen     boolean not null default false,
  created_at timestamptz not null default now()
);
create index angle_project_idx on angle (project_id);
create unique index angle_one_chosen on angle (project_id) where chosen;

-- ---------------------------------------------------------------- step 3
create table fact (
  id          uuid primary key default gen_random_uuid(),
  project_id  uuid not null references project(id) on delete cascade,
  idx         int not null default 0,
  claim       text not null,
  value       text,
  source_url  text,                       -- primary citation (= sources[0].url)
  sources     jsonb not null default '[]', -- [{url,title,is_primary}]
  status      fact_status not null default 'unverified',
  on_screen   boolean not null default false, -- allowed as on-screen number (verified, >=2 sources)
  edited_by_operator boolean not null default false,
  updated_at  timestamptz not null default now()
);
create trigger fact_updated before update on fact for each row execute function set_updated_at();
create index fact_project_idx on fact (project_id, idx);

-- ---------------------------------------------------------------- step 4
create table script (
  id          uuid primary key default gen_random_uuid(),
  project_id  uuid not null references project(id) on delete cascade,
  version     int not null,
  llm_draft   text not null,            -- untouched LLM output (human-contribution trail)
  text        text not null,            -- operator-edited text; frozen once approved
  data        jsonb not null default '{}', -- schemas/script.schema.json (beats, hook_type, writer...)
  word_count  int not null default 0,
  edit_ratio  real,                     -- share of words changed vs llm_draft, set on approve
  tts_text    text,                     -- step 5 "Copy for ElevenLabs" text (numbers as words)
  approved    boolean not null default false,
  approved_at timestamptz,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (project_id, version)
);
create trigger script_updated before update on script for each row execute function set_updated_at();
create unique index script_one_approved on script (project_id) where approved;

create table originality_report (
  id             uuid primary key default gen_random_uuid(),
  script_id      uuid not null references script(id) on delete cascade,
  max_similarity real not null,
  verdict        text not null check (verdict in ('pass', 'pass_after_rewrite', 'fail')),
  flagged_sentences jsonb not null default '[]', -- [{index,text,similarity,source_index}] (no source text)
  data           jsonb not null default '{}',   -- judge reasons, rewrites, threshold, models
  created_at     timestamptz not null default now()
);
create index originality_script_idx on originality_report (script_id, created_at desc);

-- ---------------------------------------------------------------- step 5
create table voice_track (
  id            uuid primary key default gen_random_uuid(),
  project_id    uuid not null references project(id) on delete cascade,
  script_id     uuid not null references script(id) on delete cascade,
  upload_path   text not null,          -- original mp3 as uploaded
  path          text,                   -- normalized (-16 LUFS) wav
  duration      real,                   -- seconds
  words_json    jsonb,                  -- schemas/words.schema.json
  provider      text not null default 'manual_upload' check (provider in ('manual_upload', 'elevenlabs_api')),
  provider_plan text not null default 'unknown' check (provider_plan in ('free', 'starter', 'creator', 'pro', 'unknown')),
  model_id      text not null default 'eleven_v4',
  wpm_measured  real,
  alignment_ok  boolean,
  is_current    boolean not null default true,
  created_at    timestamptz not null default now()
);
create unique index voice_one_current on voice_track (project_id) where is_current;

-- ---------------------------------------------------------------- step 6
create table storyboard (
  id          uuid primary key default gen_random_uuid(),
  project_id  uuid not null references project(id) on delete cascade,
  version     int not null,
  voice_track_id uuid references voice_track(id) on delete set null,
  data        jsonb not null,           -- schemas/storyboard.schema.json
  errors      jsonb not null default '[]', -- validator rule violations (empty = valid)
  created_at  timestamptz not null default now(),
  unique (project_id, version)
);

-- ---------------------------------------------------------------- step 7
create table image_asset (
  id          uuid primary key default gen_random_uuid(),
  project_id  uuid not null references project(id) on delete cascade,
  slot        text not null,            -- background id from storyboard, e.g. 'bg01'
  prompt      text not null,
  path        text,
  source      text not null default 'generated' check (source in ('generated', 'manual_upload', 'library', 'purchased')),
  license     text not null default 'own:gemini-api-output',
  is_photoreal        boolean not null default false,
  depicts_real_person boolean not null default false,
  attempts    int not null default 0 check (attempts between 0 and 3),
  qa_status   image_qa_status not null default 'pending',
  qa_report   jsonb,
  selected    boolean not null default true,
  created_at  timestamptz not null default now()
);
create unique index image_one_selected on image_asset (project_id, slot) where selected;

-- ---------------------------------------------------------------- library
create table pose (
  id         uuid primary key default gen_random_uuid(),
  name       text not null unique check (name ~ '^[a-z0-9_]{2,32}$'),
  path       text not null,             -- relative to LIBRARY_DIR, e.g. poses/pose_think.png
  width      int not null,
  height     int not null,
  tags       text[] not null default '{}',
  active     boolean not null default true,  -- false = candidate from a sheet, not yet named/approved
  created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------- steps 8-9
create table scene_comment (
  id         uuid primary key default gen_random_uuid(),
  project_id uuid not null references project(id) on delete cascade,
  storyboard_id uuid not null references storyboard(id) on delete cascade,
  scene_id   int not null,
  text       text not null,
  resolved   boolean not null default false,
  created_at timestamptz not null default now()
);
create index scene_comment_idx on scene_comment (project_id, storyboard_id);

create table render (
  id          uuid primary key default gen_random_uuid(),
  project_id  uuid not null references project(id) on delete cascade,
  kind        render_kind not null,     -- preview = contact sheet
  storyboard_id uuid references storyboard(id) on delete set null,
  path        text,
  props_path  text,
  duration    real,
  checks      jsonb not null default '{}', -- duration delta, LUFS, true peak, glyph check
  created_at  timestamptz not null default now()
);
create index render_project_idx on render (project_id, created_at desc);

-- ---------------------------------------------------------------- step 10
create table metadata (
  project_id     uuid primary key references project(id) on delete cascade,
  data           jsonb not null,        -- schemas/metadata.schema.json
  made_for_kids  boolean not null default false check (made_for_kids = false),
  ai_disclosure  boolean not null default false, -- computed by step 10 from asset/voice flags
  paid_promotion boolean not null default false, -- = project.sponsored
  updated_at     timestamptz not null default now()
);
create trigger metadata_updated before update on metadata for each row execute function set_updated_at();

-- ---------------------------------------------------------------- ops
create table settings (
  id         smallint primary key default 1 check (id = 1),
  data       jsonb not null default '{}',  -- operator-editable, non-secret (secrets live in .env)
  updated_at timestamptz not null default now()
);
create trigger settings_updated before update on settings for each row execute function set_updated_at();

create table job_log (
  id         bigint generated always as identity primary key,
  project_id uuid references project(id) on delete cascade,
  step       step_key,
  level      text not null default 'info' check (level in ('debug', 'info', 'warning', 'error')),
  message    text not null,
  data       jsonb,
  created_at timestamptz not null default now()
);
create index job_log_idx on job_log (project_id, step, id);

create table pricing (
  id             bigint generated always as identity primary key,
  provider       text not null,
  model          text not null,
  unit           text not null,
  usd_per_unit   numeric(12,6) not null,
  effective_from date not null,
  source_url     text,
  unique (provider, model, unit, effective_from)
);

create table cost_entry (
  id         bigint generated always as identity primary key,
  project_id uuid references project(id) on delete set null,
  step       step_key,
  provider   text not null,
  model      text not null,
  tier       text not null default 'standard',
  units      jsonb not null default '{}',   -- {"input_tokens":..,"output_tokens":..,"images":..}
  usd        numeric(10,6) not null,
  created_at timestamptz not null default now()
);
create index cost_entry_project_idx on cost_entry (project_id);
create index cost_entry_month_idx on cost_entry (created_at);

create function cost_entry_rollup() returns trigger language plpgsql as $$
begin
  if new.project_id is not null then
    update project set cost_usd = cost_usd + new.usd where id = new.project_id;
  end if;
  return new;
end $$;
create trigger cost_entry_after_insert after insert on cost_entry for each row execute function cost_entry_rollup();

-- RLS on, no policies (see header).
do $$ declare t text; begin
  foreach t in array array['project','project_step','source_material','brief','angle','fact','script',
    'originality_report','voice_track','storyboard','image_asset','pose','scene_comment','render',
    'metadata','settings','job_log','pricing','cost_entry','schema_migrations'] loop
    execute format('alter table %I enable row level security', t);
  end loop;
end $$;

-- ---------------------------------------------------------------- seed: pricing (docs/research/tools_costs.md, checked 2026-10-16)
-- Rows without a date in the research use effective_from = 2026-10-16. The ledger picks the
-- latest row with effective_from <= call date. Batch/Flex tier = 50% of these rows.
insert into pricing (provider, model, unit, usd_per_unit, effective_from, source_url) values
  ('google', 'gemini-4-argon',         '1M_input_tokens',  2.00,  '2026-10-16', 'https://ai.google.dev/gemini-api/docs/pricing'),
  ('google', 'gemini-4-argon',         '1M_output_tokens', 10.00, '2026-10-16', 'https://ai.google.dev/gemini-api/docs/pricing'),
  ('google', 'gemini-4-argon',         '1M_input_tokens',  4.00,  '2026-12-01', 'https://ai.google.dev/gemini-api/docs/pricing'),
  ('google', 'gemini-4-argon',         '1M_output_tokens', 20.00, '2026-12-01', 'https://ai.google.dev/gemini-api/docs/pricing'),
  ('google', 'gemini-3.8-flash',       '1M_input_tokens',  0.75,  '2026-10-16', 'https://ai.google.dev/gemini-api/docs/pricing'),
  ('google', 'gemini-3.8-flash',       '1M_output_tokens', 3.75,  '2026-10-16', 'https://ai.google.dev/gemini-api/docs/pricing'),
  ('google', 'gemini-3.8-flash',       '1M_input_tokens',  1.50,  '2027-01-01', 'https://ai.google.dev/gemini-api/docs/pricing'),
  ('google', 'gemini-3.8-flash',       '1M_output_tokens', 7.50,  '2027-01-01', 'https://ai.google.dev/gemini-api/docs/pricing'),
  ('google', 'gemini-3.5-flash-lite',  '1M_input_tokens',  0.30,  '2026-10-16', 'https://ai.google.dev/gemini-api/docs/pricing'),
  ('google', 'gemini-3.5-flash-lite',  '1M_output_tokens', 2.50,  '2026-10-16', 'https://ai.google.dev/gemini-api/docs/pricing'),
  ('google', 'gemini-3.1-flash-lite',  '1M_input_tokens',  0.25,  '2026-10-16', 'https://ai.google.dev/gemini-api/docs/pricing'),
  ('google', 'gemini-3.1-flash-lite',  '1M_output_tokens', 1.50,  '2026-10-16', 'https://ai.google.dev/gemini-api/docs/pricing'),
  ('google', 'gemini-embedding-2',     '1M_input_tokens',  0.20,  '2026-10-16', 'https://ai.google.dev/gemini-api/docs/pricing'),
  ('google', 'gemini-nano-banana-2.1', '1M_input_tokens',  1.50,  '2026-10-16', 'https://ai.google.dev/gemini-api/docs/pricing'),
  ('google', 'gemini-nano-banana-2.1', 'image_1K',         0.0336,'2026-10-16', 'https://ai.google.dev/gemini-api/docs/pricing'),
  ('google', 'gemini-nano-banana-2.1', 'image_2K',         0.0504,'2026-10-16', 'https://ai.google.dev/gemini-api/docs/pricing'),
  ('google', 'gemini-nano-banana-2.1', 'image_4K',         0.113, '2026-10-16', 'https://ai.google.dev/gemini-api/docs/pricing'),
  ('google', 'gemini-3.1-flash-image', 'image_1K',         0.067, '2026-10-16', 'https://ai.google.dev/gemini-api/docs/pricing'),
  ('google', 'gemini-3.1-flash-image', 'image_2K',         0.101, '2026-10-16', 'https://ai.google.dev/gemini-api/docs/pricing'),
  ('google', 'gemini-3-pro-image',     '1M_input_tokens',  2.00,  '2026-10-16', 'https://ai.google.dev/gemini-api/docs/pricing'),
  ('google', 'gemini-3-pro-image',     'image_1K_2K',      0.134, '2026-10-16', 'https://ai.google.dev/gemini-api/docs/pricing'),
  ('google', 'gemini-3.8-flash-tts',   '1M_output_tokens', 9.00,  '2026-10-16', 'https://ai.google.dev/gemini-api/docs/pricing'),
  ('google', 'gemini-3.8-flash-tts',   '1M_output_tokens', 18.00, '2027-01-01', 'https://ai.google.dev/gemini-api/docs/pricing'),
  ('google', 'google_search_grounding','search_query',     0.014, '2026-10-16', 'https://ai.google.dev/gemini-api/docs/google-search'),
  ('elevenlabs', 'eleven_v3',          '1K_characters',    0.08,  '2026-10-16', 'https://elevenlabs.io/pricing/api'),
  ('elevenlabs', 'eleven_v4',          '1K_characters',    0.08,  '2026-10-16', 'https://elevenlabs.io/pricing/api'),
  ('elevenlabs', 'creator_plan',       'month',            22.00, '2026-10-16', 'https://elevenlabs.io/pricing'),
  ('elevenlabs', 'starter_plan',       'month',            6.00,  '2026-10-16', 'https://elevenlabs.io/pricing'),
  ('supabase',   'free_plan',          'month',            0.00,  '2026-10-16', 'https://supabase.com/pricing'),
  ('anthropic',  'claude-code-cli',    'call',             0.00,  '2026-10-16', 'https://support.claude.com/articles/15036540');
-- note: google_search_grounding is free for the first 5,000 queries/month; the ledger applies the free quota.

insert into settings (id, data) values (1, '{}');
insert into schema_migrations (version) values ('0001');

commit;
