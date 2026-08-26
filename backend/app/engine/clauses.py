"""Clause detection: heuristic candidates + optional LLM refinement."""
import re
from dataclasses import dataclass

from app.engine.taxonomy import CLAUSE_CATEGORIES

# phrasal keywords with word-boundary regex
_KW_CACHE: dict[str, list[re.Pattern]] = {}


def _patterns() -> dict[str, list[re.Pattern]]:
    if not _KW_CACHE:
        for cat, spec in CLAUSE_CATEGORIES.items():
            pats = []
            for kw in spec["keywords"]:
                if "[" in kw:  # already regex (licen[cs]e)
                    pats.append(re.compile(kw, re.IGNORECASE))
                else:
                    pats.append(re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE))
            _KW_CACHE[cat] = pats
    return _KW_CACHE


@dataclass
class ClauseCandidate:
    category: str
    text: str
    char_start: int
    char_end: int
    page: int
    section_id: int | None
    confidence: float
    title: str = ""
    source: str = "heuristic"


def score_paragraph(paragraph: str, category: str) -> int:
    hits = 0
    for pat in _patterns()[category]:
        hits += len(pat.findall(paragraph))
    return hits


def split_paragraphs(text: str) -> list[tuple[int, int]]:
    """Yield (start, end) spans for paragraphs separated by blank lines."""
    spans = []
    start = None
    pos = 0
    for line in text.split("\n"):
        if line.strip():
            if start is None:
                start = pos
        elif start is not None:
            spans.append((start, pos))
            start = None
        pos += len(line) + 1
    if start is not None:
        spans.append((start, pos))
    return spans


def find_candidates(
    full_text: str,
    sections: list,  # list[Section]
) -> list[ClauseCandidate]:
    """Detect clause candidates deterministically."""
    from app.engine.taxonomy import EXPECTED_CATEGORIES

    all_cats = list(CLAUSE_CATEGORIES.keys())
    candidates: list[ClauseCandidate] = []
    seen_spans: list[tuple[str, int, int]] = []

    def already_covered(cat: str, s: int, e: int) -> bool:
        for c, ss, ee in seen_spans:
            if c == cat and not (e <= ss or s >= ee):
                return True
        return False

    for sec in sections:
        body = sec.body
        offset = sec.char_start
        for s, e in split_paragraphs(body):
            para = full_text[offset + s : offset + e]
            if not para.strip():
                para = body[s:e]
            para = para.strip()
            if len(para) < 40:
                continue
            scored = {c: score_paragraph(para, c) for c in all_cats}
            best = max(scored, key=lambda c: scored[c])
            hits = scored[best]
            if hits == 0:
                continue
            second = sorted(scored.values(), reverse=True)[1]
            margin = hits - second
            # strong signal: multiple hits with a clear winner, or one strong
            # category-specific keyword with no competition
            strong = (hits >= 2 and margin >= 1) or (hits >= 1 and margin >= 1 and len(para) >= 45)
            if strong and not already_covered(best, s, e):
                conf = min(0.95, 0.45 + 0.12 * hits + 0.05 * min(margin, 4))
                candidates.append(
                    ClauseCandidate(
                        category=best,
                        text=para[:6000],
                        char_start=offset + s,
                        char_end=offset + e,
                        page=sec.page,
                        section_id=getattr(sec, "id", None),
                        confidence=round(conf, 2),
                        title=CLAUSE_CATEGORIES[best]["label"],
                        source="heuristic",
                    )
                )
                seen_spans.append((best, s, e))
    return candidates


LLM_REFINE_PROMPT = """You are a legal NLP clause extraction engine.
Given numbered paragraph candidates from a contract, classify each into exactly one
category and rate confidence. Categories:
{cats}

Return JSON: {{"items": [{{"id": <n>, "category": "<cat>", "confidence": 0.0-1.0}}]}}
Return an empty items list if nothing fits. No commentary."""


def refine_with_llm(candidates: list[ClauseCandidate]) -> list[ClauseCandidate]:
    """Ask the LLM to re-classify ambiguous candidates (0.35-0.65 confidence)."""
    from app import llm

    if not candidates:
        return candidates
    ambiguous = [c for c in candidates if c.confidence < 0.65]
    if not ambiguous:
        return candidates

    cats = ", ".join(CLAUSE_CATEGORIES.keys())
    listing = []
    for i, c in enumerate(ambiguous):
        listing.append({"id": i, "text": c.text[:1200]})
    try:
        data = llm.chat_json(
            [
                {"role": "system", "content": LLM_REFINE_PROMPT.format(cats=cats)},
                {"role": "user", "content": str(listing)},
            ],
            max_tokens=2000,
        )
    except llm.LLMError:
        return candidates

    items = data.get("items", []) if isinstance(data, dict) else []
    for item in items:
        try:
            idx = int(item["id"])
            cat = item["category"]
            conf = float(item.get("confidence", 0.5))
        except (KeyError, TypeError, ValueError):
            continue
        if 0 <= idx < len(ambiguous) and cat in CLAUSE_CATEGORIES:
            c = ambiguous[idx]
            if cat != c.category:
                c.category = cat
                c.title = CLAUSE_CATEGORIES[cat]["label"]
            c.confidence = round(min(0.98, max(0.3, conf)), 2)
            c.source = "ai"
    return candidates
