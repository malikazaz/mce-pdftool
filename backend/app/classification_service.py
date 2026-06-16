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

import os
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from . import classification_rules as rules
from . import ocr_service
from .config import get_settings

# Confidence at/above which an academic suggestion is considered solid (no auto-review flag).
SOLID_CONFIDENCE = 0.75

_SUBJECT_GRADE_RE = [re.compile(src, re.IGNORECASE) for src in rules.SUBJECT_GRADE_REGEXES]
_OTHER_DOCTYPE_RE = [re.compile(src, re.IGNORECASE) for src in rules.OTHER_DOCTYPE_REGEXES]


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
    """Classify a single page's text as academic/other.

    Bilingual: English and Bulgarian phrase lists are checked together, so the same function
    works on either side. Awarding bodies, subject codes and candidate numbers are
    language-invariant and fire on both English originals and Bulgarian translations.
    """
    t = _norm(text)

    title_hits = _hits(t, rules.ACADEMIC_TITLE_PHRASES + rules.BG_ACADEMIC_TITLES)
    body_hits = _hits(t, rules.AWARDING_BODIES)
    award_hits = _hits(t, rules.AWARD_LANGUAGE + rules.BG_AWARD_LANGUAGE)
    grade_hits = [r.pattern[:24] + "…" for r in _SUBJECT_GRADE_RE if r.search(t)]
    letter_hits = _hits(t, rules.LETTER_SIGNALS + rules.BG_LETTER_SIGNALS)
    legal_hits = _hits(t, rules.LEGALISATION_SIGNALS + rules.BG_LEGALISATION_LEXICON)
    doctype_hits = _hits(t, rules.OTHER_DOCUMENT_TYPES + rules.BG_OTHER_DOCTYPES) + [
        "passport-mrz" for r in _OTHER_DOCTYPE_RE if r.search(t)
    ]

    academic_strong = (
        bool(title_hits)
        or (bool(body_hits) and (bool(grade_hits) or bool(award_hits)))
        or bool(award_hits)
        or len(grade_hits) >= 2
    )

    def sig(prefix: str, items: list[str]) -> list[str]:
        return [f"{prefix}:{i}" for i in items]

    # §6 step 1 — the page IS a non-academic document type (POA, passport, apostille,
    # affidavit…). Decisive, ahead of academic signals, so an incidental "diploma" mention
    # inside a Power of Attorney cannot flip it to academic.
    if doctype_hits:
        return PageVerdict("other", 0.9, True, sig("doctype", doctype_hits))

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
    # Tier-1: a Bulgarian POA/passport/apostille is non-academic even if it mentions
    # "диплома"/"образование" in the body.
    if any(term in t for term in rules.BG_OTHER_DOCTYPES):
        return False
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


def _verdict_needs_review(v: PageVerdict) -> bool:
    return (not v.decisive) or (v.label == "academic" and v.confidence < SOLID_CONFIDENCE)


def classify_project(
    original_path: str,
    translated_path: str,
    original_count: int,
    translated_count: int,
) -> list[PageSuggestion]:
    """Classify each side's document pages directly; use the English↔Bulgarian positional
    mirror only as a cross-check that flags disagreements for human review.

    Classifying the Bulgarian pages on their own merits (Bulgarian titles + language-invariant
    awarding bodies / subject codes / grades) avoids relying on the two PDFs staying
    positionally aligned — which they don't when a translation expands pages or a document is
    not translated (e.g. a passport).
    """
    orig_region = _doc_region("original", original_count)
    trans_region = _doc_region("translated", translated_count)

    # OCR is the dominant cost and each page is independent. pytesseract shells out to the
    # Tesseract binary (separate process per call), and ocr_service opens its own PDF handle
    # per page, so the work parallelises cleanly across threads — near-linear speedup with
    # cores on a multi-page set. Worker count is configurable (MCE_OCR_WORKERS); 0 = auto.
    tasks: list[tuple[str, int, str, str]] = (
        [("original", p, original_path, "eng") for p in orig_region]
        + [("translated", p, translated_path, "bul+eng") for p in trans_region]
    )

    def _verdict_for(path: str, page: int, lang: str) -> PageVerdict:
        return classify_text(ocr_service.extract_page_text(path, page, lang))

    results: dict[tuple[str, int], PageVerdict] = {}
    if tasks:
        configured = get_settings().ocr_workers
        workers = configured if configured > 0 else min(8, (os.cpu_count() or 2))
        workers = max(1, min(workers, len(tasks)))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(_verdict_for, path, page, lang): (kind, page)
                for (kind, page, path, lang) in tasks
            }
            for future, (kind, page) in futures.items():
                results[(kind, page)] = future.result()

    orig_verdicts: dict[int, PageVerdict] = {p: results[("original", p)] for p in orig_region}
    trans_verdicts: dict[int, PageVerdict] = {
        p: results[("translated", p)] for p in trans_region
    }

    suggestions: list[PageSuggestion] = []

    # English / original side.
    for p in orig_region:
        v = orig_verdicts[p]
        suggestions.append(
            PageSuggestion(
                "original", p, v.label, v.confidence, _verdict_needs_review(v), v.signals
            )
        )

    # Bulgarian / translated side — direct classification, mirror as a sanity cross-check.
    aligned = len(orig_region) == len(trans_region)
    for i, p in enumerate(trans_region):
        v = trans_verdicts[p]
        review = _verdict_needs_review(v)
        signals = list(v.signals)

        if not aligned:
            # Page counts differ -> we can't trust positional comparison; ask for a look.
            review = True
            signals.append("structure:unaligned-with-english")
        elif i < len(orig_region):
            english_label = orig_verdicts[orig_region[i]].label
            if english_label != v.label:
                review = True
                signals.append(f"disagrees-with-english:{english_label}")

        suggestions.append(
            PageSuggestion("translated", p, v.label, v.confidence, review, signals)
        )

    return suggestions
