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
    # Common qualification acronyms/short titles (language-invariant — they stay Latin on the
    # Bulgarian translations too). Padded with spaces so they only match as whole tokens.
    # NB: deliberately NOT "a level"/"a levels" — eligibility LETTERS say "completed his A
    # levels", and a letter must stay `other`.
    " gcse ",
    " igcse ",
    " gce ",
    "advanced level",
    "advanced subsidiary",
    " as level ",
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
    # --- International secondary-school equivalents (guide §3.2) ---
    # South Asia (India / Pakistan / Bangladesh / Sri Lanka / Nepal)
    "matriculation certificate",
    "matriculation examination",
    " matriculation ",
    "matric certificate",
    "intermediate certificate",
    "intermediate examination",
    "secondary school leaving certificate",
    "school leaving certificate",
    "all india senior school certificate",
    "higher secondary school certificate",
    "pre-university certificate",
    "pre university certificate",
    " o level ",
    " o-level ",
    "ordinary level",
    # Africa (Nigeria / Ghana / Kenya / South Africa …)
    "west african senior school certificate",
    "senior school certificate",
    "national senior school certificate",
    # Middle East / others
    "tawjihi",
    "thanaweya amma",
    "general secondary education certificate",
    # Europe / North America
    "abitur",
    "baccalaureate",
    "baccalaureat",
    "baccalauréat",
    "bachillerato",
    "diploma di maturita",
    "diploma di maturità",
    " matura ",
    "high school transcript",
    "high school certificate",
    "diploma supplement",
    # Scotland
    "scottish qualification certificate",
    "advanced higher",
    "national qualification",
    # --- Higher / tertiary (guide §3.3) ---
    "degree certificate",
    "bachelor of",
    "bachelor's degree",
    "bachelors degree",
    "master of",
    "master's degree",
    "masters degree",
    "doctor of philosophy",
    "doctor of",
    "doctorate",
    "doctoral degree",
    "associate of arts",
    "associate of science",
    "associate degree",
    "associate's degree",
    "foundation certificate",
    "foundation degree",
    "access to higher education",
    "postgraduate diploma",
    "postgraduate certificate",
    "advanced diploma",
    "national diploma",
    "higher national diploma",
    "higher national certificate",
    "international baccalaureate",
    # --- Results / transcript documents by name (guide §3.1, §3.3) ---
    "consolidated mark sheet",
    "consolidated marksheet",
    "detailed marks certificate",
    "marks memorandum",
    "memorandum of results",
    "memorandum of marks",
    "statement of marks",
    "statement of grades",
    "grade sheet",
    "grade card",
    "grade report",
    "report card",
    "examination certificate",
    "examination result",
    "provisional certificate",
    "cumulative record",
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
    "indian certificate of secondary education",
    "international baccalaureate",
    " ib ",
    # --- More international boards / awarding bodies (guide §5.1) ---
    # UK / Ireland
    "scottish qualifications authority",
    " sqa ",
    "state examinations commission",
    "oxford aqa",
    "cambridge igcse",
    "cambridge international examinations",
    "council for the curriculum",  # CCEA (NI)
    # India / Pakistan / Bangladesh / Sri Lanka / Nepal
    "national institute of open schooling",
    " nios ",
    "board of intermediate and secondary education",
    " bise ",
    "federal board of intermediate and secondary education",
    " fbise ",
    "board of secondary education",
    "national board of examinations",
    "national testing service",
    "department of examinations",
    # Africa
    "west african examinations council",
    "national examinations council",
    "kenya national examinations council",
    " knec ",
    "uganda national examinations board",
    " uneb ",
    "national examination council of tanzania",
    "umalusi",
    "independent examinations board",
    "department of basic education",
    # Middle East / Asia-Pacific
    "ministry of education and higher education",
    "hong kong examinations and assessment authority",
    " hkdse ",
    "ministry of education malaysia",
    # Generic institutional issuers
    "examination board",
    "board of education",
    "examinations council",
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
    # International conferral / pass phrasings (common on translated certificates).
    "is hereby conferred",
    "is conferred upon",
    "has been conferred",
    "has successfully completed",
    "has successfully passed",
    "has passed the examination",
    "qualified for the award",
    "has duly passed",
    "is declared to have passed",
    "having passed the examination",
    "has fulfilled the requirements",
    "has completed the requirements",
    "in recognition of the successful completion",
]

