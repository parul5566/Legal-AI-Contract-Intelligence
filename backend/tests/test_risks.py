from app.engine.clauses import ClauseCandidate
from app.engine.risks import evaluate_rules


def cand(category, text):
    return ClauseCandidate(
        category=category, text=text, char_start=0, char_end=len(text),
        page=1, section_id=None, confidence=0.9, title=category, source="heuristic",
    )


def test_unlimited_liability_critical():
    clauses = [cand("liability", "SUPPLIER'S LIABILITY SHALL BE UNLIMITED FOR ANY DAMAGES.")]
    hits = evaluate_rules(clauses, "x")
    assert any(h.category == "unlimited_liability" and h.severity == "critical" for h in hits)


def test_missing_cap_flagged():
    clauses = [cand("liability", "Supplier is liable for direct damages arising hereunder.")]
    hits = evaluate_rules(clauses, "x")
    assert any(h.category == "liability_exposure" and h.severity == "high" for h in hits)


def test_capped_liability_not_flagged():
    clauses = [
        cand(
            "liability",
            "Each party's aggregate liability shall not exceed the fees paid. "
            "Neither party is liable for consequential damages which are excluded.",
        )
    ]
    hits = evaluate_rules(clauses, "x")
    assert not any(
        h.category in ("unlimited_liability", "liability_exposure") for h in hits
    )


def test_one_sided_indemnity():
    clauses = [
        cand("indemnification", "Customer shall indemnify the Supplier against all claims.")
    ]
    hits = evaluate_rules(clauses, "x")
    assert any(h.category == "one_sided_indemnity" for h in hits)


def test_mutual_indemnity_ok():
    clauses = [
        cand(
            "indemnification",
            "Each party shall indemnify the other against third-party IP claims.",
        )
    ]
    hits = evaluate_rules(clauses, "x")
    assert not any(h.category == "one_sided_indemnity" for h in hits)


def test_auto_renewal_without_optout():
    clauses = [cand("renewal", "The term shall renew automatically each year thereafter.")]
    hits = evaluate_rules(clauses, "x")
    assert any(h.category == "auto_renewal" for h in hits)


def test_auto_renewal_with_optout_ok():
    clauses = [
        cand(
            "renewal",
            "The term renews automatically unless either party gives non-renewal notice "
            "60 days prior.",
        )
    ]
    hits = evaluate_rules(clauses, "x")
    assert not any(h.category == "auto_renewal" for h in hits)


def test_missing_clauses_reported():
    # no clauses at all → every expected category reported missing
    hits = evaluate_rules([], "whatever")
    missing = [h for h in hits if h.category == "missing_clause"]
    assert len(missing) >= 6
    assert all(h.clause_index is None for h in missing)


def test_extended_payment_terms():
    clauses = [cand("payment_terms", "Invoices payable net 90 days from receipt.")]
    hits = evaluate_rules(clauses, "x")
    assert any(h.category == "financial" and "Net 90" in h.title for h in hits)


def test_termination_without_notice():
    clauses = [
        cand(
            "term_termination",
            "Either party may terminate this agreement at any time without cause "
            "immediately upon written notice.",
        )
    ]
    hits = evaluate_rules(clauses, "x")
    assert any(h.category == "unfavorable_termination" for h in hits)


def test_severity_vocabulary():
    clauses = [cand("liability", "Liability shall be unlimited")]
    hits = evaluate_rules(clauses, "x")
    for h in hits:
        assert h.severity in ("low", "medium", "high", "critical")
