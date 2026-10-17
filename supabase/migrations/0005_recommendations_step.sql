-- Step 11 «Рекомендации» (owner idea 2026-10-18): what was missing for this video (poses, costumes,
-- sounds, music…) and how to add it. Run each statement in its own transaction (new enum value).
alter type step_key add value if not exists 'recommendations';
insert into project_step (project_id, step) select id, 'recommendations' from project on conflict do nothing;
