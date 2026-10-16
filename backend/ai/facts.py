"""Step 3: facts with sources.

Primary path: Gemini + Google Search grounding. Fallback (grounding refused: free tier / quota):
code fetches English Wikipedia articles, the model extracts facts with verbatim evidence quotes,
and code verifies each quote (and the number) against the fetched text.

Call: research_facts(llm, brief, angle, language=..., ctx=..., model=..., cheap_model=...) -> FactsResult
(.doc is a facts.schema.json document).
"""
from __future__ import annotations

import json
import logging
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Mapping

from app.providers.interfaces import CallContext, ILLM
from ai.gemini import GroundingUnavailable, ModelUnavailable
from ai.prompts import LANGUAGE_NAMES, load_prompt
from ai.schemas import DocFactsOut, FactsOut, QueriesOut, validate_doc
from ai.textnorm_kk import fix_homoglyphs

log = logging.getLogger("ai.facts")
UA = {"User-Agent": "BasqashaBot/0.1 (local explainer pipeline; contact: operator)"}
PRIMARY_HINTS = ("doi.org", "pubmed", "ncbi.nlm.nih.gov", ".gov", ".edu", "who.int", "un.org",
                 "worldbank.org", "oecd.org", "stat.gov.kz", "nature.com", "sciencedirect.com",
                 "springer.com", "wiley.com", "apa.org", "jstor.org", "ac.uk")
DOC_CHARS = 14_000


@dataclass
class FactsResult:
    doc: dict[str, Any]
    method: str                                  # grounding | wikipedia_fallback
    documents: list[dict[str, str]] = field(default_factory=list)   # fallback: id, title, url


def _sensitive_note(brief: Mapping[str, Any]) -> str:
    topics = brief.get("sensitive_topics") or []
    if not topics:
        return ""
    return (f"Sensitive subjects: {', '.join(topics)}. Every number needs >= 2 independent sources; "
            "keep a strictly neutral tone.")


def _is_primary(url: str) -> bool:
    return any(h in url.lower() for h in PRIMARY_HINTS)


def _finish(facts: list[dict[str, Any]], language: str) -> dict[str, Any]:
    for i, f in enumerate(facts, 1):
        f["id"] = f"f{i:02d}"
        srcs = f["sources"]
        f["on_screen"] = (f["status"] == "verified" and len(srcs) >= 2
                          and any(s.get("is_primary") for s in srcs))
    doc = {"language": language, "facts": facts}
    validate_doc("facts", doc)
    return doc


# ------------------------------------------------------------------ grounded path
def _resolve(url: str) -> str:
    """Grounding chunk URIs are redirect links; follow them to the real page URL."""
    try:
        req = urllib.request.Request(url, method="HEAD", headers=UA)
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.geturl()
    except Exception:
        return url


def _grounded(llm: ILLM, brief, angle, language, ctx, model, max_facts) -> FactsResult:
    text = load_prompt("facts").render(
        language_name=LANGUAGE_NAMES[language], brief_json=brief, angle_json=angle,
        max_facts=str(max_facts), sensitive_note=_sensitive_note(brief))
    res = llm.generate_json(prompt=text, response_model=FactsOut, model=model, ctx=ctx, grounding=True)
    found = {urllib.parse.urlparse(_resolve(u)).netloc.removeprefix("www.") for u in res.grounding_urls}
    facts = []
    for f in res.value.facts:
        sources = [{"url": s.url, "title": s.title, "is_primary": bool(s.is_primary or _is_primary(s.url))}
                   for s in f.sources if s.url.startswith("http")]
        status = f.status
        note = f.note or ""
        domains = {urllib.parse.urlparse(s["url"]).netloc.removeprefix("www.") for s in sources}
        if status == "verified" and (not sources or (found and not domains & found)):
            status, note = "unverified", (note + " [авто: источник не найден в результатах поиска]").strip()
        fact = {"claim": fix_homoglyphs(f.claim), "value": f.value, "status": status, "sources": sources}
        if note:
            fact["note"] = note
        facts.append(fact)
    return FactsResult(doc=_finish(facts, language), method="grounding")


# ------------------------------------------------------------------ Wikipedia fallback
def _wiki_get(params: dict[str, str]) -> dict[str, Any]:
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({**params, "format": "json"})
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
        return json.load(r)


