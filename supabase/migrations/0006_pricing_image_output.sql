-- Nano Banana 2.1 bills output / thinking tokens at $30 per 1M (2K image = 1,680 tokens = $0.0504).
-- The row was missing, so thinking tokens of image calls were recorded at $0.
insert into pricing (provider, model, unit, usd_per_unit, effective_from, source_url)
values ('google', 'gemini-nano-banana-2.1', '1M_output_tokens', 30.0, '2026-10-16', 'https://ai.google.dev/gemini-api/docs/pricing')
on conflict do nothing;
