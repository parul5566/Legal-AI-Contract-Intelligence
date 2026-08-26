"""AI summarization: LLM with deterministic fallback."""
from app.engine.clauses import ClauseCandidate
from app.engine.risks import RiskHit
from app.engine.taxonomy import category_label

PROMPT = """You are a contract summarization engine for business stakeholders (non-lawyers).
Summarize the contract below into JSON with EXACTLY these keys:
{{
 "executive": "3-6 sentence executive summary in plain business language",
 "key_obligations": ["..."],
 "important_dates": ["..."],
 "payments": ["..."],
 "major_risks": ["..."],
 "termination": "2-4 sentences on termination conditions",
 "restrictions": ["..."],
 "compliance": ["..."],
 "health_score": 0-100,
 "health_verdict": "one-line verdict"
}}
health_score: 100 = very well-balanced contract, 0 = severely one-sided/risky.
Use ONLY information from the contract. No commentary outside the JSON.

CONTRACT:
{contract}

EXTRACTED CLAUSES (category: text):
{clauses}

IDENTIFIED RISKS (severity — title):
{risks}"""


def _fallback(
    doc_title: str,
    clauses: list[ClauseCandidate],
    risks: list[RiskHit],
) -> dict:
    by_cat: dict[str, list[str]] = {}
    for c in clauses:
        by_cat.setdefault(c.category, []).append(c.text[:400])

    payments = [t[:200] for t in by_cat.get("payment_terms", [])] or [
        "No payment terms detected"
    ]
    term = by_cat.get("term_termination", ["No termination clause detected"])[0]
    major = [f"{r.severity.upper()}: {r.title}" for r in risks[:8]] or [
        "No significant risks detected"
    ]
    sev_weight = {"low": 4, "medium": 9, "high": 16, "critical": 26}
    penalty = sum(sev_weight.get(r.severity, 5) for r in risks)
    missing = sum(1 for r in risks if r.category == "missing_clause")
    score = max(5, 100 - penalty - missing * 5)

    cats_found = ", ".join(category_label(c) for c in list(by_cat)[:10]) or "few clauses"
    executive = (
        f"This {doc_title or 'contract'} covers {cats_found}. "
        f"Analysis identified {len(clauses)} clauses and {len(risks)} potential risks "
        f"({sum(1 for r in risks if r.severity in ('high', 'critical'))} high or critical). "
        "This summary was generated offline from extracted clauses; an AI-enhanced summary "
        "will appear when the analysis service is available."
    )
    verdict = (
        "Well-balanced" if score >= 75 else
        "Acceptable with review" if score >= 50 else
        "Requires legal review before signing"
    )
    return {
        "executive": executive,
        "key_obligations": [c.text[:300] for c in clauses if c.category in
                            ("compliance", "term_termination", "non_compete",
                             "non_solicitation", "insurance")][:8] or
                           ["No explicit obligations detected"],
        "important_dates": [],
        "payments": payments,
        "major_risks": major,
        "termination": term[:800],
        "restrictions": [c.text[:300] for c in clauses if c.category in
                         ("confidentiality", "non_compete", "non_solicitation",
                          "assignment")][:6] or ["None detected"],
        "compliance": [c.text[:300] for c in clauses if c.category in
                       ("compliance", "data_protection")][:6] or ["None detected"],
        "health_score": min(100, score),
        "health_verdict": verdict,
        "model": "deterministic",
    }


def summarize(
    doc_title: str,
    full_text: str,
    clauses: list[ClauseCandidate],
    risks: list[RiskHit],
) -> dict:
    from app import llm

    if not llm.available():
        return _fallback(doc_title, clauses, risks)

    clauses_txt = "\n".join(
        f"[{i}] {c.category}: {c.text[:800]}" for i, c in enumerate(clauses)
    )[:12000]
    risks_txt = "\n".join(f"{r.severity} — {r.title}" for r in risks)[:3000]
    contract = (full_text or "")[:14000]

    try:
        data = llm.chat_json(
            [
                {
                    "role": "system",
                    "content": PROMPT.format(
                        contract=contract, clauses=clauses_txt, risks=risks_txt
                    ),
                }
            ],
            max_tokens=2500,
        )
        out = {
            "executive": str(data.get("executive", ""))[:4000],
            "key_obligations": [str(x)[:500] for x in data.get("key_obligations", [])][:10],
            "important_dates": [str(x)[:200] for x in data.get("important_dates", [])][:10],
            "payments": [str(x)[:300] for x in data.get("payments", [])][:10],
            "major_risks": [str(x)[:300] for x in data.get("major_risks", [])][:10],
            "termination": str(data.get("termination", ""))[:1500],
            "restrictions": [str(x)[:300] for x in data.get("restrictions", [])][:10],
            "compliance": [str(x)[:300] for x in data.get("compliance", [])][:10],
            "health_score": int(max(0, min(100, int(data.get("health_score", 50))))),
            "health_verdict": str(data.get("health_verdict", ""))[:250],
            "model": "ai",
        }
        if out["executive"]:
            return out
    except Exception:  # noqa: BLE001 — LLM down/malformed → fallback
        pass
    return _fallback(doc_title, clauses, risks)
