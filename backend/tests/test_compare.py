from app.engine.clauses import ClauseCandidate
from app.engine.compare import compare, summarize_changes


def cand(category, text):
    return ClauseCandidate(
        category=category, text=text, char_start=0, char_end=len(text),
        page=1, section_id=None, confidence=0.9, title=category, source="heuristic",
    )


PAY_A = (
    "Customer shall pay Supplier the fees set forth in each SOW within sixty (60) days "
    "of receipt of a correct invoice with interest at 1.5% per month."
)
PAY_B = (
    "Customer shall pay Supplier the fees set forth in each SOW within thirty (30) days "
    "of receipt of a correct invoice with interest at 1.0% per month."
)


def test_modified_detection():
    a = [cand("payment_terms", PAY_A)]
    b = [cand("payment_terms", PAY_B)]
    changes = compare(a, b)
    assert len(changes) == 1
    assert changes[0].kind == "modified"
    assert changes[0].material  # numeric change


def test_added_removed():
    a = [cand("payment_terms", PAY_A)]
    b = [cand("payment_terms", PAY_B), cand("insurance", "Supplier maintains insurance.")]
    changes = compare(a, b)
    kinds = {c.kind for c in changes}
    assert "added" in kinds
    added = [c for c in changes if c.kind == "added"]
    assert added[0].category == "insurance"


def test_removed():
    a = [cand("payment_terms", PAY_A), cand("warranty", "Supplier warrants the deliverables.")]
    b = [cand("payment_terms", PAY_B)]
    changes = compare(a, b)
    removed = [c for c in changes if c.kind == "removed"]
    assert len(removed) == 1
    assert removed[0].category == "warranty"


def test_identical_clause_no_change():
    a = [cand("governing_law", "This agreement is governed by the laws of Delaware.")]
    b = [cand("governing_law", "This agreement is governed by the laws of Delaware.")]
    changes = compare(a, b)
    assert changes == []


def test_similarity_scores():
    a = [cand("payment_terms", PAY_A)]
    b = [cand("payment_terms", PAY_B)]
    changes = compare(a, b)
    assert 0.0 < changes[0].similarity < 1.0


def test_both_empty():
    assert compare([], []) == []


def test_summary_mentions_counts():
    changes = compare(
        [cand("payment_terms", PAY_A), cand("warranty", "w")],
        [cand("payment_terms", PAY_B), cand("insurance", "i")],
    )
    summary = summarize_changes(changes, "A", "B")
    assert "1 added" in summary
    assert "1 removed" in summary
