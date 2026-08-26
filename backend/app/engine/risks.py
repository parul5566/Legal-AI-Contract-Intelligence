"""Risk identification: deterministic rules + missing clauses + optional LLM pass."""
import re
from dataclasses import dataclass

from app.engine.clauses import ClauseCandidate
from app.engine.taxonomy import EXPECTED_CATEGORIES, category_label

UNLIMITED_RE = re.compile(
    r"(unlimited|without limitation|in no event.{0,40}liability|no limit on liability)",
    re.IGNORECASE,
)
NO_CAP_RE = re.compile(r"liability.{0,120}(shall be unlimited|without cap)", re.IGNORECASE)
CONSEQUENTIAL_RE = re.compile(r"(consequential|indirect|incidental).{0,60}damages", re.IGNORECASE)
CONSEQUENTIAL_EXCLUDED_RE = re.compile(
    r"((exclud\w*|waiv\w*|disclaim\w*)[^.;]{0,80}(consequential|indirect|incidental))"
    r"|((consequential|indirect|incidental)[^.;]{0,80}(damages[^.;]{0,40})?"
    r"(which|that|are|is|shall\s+be)\s+(excluded|waived|disclaimed))"
    r"|((consequential|indirect|incidental)[^.;]{0,60}(excluded|waived|disclaimed))"
    r"|(not\s+(be\s+)?liable[^.;]{0,80}(consequential|indirect|incidental))",
    re.IGNORECASE,
)
ONE_SIDED_INDEM_RE = re.compile(
    r"(customer|supplier|vendor|provider|contractor|client|licensee|buyer)\s+(shall|will|agrees?\s+to)\s+"
    r"(defend[,{0,40}]*|indemnif\w*[,{0,40}]*|hold[s]?\s+harmless[,{0,40}]*)",
    re.IGNORECASE,
)
AUTO_RENEW_RE = re.compile(
    r"(automatic(ally)? renew\w*|renew\w*\s+automatic(ally)?|auto-renew\w*|evergreen)",
    re.IGNORECASE,
)
TERMINATION_FOR_CONVENIENCE_BAD = re.compile(
    r"(sole discretion|at any time.{0,40}without cause|immediately upon written notice)", re.IGNORECASE
)
NO_CAUSE_TERMINATION = re.compile(r"terminat(e|ion).{0,80}(convenience|without cause)", re.IGNORECASE)
AMBIGUOUS_RE = re.compile(
    r"(reasonable (efforts?|discretion|notice)|as (deemed )?(necessary|appropriate)|"
    r"to the extent (practicable|necessary)|industry standard|satisfactory to)",
    re.IGNORECASE,
)
PAYMENT_NET_RE = re.compile(r"net\s+(\d{1,3})\s+day", re.IGNORECASE)
VAGUE_AMOUNT_RE = re.compile(r"(reasonable costs|such other amounts|as (may be )?agreed)", re.IGNORECASE)
GDPR_RE = re.compile(r"(personal data|gdpr|ccpa|data protection)", re.IGNORECASE)
NO_AUDIT_RE = re.compile(r"(no.{0,20}right of audit|audit rights.{0,40}waived)", re.IGNORECASE)


@dataclass
class RiskHit:
    category: str
    severity: str  # low | medium | high | critical
    title: str
    explanation: str
    suggestion: str
    evidence: str
    confidence: float
    clause_index: int | None  # index into the clauses list passed in
    source: str = "rule"


def _risk(cat, sev, title, explanation, suggestion, evidence, confidence, clause_index):
    return RiskHit(
        category=cat,
        severity=sev,
        title=title,
        explanation=explanation,
        suggestion=suggestion,
        evidence=evidence[:600],
        confidence=confidence,
        clause_index=clause_index,
    )


