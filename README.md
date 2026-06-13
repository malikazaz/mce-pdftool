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
2. **Label** every page in each grid: *solicitor*, *apostille*, *notary* (translated only),
   *academic*, *other*, or leave *unassigned* to exclude it. Click a thumbnail to zoom.
3. **Generate**: enter the client's full name (and optionally rename the Diploma /
   Continuation labels), review the live page-order preview for both outputs, then generate.
4. **Download** the ZIP, then **Clear project** to delete all temporary files.

## Configuration

Settings are environment-overridable with the `MCE_` prefix (see `backend/app/config.py`):

| Variable | Default | Meaning |
|---|---|---|
| `MCE_DATA_DIR` | `backend/data` | Where the SQLite db and project folders live |
| `MCE_MAX_UPLOAD_MB` | `50` | Per-file upload size cap |
| `MCE_CLEANUP_AGE_HOURS` | `24` | Projects older than this are auto-deleted |
| `MCE_CLEANUP_INTERVAL_MINUTES` | `60` | How often the cleanup task runs |
| `MCE_THUMBNAIL_WIDTH` | `240` | Thumbnail render width (px) |
| `MCE_ALLOWED_ORIGINS` | localhost:5173 | CORS origins (JSON list) |

## Privacy & security

- No AI / OCR / ML / external document APIs. All processing is local and deterministic.
- Files stored only under the per-project temp folder; removed via the `DELETE` endpoint and
  by the background cleanup task.
- Logging is restricted to method/path/status — no filenames, project ids, or document
  text are ever logged.
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
