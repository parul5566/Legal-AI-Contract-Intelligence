from app.engine.clauses import find_candidates, score_paragraph, split_paragraphs
from app.engine.segmenter import Section


def _sec(text, start=0, idx=0, sid=None):
    return Section(
        idx=idx, heading="x", body=text, char_start=start, char_end=start + len(text),
        page=1,
    ) if sid is None else _with_id(text, start, idx, sid)


def _with_id(text, start, idx, sid):
    s = Section(idx=idx, heading="x", body=text, char_start=start,
                char_end=start + len(text), page=1)
    s.id = sid
    return s


def test_score_payment_terms():
    para = "Customer shall pay all invoices within thirty (30) days of receipt."
    assert score_paragraph(para, "payment_terms") >= 1
    assert score_paragraph(para, "governing_law") == 0


def test_split_paragraphs_offsets():
    text = "para one\n\npara two\n\npara three"
    spans = split_paragraphs(text)
    assert len(spans) == 3
    for s, e in spans:
        assert text[s:e].startswith("para")


def test_find_candidates_categories():
    text = (
        "Supplier shall indemnify and hold harmless Customer from all claims.\n\n"
        "This agreement is governed by the laws of the State of New York.\n\n"
        "Each party shall keep Confidential Information secret."
    )
    sec = _with_id(text, 0, 0, 1)
    cands = find_candidates(text, [sec])
    cats = {c.category for c in cands}
    assert "indemnification" in cats
    assert "governing_law" in cats
    assert "confidentiality" in cats


def test_find_candidates_confidence_range():
    text = "Supplier shall indemnify and hold harmless Customer from all claims and damages."
    sec = _with_id(text, 0, 0, 1)
    cands = find_candidates(text, [sec])
    for c in cands:
        assert 0.0 <= c.confidence <= 1.0


def test_no_candidates_for_noise():
    text = "Hello world this is just a random note without legal keywords."
    sec = _with_id(text, 0, 0, 1)
    cands = find_candidates(text, [sec])
    assert cands == []


def test_offset_math():
    prefix = "SOME TITLE\n\n"
    text = "Supplier shall indemnify and hold harmless Customer from claims."
    full = prefix + text
    sec = _with_id(prefix + text, 0, 0, 1)
    # paragraph offset = len(prefix); body offsets shift by section start
    cands = find_candidates(full, [sec])
    assert cands, "expected an indemnification candidate"
    c = cands[0]
    extracted = full[c.char_start:c.char_end]
    assert "indemnify" in extracted
