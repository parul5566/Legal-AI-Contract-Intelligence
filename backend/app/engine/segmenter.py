"""Split document text into sections by heading heuristics."""
import re
from dataclasses import dataclass, field

from app.engine.parser import ParsedDoc, page_for_offset

# Heading patterns: "1. TITLE", "ARTICLE 3", "SECTION 4.2", "WITNESSETH",
# numbered like "4.2 Payment", ALL CAPS line, or "X. Words" ending without period.
HEADING_RE = re.compile(
    r"""^(
        (?P<roman>[IVXLC]+\.\s+.+)
      | (?P<article>ARTICLE\s+[IVXLC0-9]+.*)
      | (?P<section>SECTION\s+[0-9]+(?:\.[0-9]+)*.*)
      | (?P<num>(?:\d{1,2}\.\d{1,2}|\d{1,2}\.)\s+\S.*)
      | (?P<caps>[A-Z][A-Z0-9 ,'&/()\-]{4,80})
    )$""",
    re.VERBOSE,
)

KNOWN_HEADINGS = {
    "agreement", "background", "recitals", "witnesseth", "definitions",
    "term", "termination", "payment", "confidentiality", "indemnification",
    "liability", "warranty", "warranties", "insurance", "assignment",
    "governing law", "dispute resolution", "arbitration", "force majeure",
    "notices", "miscellaneous", "general provisions", "intellectual property",
    "data protection", "non-compete", "non-solicitation", "renewal", "compliance",
    "scope of services", "obligations", "representations", "renewal term",
}

NOISE_WORDS = {"exhibit", "appendix", "signature", "in witness whereof", "page"}


@dataclass
class Section:
    idx: int
    heading: str
    body: str
    char_start: int
    char_end: int
    page: int = 1


def _looks_like_heading(line: str) -> bool:
    stripped = line.strip()
    if not (3 <= len(stripped) <= 90):
        return False
    if any(n in stripped.lower() for n in NOISE_WORDS):
        return False
    m = HEADING_RE.match(stripped)
    if not m:
        return False
    # ALL CAPS heading must contain a known word or be a full-caps short line
    if m.group("caps") is not None:
        low = stripped.lower()
        return any(k in low for k in KNOWN_HEADINGS)
    return True


def segment(parsed: ParsedDoc) -> list[Section]:
    lines = parsed.full_text.split("\n")
    sections: list[Section] = []
    current_heading = "Preamble"
    current_lines: list[str] = []
    current_start = 0
    pos = 0
    heading_pos = 0

    def flush(end: int):
        body = "\n".join(current_lines).strip()
        if body:
            sections.append(
                Section(
                    idx=len(sections),
                    heading=current_heading.strip()[:500],
                    body=body,
                    char_start=current_start,
                    char_end=current_start + len("\n".join(current_lines)),
                    page=page_for_offset(parsed, current_start),
                )
            )

    for line in lines:
        line_len = len(line) + 1  # + newline
        if _looks_like_heading(line) and current_lines:
            flush(pos)
            current_heading = line.strip().lstrip("0123456789. ").strip() or line.strip()
            current_lines = []
            current_start = pos
            heading_pos = pos
        current_lines.append(line)
        pos += line_len
    flush(pos)

    # renumber + attach pages
    for i, s in enumerate(sections):
        s.idx = i
        s.page = page_for_offset(parsed, s.char_start)
    return sections
