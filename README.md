# MedConnect Europe — PDF Assembly Tool

A web tool that takes a legalised document set (an **original/English PDF** and its
**translated PDF**) and produces two university-ready PDFs — a **Diploma** document
(academic items) and a **Continuation** document (everything else) — each prefixed with the
legalisation pages (solicitor, apostille) and the translator's notary stamp, in a fixed
order, exported as a ZIP.

It is **deterministic**: pages are auto-suggested as academic/other by a rules engine (with
local OCR), and a staff member confirms every label. There is **no AI, machine learning, or
external/cloud document processing** — the only text extraction is local OCR (Tesseract) that
runs on this server. Uploaded files live only in a temporary per-project folder, are never
logged, never sent anywhere, and are deleteable on demand plus auto-cleaned after a
configurable age — suitable for sensitive student documents.

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

## Running locally (Windows, step by step)

You run TWO programs at the same time, each in its **own terminal window**:
**Terminal 1 = backend**, **Terminal 2 = frontend**. Keep both open while using the tool.

Commands below are PowerShell. Do the steps in order, top to bottom.

### Part A — Install the prerequisites (one time only)

1. **Python 3.12+** — check with `python --version`. If missing: https://www.python.org/downloads/
2. **Node.js 20+** — check with `node --version`. If missing: https://nodejs.org/
3. **Tesseract OCR** (needed for the auto-recognition feature):
   - Download and run the installer: https://github.com/UB-Mannheim/tesseract/wiki
   - On the **"Additional language data"** screen, tick **Bulgarian** (English is always included).
   - It installs to `C:\Program Files\Tesseract-OCR\`.
4. **Close every terminal window** and open a fresh one (so it sees the newly installed tools).
   Verify: `tesseract --version` prints a version number.
   - If it says *"not found"*, that's fine — you'll handle it in Terminal 1, step 3 below.

### Part B — First-time project setup (one time only)

In **Terminal 1**:

```powershell
cd "c:\Users\ahmed azaz\mce-pdftool\backend"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

In **Terminal 2**:

```powershell
cd "c:\Users\ahmed azaz\mce-pdftool\frontend"
npm install
```

### Part C — Start the app (every time you want to run it)

**Terminal 1 — backend.** Run these four lines in this window, in order:

```powershell
cd "c:\Users\ahmed azaz\mce-pdftool\backend"
.venv\Scripts\activate
$env:MCE_TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"
uvicorn app.main:app --reload --port 8000
```

> The 3rd line tells the app where Tesseract is. You only need it if `tesseract --version`
> failed in Part A step 4. If it worked, you can skip that line. Leave this window running.

**Terminal 2 — frontend.** Open a SECOND window and run:

```powershell
cd "c:\Users\ahmed azaz\mce-pdftool\frontend"
npm run dev
```

Leave this window running too.

### Part D — Open it

Open **http://localhost:5173** in your browser. The frontend talks to the backend
automatically. To stop the app, press `Ctrl+C` in each terminal.

> **Not on Windows?** Backend activate: `source .venv/bin/activate`. Install Tesseract with
> `sudo apt install tesseract-ocr tesseract-ocr-bul` (Linux) or
> `brew install tesseract tesseract-lang` (macOS); it's normally on `PATH`, so the
> `MCE_TESSERACT_CMD` line isn't needed.

## Deploying to Render (single Docker web service)

