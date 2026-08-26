"""Extract text from PDF / DOCX / TXT files."""
from dataclasses import dataclass, field


@dataclass
class ParsedDoc:
    pages: list[str] = field(default_factory=list)
    full_text: str = ""
    page_breaks: list[int] = field(default_factory=list)  # char offsets where each page starts

    @property
    def page_count(self) -> int:
        return max(1, len(self.pages))


def _pdf(path: str) -> ParsedDoc:
    from pdfminer.high_level import extract_pages, extract_text
    from pdfminer.layout import LTTextContainer

    pages: list[str] = []
    for page_layout in extract_pages(path):
        chunks = []
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                chunks.append(element.get_text())
        pages.append("\n".join(chunks).strip())

    if not pages:
        # fallback: single-blob extraction
        full = extract_text(path) or ""
        pages = [full]

    full_text = ""
    breaks: list[int] = []
    for p in pages:
        breaks.append(len(full_text))
        full_text += p + "\n\n"
    return ParsedDoc(pages=pages, full_text=full_text.strip(), page_breaks=breaks)


def _docx(path: str) -> ParsedDoc:
    import docx

    d = docx.Document(path)
    paras = [p.text for p in d.paragraphs]
    text = "\n".join(paras)
    return ParsedDoc(pages=[text], full_text=text, page_breaks=[0])


def _txt(path: str) -> ParsedDoc:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    return ParsedDoc(pages=[text], full_text=text, page_breaks=[0])


def parse_file(path: str, mime: str) -> ParsedDoc:
    if "pdf" in mime:
        return _pdf(path)
    if "officedocument" in mime or "wordprocessingml" in mime or mime.endswith("docx"):
        return _docx(path)
    return _txt(path)


def page_for_offset(parsed: ParsedDoc, offset: int) -> int:
    page = 1
    for i, b in enumerate(parsed.page_breaks):
        if offset >= b:
            page = i + 1
        else:
            break
    return page
