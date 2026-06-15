"""Deterministic academic-page classifier + project-level orchestration.

Implements the decision procedure of
pdf-page-classifier-handover/RECOGNISING-ACADEMIC-DOCUMENTS.md §6, using the phrase lists in
``classification_rules.py``. Pure logic: callers supply page text (from ``ocr_service``).

Design choices that follow the guide:
- A page that *calls itself* a results/certificate document is academic, even if it also
  shows letter-like or legalisation text (§5.3, §3.4).
- A letter that merely *discusses* grades is ``other`` (§4, §6 step 2).
- Pure legalisation/identity/admin pages are ``other`` (§6 step 1).
- When nothing decisive fires, default to ``other`` (§6 step 5) and flag for human review.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import classification_rules as rules
from . import ocr_service

# Confidence at/above which an academic suggestion is considered solid (no auto-review flag).
SOLID_CONFIDENCE = 0.75

_SUBJECT_GRADE_RE = [re.compile(src, re.IGNORECASE) for src in rules.SUBJECT_GRADE_REGEXES]


def _norm(text: str) -> str:
    """Lower-case, collapse whitespace, pad with spaces (so ' ocr ' style tokens match)."""
    return " " + re.sub(r"\s+", " ", text.lower()).strip() + " "


def _hits(text: str, phrases: list[str]) -> list[str]:
    return [p.strip() for p in phrases if p in text]


@dataclass
class PageVerdict:
    label: str  # "academic" | "other"
    confidence: float
    decisive: bool  # True when a strong rule fired; False = fell through to default-other
    signals: list[str] = field(default_factory=list)


def classify_text(text: str) -> PageVerdict:
    """Classify a single page's text as academic/other (English/Latin script)."""
    t = _norm(text)

    title_hits = _hits(t, rules.ACADEMIC_TITLE_PHRASES)
    body_hits = _hits(t, rules.AWARDING_BODIES)
    award_hits = _hits(t, rules.AWARD_LANGUAGE)
    grade_hits = [r.pattern[:24] + "…" for r in _SUBJECT_GRADE_RE if r.search(t)]
    letter_hits = _hits(t, rules.LETTER_SIGNALS)
    legal_hits = _hits(t, rules.LEGALISATION_SIGNALS)

    academic_strong = (
        bool(title_hits)
        or (bool(body_hits) and (bool(grade_hits) or bool(award_hits)))
        or bool(award_hits)
        or len(grade_hits) >= 2
    )

    def sig(prefix: str, items: list[str]) -> list[str]:
        return [f"{prefix}:{i}" for i in items]

    # §6 step 2 — a letter (no self-title) is other even if it shows grades.
    if letter_hits and not title_hits:
        return PageVerdict(
            "other", 0.85, True,
            sig("letter", letter_hits) + sig("grade", grade_hits),
        )

    # §6 step 1 — pure legalisation/identity page (no strong academic signal) is other.
    if legal_hits and not academic_strong:
        return PageVerdict("other", 0.85, True, sig("legalisation", legal_hits))

    # §6 step 3 — strong academic signals.
    if academic_strong:
        if title_hits:
            conf = 0.9
        elif body_hits and (grade_hits or award_hits):
            conf = 0.85
        elif award_hits:
            conf = 0.78
        else:  # grade structure alone (>=2)
            conf = 0.75
        signals = (
            sig("title", title_hits)
            + sig("body", body_hits)
            + sig("award", award_hits)
            + sig("grade", grade_hits)
        )
        return PageVerdict("academic", conf, True, signals)

    # §6 step 5 — default to other, flag for review.
    return PageVerdict("other", 0.55, False, [])


def bg_crosscheck(text: str) -> bool | None:
    """Offline Bulgarian verification of the translated side.

    Returns True (looks academic), False (looks non-academic), or None (no usable text /
    inconclusive). Used only to verify the mirrored label, never as the primary decision.
    """
    if len(text.strip()) < 3:
        return None
    t = _norm(text)
    academic = any(term in t for term in rules.BG_ACADEMIC_LEXICON)
    legal = any(term in t for term in rules.BG_LEGALISATION_LEXICON)
    if academic and not legal:
        return True
    if legal and not academic:
        return False
    return None  # mixed or neither -> inconclusive, don't flag


# --- Project-level orchestration -------------------------------------------------


@dataclass
class PageSuggestion:
    kind: str  # "original" | "translated"
    page: int  # 1-based
    suggested_role: str  # "academic" | "other"
    confidence: float
    needs_review: bool
    signals: list[str] = field(default_factory=list)


def _doc_region(kind: str, page_count: int) -> list[int]:
    """Document pages = everything except the fixed legal pages.

    original: exclude solicitor(1), apostille(2).
    translated: exclude solicitor(1), apostille(2), notary(last).
    """
    if kind == "original":
        return [p for p in range(3, page_count + 1)]
    return [p for p in range(3, page_count)]  # drop the last (notary) page too


def classify_project(
    original_path: str,
    translated_path: str,
    original_count: int,
    translated_count: int,
) -> list[PageSuggestion]:
    """Classify English doc pages, mirror onto the translated side, cross-check in Bulgarian."""
    orig_region = _doc_region("original", original_count)
    trans_region = _doc_region("translated", translated_count)

    # 1. Classify the English/original document pages directly.
    orig_verdicts: dict[int, PageVerdict] = {
        p: classify_text(ocr_service.extract_page_text(original_path, p, "eng"))
        for p in orig_region
    }

    suggestions: list[PageSuggestion] = []
    for p in orig_region:
        v = orig_verdicts[p]
        needs_review = (not v.decisive) or (
            v.label == "academic" and v.confidence < SOLID_CONFIDENCE
        )
        suggestions.append(
            PageSuggestion("original", p, v.label, v.confidence, needs_review, v.signals)
        )

    # 2. Mirror onto the translated side by document position.
    aligned = len(orig_region) == len(trans_region)
    for i, p in enumerate(trans_region):
        if i < len(orig_region):
            mirrored = orig_verdicts[orig_region[i]]
            label = mirrored.label
            confidence = mirrored.confidence
            signals = [f"mirrored:{s}" for s in mirrored.signals]
            review = (not aligned) or (not mirrored.decisive)
        else:
            # Drift: more translated doc pages than English ones.
            label, confidence, signals, review = "other", 0.4, [], True

        # 3. Offline Bulgarian cross-check.
        cc = bg_crosscheck(ocr_service.extract_page_text(translated_path, p, "bul"))
        if cc is True:
            signals.append("bg:academic")
            if label != "academic":
                review = True  # Bulgarian looks academic but mirror said other
        elif cc is False:
            signals.append("bg:non-academic")
            if label == "academic":
                review = True  # Bulgarian looks non-academic but mirror said academic

        suggestions.append(
            PageSuggestion("translated", p, label, confidence, review, signals)
        )

    return suggestions