def evaluate_rules(clauses: list[ClauseCandidate], full_text: str) -> list[RiskHit]:
    hits: list[RiskHit] = []
    text = full_text

    for i, c in enumerate(clauses):
        t = c.text
        if c.category == "liability":
            if UNLIMITED_RE.search(t) or NO_CAP_RE.search(t):
                hits.append(
                    _risk(
                        "unlimited_liability", "critical",
                        "Unlimited liability exposure",
                        "The liability clause contains language that removes or appears to "
                        "remove limits on liability, exposing the party to uncapped damages.",
                        "Negotiate an aggregate liability cap (e.g. fees paid in the prior "
                        "12 months) and mutual carve-outs.",
                        t[:400], 0.85, i,
                    )
                )
            elif not re.search(r"(cap|limit|maximum|not exceed)", t, re.IGNORECASE):
                hits.append(
                    _risk(
                        "liability_exposure", "high",
                        "No liability cap detected",
                        "The liability clause does not state a monetary cap; damages may be "
                        "unbounded.",
                        "Add an explicit limitation of liability with a defined cap.",
                        t[:400], 0.7, i,
                    )
                )
            if CONSEQUENTIAL_RE.search(t) and not CONSEQUENTIAL_EXCLUDED_RE.search(t):
                hits.append(
                    _risk(
                        "liability_exposure", "medium",
                        "Consequential damages not excluded",
                        "Consequential/indirect damages are mentioned without an explicit "
                        "mutual exclusion.",
                        "Add a mutual waiver of consequential and indirect damages.",
                        t[:400], 0.65, i,
                    )
                )
        if (
            c.category == "indemnification"
            and ONE_SIDED_INDEM_RE.search(t)
            and not re.search(r"(each party|either party|mutual).{0,60}indemnif|mutual", t, re.IGNORECASE)
        ):
            hits.append(
                _risk(
                    "one_sided_indemnity", "high",
                    "One-sided indemnification",
                    "Indemnification obligations appear to run in one direction only.",
                    "Make indemnification mutual or scope it to third-party IP infringement "
                    "and negligence only.",
                    t[:400], 0.75, i,
                )
            )
        if c.category == "renewal" and AUTO_RENEW_RE.search(t) and not re.search(
            r"(non-renew|opt-out|cancel).{0,120}(notice)", t, re.IGNORECASE
        ):
            hits.append(
                _risk(
                    "auto_renewal", "medium",
                    "Automatic renewal without clear opt-out",
                    "The contract renews automatically and no clear non-renewal mechanism "
                    "was detected.",
                    "Add a non-renewal notice window (e.g. 60 days) and calendar the deadline.",
                    t[:400], 0.7, i,
                )
            )
        if c.category == "term_termination":
            if NO_CAUSE_TERMINATION.search(t) or (
                TERMINATION_FOR_CONVENIENCE_BAD.search(t)
                and not re.search(r"(notice period|days.{0,20}prior)", t, re.IGNORECASE)
            ):
                hits.append(
                    _risk(
                        "unfavorable_termination", "high",
                        "Termination at will / without adequate notice",
                        "Termination appears possible with little or no notice, creating "
                        "revenue and planning risk.",
                        "Require a minimum notice period (30-90 days) for without-cause "
                        "termination.",
                        t[:400], 0.7, i,
                    )
                )
        if c.category == "payment_terms":
            m = PAYMENT_NET_RE.search(t)
            if m and int(m.group(1)) > 60:
                hits.append(
                    _risk(
                        "financial", "low",
                        f"Extended payment terms (Net {m.group(1)})",
                        "Payment terms exceed Net 60, which lengthens cash conversion.",
                        "Negotiate Net 30/45 or early-payment discounts.",
                        t[:400], 0.8, i,
                    )
                )
            if VAGUE_AMOUNT_RE.search(t):
                hits.append(
                    _risk(
                        "financial", "medium",
                        "Open-ended payment obligations",
                        "Payment language refers to unspecified or 'as agreed' amounts.",
                        "Attach a fee schedule or cap variable amounts.",
                        t[:400], 0.6, i,
                    )
                )
        if AMBIGUOUS_RE.search(t) and c.category not in ("governing_law",):
            hits.append(
                _risk(
                    "ambiguity", "low",
                    f"Ambiguous language in {category_label(c.category)}",
                    "The clause relies on vague standards ('reasonable', 'as necessary') "
                    "without objective criteria.",
                    "Define measurable standards or deadlines for the vague terms.",
                    t[:400], 0.55, i,
                )
            )
        if c.category == "data_protection" and GDPR_RE.search(t) and not re.search(
            r"(processor|controller|dpa|data processing addendum)", t, re.IGNORECASE
        ):
            hits.append(
                _risk(
                    "data_privacy", "medium",
                    "Data protection terms may be incomplete",
                    "Personal data is mentioned without clear controller/processor roles or "
                    "a DPA reference.",
                    "Attach a Data Processing Addendum with roles, transfer, and breach "
                    "terms.",
                    t[:400], 0.6, i,
                )
            )

    # missing clauses
    present = {c.category for c in clauses}
    for cat in EXPECTED_CATEGORIES:
        if cat not in present:
            hits.append(
                _risk(
                    "missing_clause", "medium",
                    f"Missing clause: {category_label(cat)}",
                    f"No {category_label(cat).lower()} provision was detected. Its absence "
                    "leaves the parties exposed on this topic.",
                    "Add a standard clause covering this topic before signing.",
                    "", 0.75, None,
                )
            )

    # whole-document rules
    if NO_AUDIT_RE.search(text):
        hits.append(
            _risk(
                "compliance", "medium", "Audit rights waived or absent",
                "The document appears to waive or exclude audit rights.",
                "Retain audit rights with reasonable notice and frequency limits.",
                NO_AUDIT_RE.search(text).group(0), 0.65, None,
            )
        )
    return hits