The repo ships a `Dockerfile` and `render.yaml` that build **one** service: FastAPI serves
the `/api` **and** the built React frontend from the same origin (the SPA uses relative
`/api` paths, so there's no CORS or API-base config). The image installs **Tesseract +
English/Bulgarian** language packs, which a plain Python runtime can't.

**Steps:**
1. Push to GitHub (already done for this repo).
2. In Render: **New + → Blueprint**, select this repo. Render reads `render.yaml` and creates
   a free Docker web service. (Or **New + → Web Service**, pick the repo, choose **Docker** and
   the **Free** plan — Render auto-detects the `Dockerfile`.)
3. Deploy. The build takes a few minutes (it compiles the frontend and installs Tesseract).
   When live you get a public `https://<name>.onrender.com` URL.

**Free-tier notes:**
- The service **spins down after ~15 min idle**; the next request cold-starts in ~30–60s.
- The disk is **ephemeral** — uploads/SQLite are wiped on each deploy/restart. Fine here: the
  flow is upload → generate → download → clear, and projects auto-clean anyway.
- 512 MB RAM. If OCR OOMs on large scans, set `MCE_OCR_DPI=200` (env var in the dashboard).
- **No authentication** and a **public URL** — for student PII, demo with dummy/redacted
  documents, or put the service behind an auth gate before sharing widely.

Run the image locally the same way Render does:

```powershell
docker build -t mce-pdftool .
docker run -p 8000:8000 mce-pdftool   # open http://localhost:8000
```

## Running the tests

In **Terminal 1** (with the venv activated):

```powershell
cd "c:\Users\ahmed azaz\mce-pdftool\backend"
.venv\Scripts\activate
pytest
```

The suite asserts the exact page order/counts, validation (non-PDF / out-of-range /
sanitised filenames), the full upload→generate→download API flow, and the academic-page
classifier (using the recognition guide's worked examples). It runs without Tesseract.

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

The academic lexicon is **international**, not just UK: alongside GCSE/IGCSE/GCE A-Level it
recognises secondary-school equivalents and exam boards from South Asia (Matriculation,
Intermediate, CBSE/ICSE, BISE/FBISE, Class X/XII mark sheets, divisions/CGPA),
Africa (WAEC/NECO/KNEC, National/Senior Senior School Certificate, Umalusi),
the Middle East (Tawjihi, Thanaweya Amma), and Europe/North America (Abitur, Baccalauréat,
Bachillerato, Maturità, High School Diploma/Transcript), plus tertiary qualifications
(Bachelor/Master/Doctorate, HND, foundation/associate/postgraduate diplomas). Civil-registry
certificates (birth/marriage/etc.) are explicitly kept out of "academic".

How it works (no AI, no external APIs — fully offline, GDPR-friendly for student data):

- **Local OCR** extracts page text — the PDF's embedded text layer first, then **Tesseract**
  for scanned pages. Extracted text is used in memory only and is **never logged or stored**.
- A **deterministic rules engine** (`backend/app/classification_service.py`, driven by the
  editable ruleset in `backend/app/classification_rules.py`) classifies the **English**
  pages. The rules are a direct encoding of the internal recognition guidance
  (`RECOGNISING-ACADEMIC-DOCUMENTS.md`, kept out of this repo); every `academic` verdict
  records the signals behind it for auditability.
- The **Bulgarian (translated) side is classified directly** by the same bilingual rules:
  Bulgarian titles/award-language plus the language-invariant signals the translations keep
  (awarding bodies like AQA/WJEC, subject codes such as `601/4625/4`, candidate numbers,
  grades). The English page in the same position is used only as a **cross-check** — where
  the two sides disagree, or the page counts don't line up (e.g. a translation that expands
  to two pages, or an untranslated passport), the page is flagged "review". No machine
  translation, no API.
- **Graceful degradation:** if Tesseract is not installed, the tool reports that
  auto-labelling is unavailable and manual labelling works exactly as before.

> The ruleset and the Bulgarian lexicon (`BG_ACADEMIC_LEXICON`) are starter sets distilled
> from the recognition guide. Tune the English phrase lists as new document types appear, and
> have a **native Bulgarian speaker review the lexicon** for production use.

(Tesseract installation is covered in "Running locally" → Part A.)

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
| `MCE_OCR_DPI` | `300` | Render DPI when OCR'ing a scanned page (higher = better on faint scans, slower) |
| `MCE_OCR_TEXT_THRESHOLD` | `20` | Below this many embedded chars, a page is OCR'd |
| `MCE_OCR_WORKERS` | `0` | Parallel OCR workers (0 = auto: min(8, CPU count)); lower on small hosts |
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
