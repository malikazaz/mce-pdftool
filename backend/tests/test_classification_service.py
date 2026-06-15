"""Tests for the deterministic classifier and project orchestration.

The ``classify_text`` cases mirror the worked-example table in
RECOGNISING-ACADEMIC-DOCUMENTS.md §8 — especially the confusable pairs (CLAUDE.md §5), which
are where accuracy is won or lost. These need no OCR (pure text in).
"""

from __future__ import annotations

from app import classification_service as cs
from app.classification_service import classify_text

from .conftest import make_text_pdf


# --- classify_text: the guide's worked examples (§8) ---

def test_statement_of_results_is_academic():
    text = (
        "Statement of Provisional Results. Cambridge Assessment International Education. "
        "Candidate Number 012345. Biology: A Chemistry: B Mathematics: A*"
    )
    v = classify_text(text)
    assert v.label == "academic" and v.decisive


def test_certificate_of_achievement_is_academic():
    v = classify_text(
        "GCE Advanced Level Certificate of Achievement. This is to certify that the "
        "candidate has been awarded the following grades."
    )
    assert v.label == "academic"


def test_cbse_mark_sheet_is_academic():
    v = classify_text("CBSE Class XII Mark Sheet. Central Board of Secondary Education.")
    assert v.label == "academic"


def test_degree_certificate_is_academic():
    v = classify_text(
        "This is to certify that John Smith has been awarded the degree of Bachelor of Science."
    )
    assert v.label == "academic"


def test_school_grade_letter_is_other_even_with_grades():
    # The key confusable case (§5.3): a letter that *confirms* grades is OTHER.
    text = (
        "To whom it may concern. I am writing to confirm that the student achieved "
        "Biology A and Chemistry B. Yours sincerely, Head Teacher."
    )
    v = classify_text(text)
    assert v.label == "other" and v.decisive


def test_eligibility_letter_is_other():
    v = classify_text(
        "Dear Sir/Madam, this letter confirms the student is eligible to apply. "
        "Yours faithfully."
    )
    assert v.label == "other"


def test_power_of_attorney_is_other_despite_diploma_mention():
    # Real-world regression: a POA that mentions "high school diploma" must stay OTHER.
    text = (
        "POWER OF ATTORNEY. APPOINTS the following persons. Represent the Student before "
        "the Ministry of Education in Bulgaria with regards to obtaining a certificate of "
        "equivalence of high school diploma and any other documents required for admission."
    )
    v = classify_text(text)
    assert v.label == "other" and v.decisive


def test_passport_is_other():
    v = classify_text(
        "PASSPORT PASSEPORT UNITED KINGDOM OF GREAT BRITAIN P<GBRHUSSAIN<<HAROON"
    )
    assert v.label == "other" and v.decisive


def test_apostille_page_is_other():
    v = classify_text("APOSTILLE. Convention de la Haye du 5 octobre 1961.")
    assert v.label == "other" and v.decisive


def test_notary_true_copy_is_other():
    v = classify_text("I certify this to be a true copy of the original. Notary Public.")
    assert v.label == "other"


def test_unknown_page_defaults_to_other_and_flags_review():
    v = classify_text("Some random text with no meaningful signals at all.")
    assert v.label == "other" and not v.decisive


def test_certified_translation_of_certificate_stays_academic():
    # §3.4 — academic title wins even when a translator stamp is present on the page.
    v = classify_text(
        "Diploma. Bachelor of Arts. I certify that this is a true and accurate translation."
    )
    assert v.label == "academic"


# --- Direct Bulgarian classification (translated side) ---

def test_bg_certificate_is_academic_directly():
    # A Bulgarian GCE translation: Bulgarian title + Latin awarding body + subject code/grade.
    text = (
        "AQA Общ сертификат за образование. ALTRINCHAM GRAMMAR SCHOOL FOR BOYS. "
        "БИОЛОГИЯ (601/4625/4) Оценка B (b)"
    )
    v = classify_text(text)
    assert v.label == "academic" and v.decisive