LLM_RISK_PROMPT = """You are a contract risk analysis engine. Analyze the numbered clauses
and identify ADDITIONAL material risks that the deterministic rules may have missed.
Categories: {cats}. Severities: low, medium, high, critical.

Return JSON: {{"risks": [{{"clause_id": <n or null>, "category": "<cat>", "severity":
"<sev>", "title": "...", "explanation": "...", "suggestion": "...", "confidence": 0.0-1.0}}]}}
Only include genuine, material risks. Max 8. No commentary."""


def enrich_with_llm(clauses: list[ClauseCandidate]) -> list[RiskHit]:
    from app import llm

    if not clauses:
        return []
    from app.engine.taxonomy import RISK_CATEGORIES

    listing = [
        {"id": i, "category": c.category, "text": c.text[:1500]}
        for i, c in enumerate(clauses)
    ]
    try:
        data = llm.chat_json(
            [
                {
                    "role": "system",
                    "content": LLM_RISK_PROMPT.format(cats=", ".join(RISK_CATEGORIES.keys())),
                },
                {"role": "user", "content": str(listing)},
            ],
            max_tokens=3000,
        )
    except llm.LLMError:
        return []

    out: list[RiskHit] = []
    risks = data.get("risks", []) if isinstance(data, dict) else []
    seen_titles = set()
    for r in risks:
        try:
            cat = r["category"]
            sev = r["severity"].lower()
            title = str(r["title"])[:250]
            if cat not in RISK_CATEGORIES or sev not in ("low", "medium", "high", "critical"):
                continue
            if title.lower() in seen_titles:
                continue
            seen_titles.add(title.lower())
            clause_id = r.get("clause_id")
            clause_index = int(clause_id) if clause_id is not None and 0 <= int(clause_id) < len(clauses) else None
            out.append(
                RiskHit(
                    category=cat,
                    severity=sev,
                    title=title,
                    explanation=str(r.get("explanation", ""))[:2000],
                    suggestion=str(r.get("suggestion", ""))[:2000],
                    evidence=clauses[clause_index].text[:400] if clause_index is not None else "",
                    confidence=min(0.95, max(0.3, float(r.get("confidence", 0.6)))),
                    clause_index=clause_index,
                    source="ai",
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return out
