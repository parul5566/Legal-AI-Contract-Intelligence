"""Contract comparison via TF-IDF cosine similarity + category alignment."""
import re
from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.engine.clauses import ClauseCandidate
from app.engine.taxonomy import category_label

MODIFIED_THRESHOLD = 0.92  # above this (same category) => unchanged
MATCH_THRESHOLD = 0.45  # below this => not a match at all
MATERIAL_HINTS = re.compile(
    r"(unlimited|sole discretion|net\s+\d+|exclusiv|perpetual|irrevocab|"
    r"terminat|liabilit|indemnif|governing law|jurisdiction|renew)",
    re.IGNORECASE,
)


@dataclass
class Change:
    kind: str  # added | removed | modified
    category: str
    text_a: str
    text_b: str
    similarity: float
    material: bool
    rationale: str
    clause_a_index: int | None
    clause_b_index: int | None


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _materiality(sim: float, a: str, b: str, category: str) -> tuple[bool, str]:
    if sim >= MODIFIED_THRESHOLD:
        return False, "Textually near-identical"
    # detect numeric/keyword shifts
    nums_a = set(re.findall(r"\d+", a))
    nums_b = set(re.findall(r"\d+", b))
    changed_nums = nums_a != nums_b
    hints_a = set(MATERIAL_HINTS.findall(a.lower()))
    hints_b = set(MATERIAL_HINTS.findall(b.lower()))
    if changed_nums:
        return True, "Numeric terms changed (amounts, days, thresholds)"
    if hints_a != hints_b:
        return True, "Material legal keywords changed"
    if sim < 0.75:
        return True, f"Substantial rewrite in {category_label(category)} (similarity {sim:.2f})"
    return False, "Minor wording change"


def compare(a_clauses: list[ClauseCandidate], b_clauses: list[ClauseCandidate]) -> list[Change]:
    changes: list[Change] = []
    if not a_clauses and not b_clauses:
        return changes

    texts = [_norm(c.text) for c in a_clauses] + [_norm(c.text) for c in b_clauses]
    try:
        vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)
        matrix = vec.fit_transform(texts)
    except ValueError:
        return changes

    n_a = len(a_clauses)
    sim = cosine_similarity(matrix[:n_a], matrix[n_a:])

    used_b: set[int] = set()
    for i, ca in enumerate(a_clauses):
        row = sim[i]
        # prefer same-category matches
        best_j, best_score = -1, -1.0
        for j in range(len(b_clauses)):
            if j in used_b:
                continue
            score = row[j] + (0.08 if b_clauses[j].category == ca.category else 0)
            if score > best_score:
                best_score, best_j = score, j
        if best_j >= 0 and row[best_j] >= MATCH_THRESHOLD:
            cb = b_clauses[best_j]
            used_b.add(best_j)
            s = float(row[best_j])
            if s < MODIFIED_THRESHOLD or cb.category != ca.category:
                material, rationale = _materiality(s, ca.text, cb.text, ca.category)
                changes.append(
                    Change(
                        kind="modified",
                        category=ca.category if ca.category == cb.category else f"{ca.category} → {cb.category}",
                        text_a=ca.text[:2500],
                        text_b=cb.text[:2500],
                        similarity=round(s, 3),
                        material=material,
                        rationale=rationale,
                        clause_a_index=i,
                        clause_b_index=best_j,
                    )
                )
        else:
            changes.append(
                Change(
                    kind="removed",
                    category=ca.category,
                    text_a=ca.text[:2500],
                    text_b="",
                    similarity=0.0,
                    material=True,
                    rationale="Present in Contract A, absent in Contract B",
                    clause_a_index=i,
                    clause_b_index=None,
                )
            )

    for j, cb in enumerate(b_clauses):
        if j not in used_b:
            changes.append(
                Change(
                    kind="added",
                    category=cb.category,
                    text_a="",
                    text_b=cb.text[:2500],
                    similarity=0.0,
                    material=True,
                    rationale="New clause in Contract B",
                    clause_a_index=None,
                    clause_b_index=j,
                )
            )
    return changes


def summarize_changes(changes: list[Change], a_name: str, b_name: str) -> str:
    added = [c for c in changes if c.kind == "added"]
    removed = [c for c in changes if c.kind == "removed"]
    modified = [c for c in changes if c.kind == "modified"]
    material = [c for c in changes if c.material]
    lines = [
        f"Comparison of {a_name} (Contract A) vs {b_name} (Contract B):",
        f"{len(added)} added, {len(removed)} removed, {len(modified)} modified clauses "
        f"({len(material)} material).",
    ]
    if added:
        lines.append("Added: " + ", ".join(sorted({category_label(c.category.split(' → ')[0]) if c.kind=='modified' else category_label(c.category) for c in added})))
    if removed:
        lines.append("Removed: " + ", ".join(sorted({category_label(c.category) for c in removed})))
    if material:
        lines.append(
            "Material changes: "
            + ", ".join(
                f"{category_label(c.category)} ({c.rationale})" for c in material[:6]
            )
        )
    return "\n".join(lines)
