"""Editable ruleset for academic-page recognition.

This file is the in-code source of truth for *what* counts as academic. It is a direct
encoding of pdf-page-classifier-handover/RECOGNISING-ACADEMIC-DOCUMENTS.md — keep the two in
lockstep. Tune the phrase lists here without touching the engine logic in
``classification_service.py``.

All English phrases are matched case-insensitively against lower-cased page text.
"""

from __future__ import annotations

# --- Strong academic signals (guide §5.1) ---

# Titles a page may call itself. A self-title is the single strongest academic signal.
ACADEMIC_TITLE_PHRASES: list[str] = [
    "statement of results",
    "statement of provisional results",
    "provisional statement of results",
    "notification of performance",
    "results statement",
    "results slip",
    "certificate of achievement",
    "certificate of secondary education",
    "certificate of education",
    "general certificate",
    "transcript of records",
    "academic transcript",
    "transcript",
    "mark sheet",
    "marksheet",
    "record of achievement",
    "record of study",
    "academic record",
    "diploma",
    "high school diploma",
    "secondary school certificate",
    "senior secondary certificate",
    "higher secondary certificate",
    "national senior certificate",
    "senior certificate",
    "leaving certificate",
    "junior certificate",
    "degree certificate",
    "bachelor of",
    "master of",
    "international baccalaureate",
]

# Awarding bodies / exam boards (often appear with a seal or crest).
AWARDING_BODIES: list[str] = [
    "cambridge assessment",
    "cambridge international",
    "cambridge",
    "oxford cambridge and rsa",
    " ocr ",
    " aqa ",
    "pearson edexcel",
    "edexcel",
    "pearson",
    " wjec ",
    " ccea ",
    " waec ",
    "west african examinations",
    " neco ",
    " cbse ",
    "central board of secondary education",
    " icse ",
    "council for the indian school",
    "international baccalaureate",
    " ib ",
]

# Award language (guide §5.1).
AWARD_LANGUAGE: list[str] = [
    "has been awarded",
    "is awarded",
    "this is to certify that",
    "has satisfied the requirements",
    "having satisfied the examiners",
    "is hereby awarded",
    "awarded the qualification",
]

# Regex sources (compiled in the service). Subject–grade structure & candidate identifiers.
SUBJECT_GRADE_REGEXES: list[str] = [
    # e.g. "Biology: A*", "Mathematics  A", "Chemistry - B"
    r"\b(biology|chemistry|physics|mathematics|maths|english|history|geography|"
    r"economics|business|psychology|sociology|computing|computer science|"
    r"further mathematics|literature|language)\b[^\n]{0,12}\b(a\*|[a-eu])\b",
    r"\bcandidate (number|no\.?)\b",
    r"\bcentre (number|no\.?)\b",
    r"\b(uci|uln)\b",
    r"\bgrade\b[^\n]{0,10}\b(a\*|[a-eu])\b",
]

# --- "Other" signals ---

# Letter structure (guide §5.2). A cluster of these marks a letter -> other.
LETTER_SIGNALS: list[str] = [
    "to whom it may concern",
    "dear sir",
    "dear madam",
    "dear sir/madam",
    "yours sincerely",
    "yours faithfully",
    "kind regards",
    "i am writing to confirm",
    "i can confirm that",
    "this letter confirms",
    "please accept this letter",
]

# TIER 1 — document-type identity markers (guide §6 step 1). If a page IS one of these
# document types it is DECISIVELY `other`, even if it incidentally mentions a qualification
# (e.g. a Power of Attorney that talks about a "high school diploma"). These never appear on
# a genuine academic certificate, so they outrank academic signals.
OTHER_DOCUMENT_TYPES: list[str] = [
    "power of attorney",
    "passport",
    "passeport",
    "identity card",
    "national identity",
    "apostille",
    "convention de la haye",
    "hague convention",
    "affidavit",
    "statutory declaration",
    "deed poll",
    "tenancy agreement",
    "application form",
    "payment receipt",
]
# Passport machine-readable-zone prefix (e.g. "P<GBR..."), a reliable passport marker.
OTHER_DOCTYPE_REGEXES: list[str] = [r"\bp<[a-z]{3}"]

# TIER 2 — legalisation phrases that may co-occur ON an academic page (e.g. a translator's
# stamp on a certified translation, guide §3.4). These mark `other` only when there is no
# strong academic signal, so they don't override a real certificate.
LEGALISATION_SIGNALS: list[str] = [
    "i certify this to be a true copy",
    "certified to be a true copy",
    "true and accurate translation",
    "certify that this is a true",
    "notary public",
    "notarial",
    "commissioner for oaths",
    "embassy",
    "consular",
]

# --- Bulgarian cross-check lexicon (offline verification only, guide §3.4 / §6.4) ---
# Academic terms as they typically appear in Bulgarian certified translations. Awarding-body
# names and candidate numbers usually remain in Latin/numeric form, which also helps.
# NOTE: starter set — should be reviewed by a native Bulgarian speaker (see README).
BG_ACADEMIC_LEXICON: list[str] = [
    "диплома",          # diploma
    "свидетелство",     # certificate
    "удостоверение",    # certificate/attestation (academic context)
    "атестат",          # secondary-school leaving certificate
    "академична справка",  # academic transcript
    "справка за успех",    # statement of results
    "уверение",         # confirmation/attestation
    "оценк",            # grade/mark (stem: оценка/оценки)
    "успех",            # academic performance/result
    "квалификация",     # qualification
    "бакалавър",        # bachelor
    "магистър",         # master
]

# Bulgarian TIER-1 document-type markers — decisively non-academic in the cross-check, even
# when the page also contains academic-sounding words (e.g. a ПЪЛНОМОЩНО that mentions
# "диплома"/"образование"). Mirrors the English OTHER_DOCUMENT_TYPES.
BG_OTHER_DOCTYPES: list[str] = [
    "пълномощно",          # power of attorney
    "паспорт",             # passport
    "апостил",             # apostille
    "клетвена деклараци",  # affidavit / sworn declaration
]

# Bulgarian legalisation terms -> other (so a notary/apostille translation isn't misread).
BG_LEGALISATION_LEXICON: list[str] = [
    "нотариус",         # notary
    "заверен",          # certified
    "превод",           # translation (translator's certification page)
]
