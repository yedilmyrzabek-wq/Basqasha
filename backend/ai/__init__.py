"""AI layer (ai-engineer). Entry points for the backend:

    from ai.factory import build_ai          # wires everything from app.config settings + a ledger
    ai = build_ai(ledger)
    ai.idea(transcript, ...)                  -> brief.schema.json doc            (step 2)
    ai.facts(brief, angle, ...)               -> FactsResult(.doc = facts.schema.json)  (step 3)
    ai.writer.write(ScriptRequest, ctx)       -> script.schema.json doc          (step 4)
    ai.originality(script, reference, ctx)    -> (script, originality report)    (step 4)
    ai.tts(script)                            -> TtsExport                       (step 5 text)
"""
