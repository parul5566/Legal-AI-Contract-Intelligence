from app.engine.parser import ParsedDoc
from app.engine.segmenter import segment


def _parsed(text: str) -> ParsedDoc:
    return ParsedDoc(pages=[text], full_text=text, page_breaks=[0])


def test_basic_sectioning():
    text = (
        "This agreement is between A and B.\n\n"
        "1. PAYMENT TERMS\nCustomer shall pay within 30 days.\n\n"
        "2. TERMINATION\nEither party may terminate.\n\n"
        "9. GOVERNING LAW\nThe laws of Delaware apply.\n"
    )
    sections = segment(_parsed(text))
    headings = [s.heading for s in sections]
    assert len(sections) >= 3
    assert any("PAYMENT" in h.upper() for h in headings)
    assert any("TERMINATION" in h.upper() for h in headings)
    assert any("GOVERNING" in h.upper() for h in headings)


def test_numbered_headings():
    text = "Preamble text here.\n\n4.2 Payment Schedule\nFees due monthly.\n\n4.3 Audit\nRights reserved.\n"
    sections = segment(_parsed(text))
    heads = [s.heading for s in sections]
    assert any("Payment Schedule" in h for h in heads)
    assert any("Audit" in h for h in heads)


def test_spans_cover_text():
    text = "Intro.\n\n1. TITLE ONE\nBody body body.\n\n2. TITLE TWO\nMore body text.\n"
    sections = segment(_parsed(text))
    for s in sections:
        snippet = text[s.char_start : s.char_end]
        assert snippet.strip(), "span should select non-empty text"
        assert s.body.strip() in text


def test_empty_text():
    assert segment(_parsed("")) == []


def test_no_headings_single_section():
    text = "Just one long paragraph of text without any headings at all here."
    sections = segment(_parsed(text))
    assert len(sections) == 1
    assert sections[0].heading == "Preamble"