def test_bg_school_letter_is_other_directly():
    text = (
        "До всички заинтересовани. Уважаеми господине/госпожо, пиша Ви, за да потвърдя. "
        "С уважение, Директор."
    )
    v = classify_text(text)
    assert v.label == "other" and v.decisive


def test_bg_power_of_attorney_is_other_directly():
    v = classify_text(
        "ПЪЛНОМОЩНО НАЗНАЧАВА удостоверение за приравняване на дипломата за средно образование"
    )
    assert v.label == "other" and v.decisive


# --- Bulgarian cross-check ---

def test_bg_crosscheck_detects_academic():
    assert cs.bg_crosscheck("Диплома за висше образование, академична справка") is True


def test_bg_crosscheck_detects_non_academic():
    assert cs.bg_crosscheck("Пълномощно и нотариус") is False


def test_bg_crosscheck_poa_with_diploma_words_is_non_academic():
    # BG POA mentions диплома/образование but is a пълномощно -> must be non-academic.
    text = (
        "ПЪЛНОМОЩНО НАЗНАЧАВА удостоверение за приравняване на дипломата за средно "
        "образование"
    )
    assert cs.bg_crosscheck(text) is False


def test_bg_crosscheck_inconclusive_on_empty():
    assert cs.bg_crosscheck("") is None


# --- classify_project: regions, mirror, exclusions (embedded text -> no OCR needed) ---

def _build_pair(tmp_path):
    original = tmp_path / "original.pdf"
    translated = tmp_path / "translated.pdf"
    make_text_pdf(
        original,
        [
            "Solicitor certification page.",  # p1 legal (excluded)
            "Apostille certificate.",          # p2 legal (excluded)
            "Statement of Results. Cambridge Assessment. Candidate Number 1. "
            "Biology: A Chemistry: B",        # p3 academic
            "Degree Certificate. This is to certify that the candidate has been awarded "
            "the degree of Bachelor of Science.",  # p4 academic
            "To whom it may concern. I confirm eligibility. Yours sincerely.",  # p5 other
        ],
    )
    make_text_pdf(
        translated,
        [
            "Заверен превод на solicitor.",     # p1 legal (excluded)
            "Апостил.",                          # p2 legal (excluded)
            "Диплома, академична справка, оценки",  # p3 academic
            "Диплома, бакавалавър",              # p4 academic
            "Пълномощно.",                       # p5 other
            "Нотариус. Апостил.",                # p6 notary (excluded)
        ],
    )
    return original, translated


def test_classify_project_mirror_and_regions(tmp_path):
    original, translated = _build_pair(tmp_path)
    out = cs.classify_project(str(original), str(translated), 5, 6)

    by_key = {(s.kind, s.page): s for s in out}
    # Legal pages never appear.
    assert ("original", 1) not in by_key and ("original", 2) not in by_key
    assert ("translated", 1) not in by_key and ("translated", 6) not in by_key  # notary

    # English classification.
    assert by_key[("original", 3)].suggested_role == "academic"
    assert by_key[("original", 4)].suggested_role == "academic"
    assert by_key[("original", 5)].suggested_role == "other"

    # Translated mirrors English by position.
    assert by_key[("translated", 3)].suggested_role == "academic"
    assert by_key[("translated", 4)].suggested_role == "academic"
    assert by_key[("translated", 5)].suggested_role == "other"


def test_classify_project_flags_drift(tmp_path):
    # Original doc region = 1 page; translated doc region = 2 pages -> drift -> review.
    original = tmp_path / "o.pdf"
    translated = tmp_path / "t.pdf"
    make_text_pdf(original, ["sol", "apo", "Statement of Results. Cambridge. Grade A"])
    make_text_pdf(translated, ["sol", "apo", "Диплома", "Диплома", "Нотариус"])
    out = cs.classify_project(str(original), str(translated), 3, 5)
    translated_pages = [s for s in out if s.kind == "translated"]
    assert translated_pages and all(s.needs_review for s in translated_pages)