def fetch_wikipedia(queries: list[str], max_docs: int = 6) -> list[dict[str, str]]:
    titles: list[str] = []
    for q in queries:
        try:
            hits = _wiki_get({"action": "query", "list": "search", "srsearch": q, "srlimit": "2"})
        except Exception as e:  # network hiccup: skip the query
            log.warning("wikipedia search %r failed: %s", q, e)
            continue
        for h in hits.get("query", {}).get("search", [])[:1 if len(titles) >= 3 else 2]:
            if h["title"] not in titles:
                titles.append(h["title"])
        if len(titles) >= max_docs:
            break
    docs = []
    for t in titles[:max_docs]:
        data = _wiki_get({"action": "query", "prop": "extracts|info", "explaintext": "1",
                          "inprop": "url", "titles": t, "redirects": "1"})
        for page in data.get("query", {}).get("pages", {}).values():
            text = re.sub(r"\n{2,}", "\n", page.get("extract", ""))
            text = text.split("\n== See also ==")[0].split("\n== References ==")[0]
            if len(text) > 500:
                docs.append({"id": f"D{len(docs) + 1}", "title": page["title"],
                             "url": page.get("fullurl", ""), "text": text[:DOC_CHARS]})
    return docs


def _norm(s: str) -> str:
    s = s.lower().replace("’", "'").replace("“", '"').replace("”", '"').replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", re.sub(r"[^\w%.,'\"-]+", " ", s)).strip()


def _digits(s: str | None) -> list[str]:
    """Number tokens incl. a decade 's' ('1960s' != '1960')."""
    return re.findall(r"\d+(?:'s|’s|s)?(?![A-Za-z])", (s or "").replace(",", ""))


def _from_docs(llm: ILLM, brief, angle, language, ctx, model, cheap_model, max_facts) -> FactsResult:
    q_prompt = load_prompt("facts_queries").render(brief_json=brief, angle_json=angle, max_queries="6")
    try:
        queries = llm.generate_json(prompt=q_prompt, response_model=QueriesOut, model=cheap_model, ctx=ctx).value.queries
    except ModelUnavailable:
        queries = llm.generate_json(prompt=q_prompt, response_model=QueriesOut, model=model, ctx=ctx).value.queries
    docs = fetch_wikipedia(queries)
    if not docs:
        raise RuntimeError(f"facts fallback: no Wikipedia documents for {queries}")
    by_id = {d["id"]: d for d in docs}
    docs_text = "\n\n".join(f"### {d['id']} — {d['title']} ({d['url']})\n{d['text']}" for d in docs)
    text = load_prompt("facts_docs").render(
        language_name=LANGUAGE_NAMES[language], brief_json=brief, angle_json=angle,
        max_facts=str(max_facts), documents=docs_text)
    out = llm.generate_json(prompt=text, response_model=DocFactsOut, model=model, ctx=ctx).value

    norm_docs = {i: _norm(d["text"]) for i, d in by_id.items()}
    facts = []
    for f in out.facts:
        ok_sources: dict[str, dict[str, Any]] = {}
        quotes_ok = []
        for ev in f.evidence:
            d = by_id.get(ev.doc_id.strip())
            if d and len(ev.quote) >= 20 and _norm(ev.quote) in norm_docs[d["id"]]:
                ok_sources[d["url"]] = {"url": d["url"], "title": f"Wikipedia — {d['title']}", "is_primary": False}
                quotes_ok.append(ev.quote)
        value_ok = not _digits(f.value) or any(set(_digits(f.value)) <= set(_digits(q)) for q in quotes_ok)
        if f.disputed and ok_sources:
            status = "conflicting"
        elif ok_sources and value_ok:
            status = "verified"
        else:
            status = "unverified"
        note = (f.note or "").strip()
        if ok_sources and not value_ok:
            note = (note + " [авто: число не найдено в цитате источника]").strip()
        fact = {"claim": fix_homoglyphs(f.claim), "value": f.value, "status": status,
                "sources": list(ok_sources.values())}
        if note:
            fact["note"] = note
        facts.append(fact)
    return FactsResult(doc=_finish(facts, language), method="wikipedia_fallback",
                       documents=[{k: d[k] for k in ("id", "title", "url")} for d in docs])


# ------------------------------------------------------------------ public
def research_facts(llm: ILLM, brief: Mapping[str, Any], angle: Mapping[str, Any], *, language: str,
                   ctx: CallContext, model: str, cheap_model: str, max_facts: int = 12,
                   use_grounding: bool = True) -> FactsResult:
    """``brief`` = brief.schema.json#/properties/brief, ``angle`` = the chosen angle."""
    if use_grounding:
        try:
            return _grounded(llm, brief, angle, language, ctx, model, max_facts)
        except GroundingUnavailable as e:
            log.warning("grounding unavailable (%s) -> Wikipedia fallback", str(e)[:160])
    return _from_docs(llm, brief, angle, language, ctx, model, cheap_model, max_facts)


def verified_facts(facts_doc: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Facts a script may use for numbers (status verified only)."""
    return [f for f in facts_doc["facts"] if f["status"] == "verified"]


def writer_facts(facts_doc: Mapping[str, Any]) -> list[dict[str, Any]]:
    """What to put into ScriptRequest.facts: verified facts + conflicting ones (used only as caveats)."""
    return [f for f in facts_doc["facts"] if f["status"] in ("verified", "conflicting")]