# Regex sources (compiled in the service). Subject–grade structure & candidate identifiers.
# Several are LANGUAGE-INVARIANT (subject codes, candidate numbers), so they fire on the
# Bulgarian translations too — which is what makes direct Bulgarian classification reliable.
SUBJECT_GRADE_REGEXES: list[str] = [
    # e.g. "Biology: A*", "Mathematics  A", "Chemistry - B"
    r"\b(biology|chemistry|physics|mathematics|maths|english|history|geography|"
    r"economics|business|psychology|sociology|computing|computer science|"
    r"further mathematics|literature|language)\b[^\n]{0,12}\b(a\*|[a-eu])\b",
    r"\bcandidate (number|no\.?)\b",
    r"\bcentre (number|no\.?)\b",
    r"\b(uci|uln)\b",
    # Letter grades (A*-E, U) and numeric GCSE grades (1-9), e.g. "GRADE 8 (eight)".
    r"\bgrade\b[^\n]{0,10}\b(a\*|[a-eu]|[1-9])\b",
    # Awarding-body subject code, e.g. "601/4625/4", "603/0859/X" — same in both languages.
    r"\b\d{3}/\d{4}/[0-9xх]\b",
    # International grading systems: GPA / CGPA, percentage of marks, division & class honours.
    r"\b(c?gpa|grade point average)\b",
    r"\b(first|second|third)\s+division\b",
    r"\b(first|second|upper second|lower second|third)\s+class\s+(honours|honors|division)\b",
    r"\b(marks? obtained|maximum marks|total marks|marks? secured|out of \d{2,4})\b",
    # Candidate/student identifiers common on international mark sheets & transcripts.
    r"\b(roll|seat|index|enrol{1,2}ment|registration|admission)\s*(no\.?|number)\b",
    # School-year levels used as the document subject (Class IX–XII, Grade 10–12).
    r"\bclass\s+(ix|x|xi|xii)\b",
    r"\bgrade\s*1[0-2]\b",
    # Bulgarian: "Оценка B (b)", "ОЦЕНКА 8 (осем)" and candidate/centre number labels.
    r"\bоценка\b",
    r"\b(номер на кандидата|№ на кандидата|номер на центъра|№ на центъра)\b",
    # Bulgarian: "среден успех" (GPA), "клас" level, "положи изпит".
    r"\bсреден успех\b",
    r"\b(10|11|12)\.?\s*клас\b",
]

# --- "Other" signals ---

# Letter structure (guide §5.2). A cluster of these marks a letter -> other.
LETTER_SIGNALS: list[str] = [
    "to whom it may concern",
    "to whomsoever it may concern",
    "dear sir",
    "dear madam",
    "dear sir/madam",
    "respected sir",
    "respected madam",
    "yours sincerely",
    "yours faithfully",
    "yours truly",
    "kind regards",
    "best regards",
    "i am writing to confirm",
    "i can confirm that",
    "this letter confirms",
    "this is to confirm that",
    "please accept this letter",
    "with reference to your",
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
    # Civil-registry / identity documents that carry the word "certificate" or are ID pages
    # but are NEVER academic — listed here so they can't be misread as a qualification.
    "birth certificate",
    "marriage certificate",
    "death certificate",
    "divorce certificate",
    "police clearance",
    "driving licence",
    "driver's license",
    "residence permit",
    "national insurance",
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

# --- Bulgarian classification phrases (the translated documents are in Bulgarian) ---
# These let the Bulgarian side be classified DIRECTLY (not just mirrored). Combined with the
# language-invariant signals above (awarding bodies in Latin, subject codes, candidate
# numbers), they give the translated pages strong, self-contained signals.
# NOTE: starter set — should be reviewed by a native Bulgarian speaker (see README).

# Academic titles a Bulgarian translation may carry (guide §5.1 equivalents).
BG_ACADEMIC_TITLES: list[str] = [
    "диплома",                          # diploma (also matches "дипломата")
    "академична справка",               # academic transcript
    "свидетелство за",                  # certificate of …
    "общ сертификат",                   # General Certificate (of [Secondary] Education)
    "сертификат за образование",        # certificate of education
    "сертификат за средно образование",  # certificate of secondary education
    "атестат",                          # secondary-school leaving certificate
    # Broader Bulgarian academic vocabulary (translations of any source-country credential).
    "диплома за средно образование",    # secondary education diploma
    "диплома за висше образование",     # higher education diploma
    "диплома за завършено",             # diploma for completed (education)
    "матура",                           # matriculation / school-leaving exam
    "зрелостен изпит",                  # maturity (school-leaving) examination
    "свидетелство за основно образование",  # basic education certificate
    "свидетелство за зрелост",          # certificate of maturity
    "приложение към диплома",           # diploma supplement
    "уверение",                         # attestation/confirmation (academic)
    "академична справка за",            # academic transcript for
    "справка за успех",                 # statement of results
    "бакалавър",                        # bachelor
    "магистър",                         # master
    "квалификационна степен",           # qualification degree
]

# Award language (guide §5.1 equivalents).
BG_AWARD_LANGUAGE: list[str] = [
    "с настоящото се удостоверява",     # this is to certify
    "удостоверява се, че",              # it is certified that
    "постигна следния резултат",        # achieved the following result
    "постигна следните резултати",      # achieved the following results
    "постигна два резултата",           # achieved two results
    # Broader conferral / pass phrasings.
    "успешно завърши",                  # successfully completed
    "успешно положи",                   # successfully passed
    "издържа изпита",                   # passed the examination
    "положи зрелостен изпит",           # passed the maturity exam
    "завърши пълния курс",              # completed the full course
    "присъжда се",                      # is awarded / conferred
    "придобива квалификация",           # acquires the qualification
    "присъдена квалификация",           # awarded qualification
]

# Letter structure (guide §5.2 equivalents) — push to other.
BG_LETTER_SIGNALS: list[str] = [
    "до всички заинтересовани",         # to whom it may concern
    "до когото може да се отнася",      # to whom it may concern (variant)
    "уважаеми господине",               # dear sir
    "уважаема госпожо",                 # dear madam
    "уважаеми господине/госпожо",       # dear sir/madam
    "с уважение",                       # yours sincerely / faithfully
    "на вниманието на",                 # for the attention of
    "с настоящото потвърждаваме",       # we hereby confirm (letter)
    "потвърждаваме, че",                # we confirm that
]

# Academic lexicon used by the (secondary) cross-check helper.
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
