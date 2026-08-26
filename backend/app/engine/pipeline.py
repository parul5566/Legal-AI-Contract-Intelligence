"""End-to-end document analysis pipeline (runs in worker process)."""
import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app import llm
from app.engine.clauses import find_candidates, refine_with_llm
from app.engine.compare import Change, compare, summarize_changes
from app.engine.parser import parse_file
from app.engine.risks import enrich_with_llm, evaluate_rules
from app.engine.segmenter import segment
from app.engine.summarizer import summarize
from app.models import (
    Clause,
    Comparison,
    ComparisonChange,
    Document,
    DocumentSection,
    RiskFinding,
    Summary,
)

DOCTYPE_RE = [
    (r"master services agreement|msa", "MSA"),
    (r"non-?disclosure|nda|confidentiality agreement", "NDA"),
    (r"statement of work|sow", "SOW"),
    (r"employment agreement", "Employment Agreement"),
    (r"lease", "Lease"),
    (r"licen[cs]e agreement", "License Agreement"),
    (r"purchase agreement|supply agreement", "Purchase Agreement"),
    (r"services agreement", "Services Agreement"),
]

PARTY_RE = re.compile(r"between\s+(.{3,80}?)\s+(?:and|&)\s+(.{3,80}?)[,.]", re.IGNORECASE)
DATE_RE = re.compile(
    r"\b(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+\d{4}|(?:January|February|March|April|May|June|July|"
    r"August|September|October|November|December)\s+\d{1,2},?\s+\d{4})\b"
)
EFFECTIVE_RE = re.compile(r"effective (?:as of )?(\w+ \d{1,2},? \d{4})", re.IGNORECASE)
JURISDICTION_RE = re.compile(
    r"(?:laws of|governed by the laws of)\s+(?:the\s+)?(State of\s+)?([A-Z][a-zA-Z .]{2,30})"
)


def extract_metadata(text: str, filename: str) -> dict:
    doc_type = "Contract"
    low = text[:4000].lower()
    for pat, dt in DOCTYPE_RE:
        if re.search(pat, low):
            doc_type = dt
            break
    parties = []
    m = PARTY_RE.search(text[:3000])
    if m:
        parties = [g.strip(" .,") for g in m.groups()]
    dates = DATE_RE.findall(text[:6000])
    effective = EFFECTIVE_RE.search(text[:6000])
    jurisdiction = None
    jm = JURISDICTION_RE.search(text)
    if jm:
        jurisdiction = (jm.group(1) or "") + jm.group(2)
        jurisdiction = jurisdiction.strip()
    return {
        "doc_type": doc_type,
        "title": (text.strip().split("\n")[0][:200] or filename),
        "parties": parties,
        "effective_date": effective.group(1) if effective else (dates[0] if dates else None),
        "expiry_date": dates[-1] if len(dates) > 1 else None,
        "jurisdiction": jurisdiction,
    }


