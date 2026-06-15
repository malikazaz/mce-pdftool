# MedConnect Europe — PDF Assembly Tool

A web tool that takes a legalised document set (an **original/English PDF** and its
**translated PDF**) and produces two university-ready PDFs — a **Diploma** document
(academic items) and a **Continuation** document (everything else) — each prefixed with the
legalisation pages (solicitor, apostille) and the translator's notary stamp, in a fixed
order, exported as a ZIP.

It is **deterministic and manual**: a staff member labels every page by hand. There is **no
AI, OCR, machine learning, or external/cloud document processing**. Uploaded files live only
in a temporary per-project folder on the server, are never logged, never sent anywhere, and
are deleteable on demand plus auto-cleaned after a configurable age — suitable for sensitive
student documents.

## How the output is assembled

For each output (bucket = *academic* for Diploma, *other* for Continuation), pages are
written in this exact order:

```
1. Translated solicitor certificate     (translated PDF)
2. Translated apostille                  (translated PDF)
3. Translated bucket documents, in order (translated PDF)
4. Notary stamp                          (translated PDF — translated-only)
5. English solicitor certificate         (original PDF)
6. English apostille                     (original PDF)
7. English bucket documents, in order    (original PDF)
```

The whole translated section comes first (ending with the notary), then the whole English
section. The notary belongs to the translator, so it appears only in the translated section.

Because the translated PDF usually has an extra notary page, page numbers do **not** line up
1:1 between the two PDFs — so you label pages independently in each grid, and the tool
collects pages by role + bucket in each PDF's natural reading order.

## Project layout

```
mce-pdftool/
  backend/    FastAPI + pypdf + PyMuPDF + SQLite
  frontend/   React + TypeScript + Vite + PDF.js
```

## Running locally

### Backend

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate     macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API is served at `http://127.0.0.1:8000` (interactive docs at `/docs`).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies `/api` to the backend, so no
extra configuration is needed.

### Tests

```bash
cd backend
pytest
```

The suite generates sample PDFs (with identifiable pages) and asserts the exact page order,
counts, validation (non-PDF / out-of-range / sanitised filenames), and the full
upload→generate→download API flow.

## Workflow

1. **Upload** the original and translated PDFs (drag & drop). Page counts are shown; a
   non-blocking warning appears if the counts differ (normal when a notary page is present).
2. **Review** the page labels. Legal pages are auto-set (solicitor p1, apostille p2,
   translated notary = last page) and document pages are **auto-suggested** as *academic* or
   *other* (see below). Suggested pages show an "auto" tag; pages the tool is unsure about
   show a "review" tag with an amber highlight. Change any label via its dropdown; click a
   thumbnail to zoom.
3. **Generate**: enter the client's full name (and optionally rename the Diploma /
   Continuation labels), review the live page-order preview for both outputs, then generate.
4. **Download** the ZIP, then **Clear project** to delete all temporary files.

## Automatic academic-document recognition

After both PDFs are uploaded, the tool suggests which document pages are **academic**
(degree/diploma certificates, statements of results, transcripts, mark sheets…) versus
**other** (letters, identity/legal/admin pages). This is **always a suggestion the staff
member confirms** — never a final decision.

How it works (no AI, no external APIs — fully offline, GDPR-friendly for student data):

- **Local OCR** extracts page text — the PDF's embedded text layer first, then **Tesseract**
  for scanned pages. Extracted text is used in memory only and is **never logged or stored**.
- A **deterministic rules engine** (`backend/app/classification_service.py`, driven by the
  editable ruleset in `backend/app/classification_rules.py`) classifies the **English**
  pages. The rules are a direct encoding of the internal recognition guidance
  (`RECOGNISING-ACADEMIC-DOCUMENTS.md`, kept out of this repo); every `academic` verdict
  records the signals behind it for auditability.
- The **Bulgarian (translated) side is mirrored by document position** from the English
  result (the translator preserves order), then **cross-checked offline** with Tesseract's
  Bulgarian model + a bilingual lexicon. Pages where the mirror drifts or the cross-check
  disagrees are flagged "review". No machine translation, no API.
- **Graceful degradation:** if Tesseract is not installed, the tool reports that
  auto-labelling is unavailable and manual labelling works exactly as before.

> The ruleset and the Bulgarian lexicon (`BG_ACADEMIC_LEXICON`) are starter sets distilled
> from the recognition guide. Tune the English phrase lists as new document types appear, and
> have a **native Bulgarian speaker review the lexicon** for production use.

### Installing Tesseract (required for auto-recognition)

- **Windows:** install the UB Mannheim build (`winget install UB-Mannheim.TesseractOCR`) or
  from <https://github.com/UB-Mannheim/tesseract/wiki>, and add the **Bulgarian** language
  pack during setup (English is included). If it isn't on `PATH`, set `MCE_TESSERACT_CMD`
  (see config table) to e.g. `C:/Program Files/Tesseract-OCR/tesseract.exe`.
- **Debian/Ubuntu:** `sudo apt install tesseract-ocr tesseract-ocr-bul`.
- **macOS:** `brew install tesseract tesseract-lang`.

## Configuration

Settings are environment-overridable with the `MCE_` prefix (see `backend/app/config.py`):

| Variable | Default | Meaning |
|---|---|---|
| `MCE_DATA_DIR` | `backend/data` | Where the SQLite db and project folders live |
| `MCE_MAX_UPLOAD_MB` | `50` | Per-file upload size cap |
| `MCE_CLEANUP_AGE_HOURS` | `24` | Projects older than this are auto-deleted |
| `MCE_CLEANUP_INTERVAL_MINUTES` | `60` | How often the cleanup task runs |
| `MCE_THUMBNAIL_WIDTH` | `240` | Thumbnail render width (px) |
| `MCE_TESSERACT_CMD` | _(empty)_ | Explicit path to the Tesseract binary (else use `PATH`) |
| `MCE_OCR_DPI` | `200` | Render DPI when OCR'ing a scanned page |
| `MCE_OCR_TEXT_THRESHOLD` | `20` | Below this many embedded chars, a page is OCR'd |
| `MCE_ALLOWED_ORIGINS` | localhost:5173 | CORS origins (JSON list) |

## Privacy & security

- No AI / ML / external document APIs. The only text extraction is **local OCR** (Tesseract)
  for the auto-recognition feature; it runs on this server and its output is used in memory
  only. All processing is local and deterministic.
- Files stored only under the per-project temp folder; removed via the `DELETE` endpoint and
  by the background cleanup task.
- Logging is restricted to method/path/status — no filenames, project ids, or document
  text (including OCR output) are ever logged.
- All user-supplied paths/filenames pass through `safe_join` + `sanitise_filename`
  (path-traversal guard, forced `.pdf`).
- Upload size is capped before the full file is read.

## Integrating into the MedConnect portal

Search the backend for `PORTAL-AUTH:` markers. The recommended integration points:

- Protect the project router with the portal's auth dependency
  (`backend/app/routes/projects.py`) and scope projects to the authenticated user.
- Mount the FastAPI app behind the portal and tighten `MCE_ALLOWED_ORIGINS`.

Authentication is intentionally **not** built into the MVP.

## Possible future extensions (not built)

- **University templates** — predefine which buckets/outputs a given university requires so a
  user maps pages once and generates everything needed.
- **Server-side persistence of page labels** (a `labels` table) so a project can be resumed
  after a browser refresh — currently labels live in frontend state and travel in the
  generate payload.
- Optional translated-only or extra legal pages if a university's requirements change.
