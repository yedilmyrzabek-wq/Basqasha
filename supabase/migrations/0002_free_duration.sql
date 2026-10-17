-- Owner decision 2026-10-18: video length is free (e.g. 8 min), not limited to 3-5 min.
-- Allowed: 1 to 60 minutes.
alter table project drop constraint if exists project_target_seconds_check;
alter table project add constraint project_target_seconds_check check (target_seconds between 60 and 3600);
