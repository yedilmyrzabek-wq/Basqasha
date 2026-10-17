-- Indexes on foreign keys that had none (cascade deletes and joins stay fast as projects pile up)
-- and on the growth tables' list order. Cheap at our size; harmless to re-run.
create index if not exists image_asset_project_idx   on image_asset (project_id, slot);
create index if not exists voice_track_script_idx    on voice_track (script_id);
create index if not exists storyboard_voice_idx      on storyboard (voice_track_id);
create index if not exists scene_comment_sb_idx      on scene_comment (storyboard_id);
create index if not exists render_storyboard_idx     on render (storyboard_id);
create index if not exists competitor_item_created_idx on competitor_item (created_at desc);