def analyze_document(db: Session, doc: Document, upload_dir: str) -> None:
    """Parse + analyze + persist. Raises on fatal errors (worker marks failed)."""
    doc.status = "parsing"
    db.commit()

    parsed = parse_file(f"{upload_dir}/{doc.filename}", doc.mime)
    if not parsed.full_text.strip():
        raise ValueError("No extractable text found in document (scanned PDFs need OCR)")

    doc.char_count = len(parsed.full_text)
    doc.page_count = parsed.page_count

    # sections (delete children first: risks reference clauses, clauses reference sections,
    # comparison_changes reference clauses)
    from app.models import (
        ComparisonChange as CC,
        DocumentSection,
        RiskFinding as RF,
        Summary as Sum,
    )

    stale_clause_ids = [
        row[0]
        for row in db.query(Clause.id).filter(Clause.document_id == doc.id).all()
    ]
    if stale_clause_ids:
        db.query(CC).filter(
            (CC.clause_a_id.in_(stale_clause_ids)) | (CC.clause_b_id.in_(stale_clause_ids))
        ).delete(synchronize_session=False)
    db.query(RF).filter(RF.document_id == doc.id).delete(synchronize_session=False)
    db.query(Clause).filter(Clause.document_id == doc.id).delete(synchronize_session=False)
    db.query(Sum).filter(Sum.document_id == doc.id).delete(synchronize_session=False)
    db.query(DocumentSection).filter(DocumentSection.document_id == doc.id).delete(
        synchronize_session=False
    )
    db.flush()
    sections = segment(parsed)
    for s in sections:
        doc.sections.append(
            DocumentSection(
                idx=s.idx, heading=s.heading, body=s.body,
                char_start=s.char_start, char_end=s.char_end, page=s.page,
            )
        )
    db.commit()

    doc.status = "analyzing"
    db.commit()

    candidates = find_candidates(parsed.full_text, doc.sections)
    if llm.available():
        candidates = refine_with_llm(candidates)


    for c in candidates:
        db.add(
            Clause(
                document_id=doc.id,
                section_id=c.section_id,
                category=c.category,
                title=c.title or c.category,
                text=c.text,
                char_start=c.char_start,
                char_end=c.char_end,
                page=c.page,
                confidence=c.confidence,
                source=c.source,
            )
        )
    db.flush()

    clause_objs = (
        db.query(Clause)
        .filter(Clause.document_id == doc.id)
        .order_by(Clause.char_start)
        .all()
    )
    # rebuild candidates bound to persisted clauses for risk linkage
    bound = []
    for c, obj in zip(candidates, clause_objs, strict=False):
        c.section_id = obj.section_id
        bound.append(c)

    risk_hits = evaluate_rules(bound, parsed.full_text)
    if llm.available():
        extra = enrich_with_llm(bound)
        seen = {(h.category, h.title.lower()) for h in risk_hits}
        for h in extra:
            if (h.category, h.title.lower()) not in seen:
                risk_hits.append(h)

    for h in risk_hits:
        clause_id = None
        if h.clause_index is not None and 0 <= h.clause_index < len(clause_objs):
            clause_id = clause_objs[h.clause_index].id
        db.add(
            RiskFinding(
                document_id=doc.id,
                clause_id=clause_id,
                category=h.category,
                severity=h.severity,
                title=h.title,
                explanation=h.explanation,
                suggestion=h.suggestion,
                evidence=h.evidence,
                confidence=h.confidence,
            )
        )
    db.flush()

    risk_objs = db.query(RiskFinding).filter(RiskFinding.document_id == doc.id).all()

    meta = extract_metadata(parsed.full_text, doc.original_name)
    for k, v in meta.items():
        setattr(doc, k, v)

    summ = summarize(
        meta.get("title") or doc.original_name,
        parsed.full_text,
        bound,
        [
            __import__("app.engine.risks", fromlist=["RiskHit"]).RiskHit(
                category=r.category, severity=r.severity, title=r.title,
                explanation=r.explanation, suggestion=r.suggestion, evidence=r.evidence,
                confidence=r.confidence, clause_index=None,
            )
            for r in risk_objs
        ],
    )
    doc.summary = Summary(document_id=doc.id, **summ)
    doc.status = "ready"
    doc.analyzed_at = datetime.now(timezone.utc)
    doc.error = None
    db.commit()


def analyze_comparison(db: Session, cmp_: Comparison) -> None:
    cmp_.status = "processing"
    db.commit()

    from app.engine.clauses import ClauseCandidate

    def load(doc_id: int) -> tuple[Document, list[ClauseCandidate]]:
        d = db.get(Document, doc_id)
        if not d or d.status != "ready":
            raise ValueError(f"Document {doc_id} is not ready for comparison")
        cs = (
            db.query(Clause)
            .filter(Clause.document_id == doc_id)
            .order_by(Clause.char_start)
            .all()
        )
        cands = [
            ClauseCandidate(
                category=c.category, text=c.text, char_start=c.char_start,
                char_end=c.char_end, page=c.page, section_id=c.section_id,
                confidence=c.confidence, title=c.title, source=c.source,
            )
            for c in cs
        ]
        return d, cands

    doc_a, a_clauses = load(cmp_.doc_a_id)
    doc_b, b_clauses = load(cmp_.doc_b_id)

    changes: list[Change] = compare(a_clauses, b_clauses)
    db.query(ComparisonChange).filter(ComparisonChange.comparison_id == cmp_.id).delete()
    db.flush()

    a_clause_ids = [
        c.id
        for c in db.query(Clause)
        .filter(Clause.document_id == doc_a.id)
        .order_by(Clause.char_start)
        .all()
    ]
    b_clause_ids = [
        c.id
        for c in db.query(Clause)
        .filter(Clause.document_id == doc_b.id)
        .order_by(Clause.char_start)
        .all()
    ]

    for ch in changes:
        clause_a_id = (
            a_clause_ids[ch.clause_a_index]
            if ch.clause_a_index is not None and ch.clause_a_index < len(a_clause_ids)
            else None
        )
        clause_b_id = (
            b_clause_ids[ch.clause_b_index]
            if ch.clause_b_index is not None and ch.clause_b_index < len(b_clause_ids)
            else None
        )
        db.add(
            ComparisonChange(
                comparison_id=cmp_.id,
                kind=ch.kind,
                category=ch.category,
                clause_a_id=clause_a_id,
                clause_b_id=clause_b_id,
                text_a=ch.text_a,
                text_b=ch.text_b,
                similarity=ch.similarity,
                material=ch.material,
                rationale=ch.rationale,
            )
        )
    cmp_.summary = summarize_changes(changes, doc_a.original_name, doc_b.original_name)
    cmp_.status = "ready"
    db.commit()
    db.refresh(cmp_)
    db.expire(cmp_, ["changes"])
    db.refresh(cmp_, attribute_names=["changes"])
