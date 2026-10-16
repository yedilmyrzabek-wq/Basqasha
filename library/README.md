# library/ — shared assets (PLACEHOLDERS)

Everything here is copied from `reference/costco_project_example` **only as a test placeholder**.
The owner will supply the channel's own character (also the channel logo), its poses and sounds.
The engine has no hard-coded pose names, file names or character look — it only reads what props.json gives it,
and the backend builds props from the manifests below. Swapping assets = replace files + update the manifest.

- `poses/` — transparent PNG per pose + `poses.json`: `{"poses":[{name, file, tags, width, height}]}`.
  `width`/`height` = native PNG pixel size (the engine keeps the aspect ratio; feet = bottom edge, figure centred).
  Pose PNGs should be trimmed to the figure with the feet touching the bottom edge.
- `sfx/` — one-shot `.wav` + `sfx.json` manifest (`name`, `file`, `use`); `sfx/music/` — music beds (in `sfx.json` → `music`).
- `style/samples/` — 5 sample backgrounds (style reference + engine fixture); `style/character/` — character reference sheets.
