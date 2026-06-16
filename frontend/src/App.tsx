import { useEffect, useRef, useState } from "react";
import { api } from "./api/client";
import UploadPanel from "./components/UploadPanel";
import PageGrid from "./components/PageGrid";
import PageZoomModal from "./components/PageZoomModal";
import GeneratePanel from "./components/GeneratePanel";
import { ROLE_META, ROLE_ORDER } from "./roles";
import { defaultRolesFor } from "./payload";
import type { Classification, Kind, Role, SuggestionMeta } from "./types/pdf";

const emptyClassification = (): Classification => ({ original: {}, translated: {} });
const emptyMeta = (): SuggestionMeta => ({ original: {}, translated: {} });

type ClassifyState = "idle" | "running" | "done" | "unavailable";

export default function App() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [pageCounts, setPageCounts] = useState<{ original: number | null; translated: number | null }>({
    original: null,
    translated: null,
  });
  const [classification, setClassification] = useState<Classification>(emptyClassification());
  const [suggestionMeta, setSuggestionMeta] = useState<SuggestionMeta>(emptyMeta());
  const [classifyState, setClassifyState] = useState<ClassifyState>("idle");
  const [classifyNote, setClassifyNote] = useState<string | null>(null);
  const [classifyDone, setClassifyDone] = useState(false);
  const [previewPhase, setPreviewPhase] = useState<"idle" | "preparing" | "ready">("idle");
  const [thumbsLoaded, setThumbsLoaded] = useState(0);
  const [warning, setWarning] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [zoom, setZoom] = useState<{ kind: Kind; page: number } | null>(null);

  // TEMP DIAGNOSTIC (remove later): time the analysis (upload-complete → previews ready)
  // and the generate step.
  const analysisStartRef = useRef<number | null>(null);
  const [analysisMs, setAnalysisMs] = useState<number | null>(null);
  const [generateMs, setGenerateMs] = useState<number | null>(null);

  // Create a project on first load.
  useEffect(() => {
    api
      .createProject()
      .then((p) => setProjectId(p.project_id))
      .catch((e) => setError((e as Error).message));
  }, []);

  const handleUploaded = (kind: Kind, pageCount: number, warn: string | null) => {
    setPageCounts((c) => ({ ...c, [kind]: pageCount }));
    // Auto-label the predictable legal pages; user can still override them.
    setClassification((c) => ({ ...c, [kind]: defaultRolesFor(kind, pageCount) }));
    setWarning(warn);
    setError(null);
  };

  const ready = pageCounts.original !== null && pageCounts.translated !== null;

  // Once both PDFs are present, auto-suggest academic/other labels (local OCR + rules).
  // Re-runs if either file is replaced (page count changes).
  useEffect(() => {
    if (!projectId || pageCounts.original === null || pageCounts.translated === null) return;
    let cancelled = false;
    setClassifyState("running");
    setClassifyNote(null);
    setClassifyDone(false);
    api
      .classify(projectId)
      .then((res) => {
        if (cancelled) return;
        if (!res.ocr_available) {
          setClassifyState("unavailable");
          setClassifyNote(res.note);
          setClassifyDone(true);
          return;
        }
        // Merge suggestions over the legal-page defaults (suggestions never touch them).
        setClassification((c) => {
          const next: Classification = {
            original: { ...c.original },
            translated: { ...c.translated },
          };
          for (const s of res.suggestions) next[s.kind][s.page] = s.suggested_role;
          return next;
        });
        const meta = emptyMeta();
        for (const s of res.suggestions) {
          meta[s.kind][s.page] = { needsReview: s.needs_review, confidence: s.confidence };
        }
        setSuggestionMeta(meta);
        setClassifyState("done");
        setClassifyDone(true);
      })
      .catch((e) => {
        if (cancelled) return;
        setClassifyState("idle");
        setClassifyDone(true); // let previews reveal; manual labelling still works
        setError((e as Error).message);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, pageCounts.original, pageCounts.translated]);

  // Hold the previews until everything is ready: preload every page thumbnail (so the grid
  // appears all at once instead of images popping in) while classification runs in parallel.
  useEffect(() => {
    if (!projectId || pageCounts.original === null || pageCounts.translated === null) return;
    setPreviewPhase("preparing");
    setThumbsLoaded(0);
    analysisStartRef.current = performance.now(); // TEMP DIAGNOSTIC
    setAnalysisMs(null); // TEMP DIAGNOSTIC

    const pages: { kind: Kind; page: number }[] = [];
    for (let p = 1; p <= pageCounts.original; p++) pages.push({ kind: "original", page: p });
    for (let p = 1; p <= pageCounts.translated; p++) pages.push({ kind: "translated", page: p });

    let cancelled = false;
    let loaded = 0;
    const imgs: HTMLImageElement[] = [];
    for (const { kind, page } of pages) {
      const img = new Image();
      const done = () => {
        if (cancelled) return;
        loaded += 1;
        setThumbsLoaded(loaded);
      };
      img.onload = done;
      img.onerror = done;
      img.src = api.thumbnailUrl(projectId, kind, page);
      imgs.push(img);
    }
    return () => {
      cancelled = true;
      for (const img of imgs) {
        img.onload = null;
        img.onerror = null;
      }
    };
  }, [projectId, pageCounts.original, pageCounts.translated]);

  const totalThumbs = (pageCounts.original ?? 0) + (pageCounts.translated ?? 0);
  // Two phases: preview preload (fast, determinate %) then OCR/classification (variable —
  // shown as an indeterminate spinner so the bar never looks "stuck").
  const previewsLoading = totalThumbs === 0 || thumbsLoaded < totalThumbs;
  const thumbPercent = totalThumbs === 0 ? 0 : Math.round((thumbsLoaded / totalThumbs) * 100);

  // Reveal the grids once all thumbnails are in AND classification has settled.
  useEffect(() => {
    if (previewPhase !== "preparing") return;
    if (totalThumbs > 0 && thumbsLoaded >= totalThumbs && classifyDone) {
      setPreviewPhase("ready");
      // TEMP DIAGNOSTIC: record how long the full analysis took.
      if (analysisStartRef.current != null) {
        setAnalysisMs(performance.now() - analysisStartRef.current);
      }
    }
  }, [previewPhase, thumbsLoaded, totalThumbs, classifyDone]);

  // Pages the classifier flagged for human review (drives the strong red flag + the
  // pre-generate safety gate).
  const reviewPages = (["original", "translated"] as Kind[]).flatMap((kind) =>
    Object.entries(suggestionMeta[kind])
      .filter(([, info]) => info.needsReview)
      .map(([page]) => ({ kind, page: Number(page) }))
  );

  const handleRole = (kind: Kind, page: number, role: Role) => {
    setClassification((c) => ({
      ...c,
      [kind]: { ...c[kind], [page]: role },
    }));
    // A manual choice resolves any "needs review" flag on that page.
    setSuggestionMeta((m) => {
      if (!m[kind][page]) return m;
      const next = { ...m, [kind]: { ...m[kind] } };
      delete next[kind][page];
      return next;
    });
  };

  // Clear a review flag without changing the label — for a page the team checked and the
  // suggested label is correct (e.g. a translated page flagged only because it didn't line up
  // positionally with the English side). Keeps the "auto" tag; clears the red flag and the gate.
  const dismissReview = (kind: Kind, page: number) => {
    setSuggestionMeta((m) => {
      const info = m[kind][page];
      if (!info || !info.needsReview) return m;
      return { ...m, [kind]: { ...m[kind], [page]: { ...info, needsReview: false } } };
    });
  };

  const resetProject = async () => {
    setProjectId(null);
    setPageCounts({ original: null, translated: null });
    setClassification(emptyClassification());
    setSuggestionMeta(emptyMeta());
    setClassifyState("idle");
    setClassifyNote(null);
    setClassifyDone(false);
    setPreviewPhase("idle");
    setThumbsLoaded(0);
    analysisStartRef.current = null; // TEMP DIAGNOSTIC
    setAnalysisMs(null); // TEMP DIAGNOSTIC
    setGenerateMs(null); // TEMP DIAGNOSTIC
    setWarning(null);
    setResultKey((k) => k + 1);
    const p = await api.createProject();
    setProjectId(p.project_id);
  };

  // Force GeneratePanel to remount (clear its local form state) after a reset.
  const [resultKey, setResultKey] = useState(0);

  return (
    <>
      <main>
        {error && <div className="error">{error}</div>}
        {!projectId && <p className="muted">Starting a new project…</p>}

        {projectId && (
          <>
            <UploadPanel
              projectId={projectId}
              pageCounts={pageCounts}
              onUploaded={handleUploaded}
              onError={setError}
            />

            {warning && <div className="warning">{warning}</div>}

            {ready && previewPhase === "preparing" && (
              <section className="panel">
                <h2>Preparing previews…</h2>
                <div className="prep-status">
                  <span className="spinner" aria-hidden="true" />
                  <span>
                    {previewsLoading
                      ? `Loading page previews… ${thumbPercent}%`
                      : "Detecting academic documents… scanned pages take a little longer."}
                  </span>
                </div>
                {previewsLoading ? (
                  <div className="progress progress-lg">
                    <div className="progress-bar" style={{ width: `${thumbPercent}%` }} />
                  </div>
                ) : (
                  <div className="progress progress-lg indeterminate">
                    <div className="progress-bar" />
                  </div>
                )}
                <p className="muted" style={{ marginBottom: 0 }}>
                  Everything will appear together once it's ready.
                </p>
              </section>
            )}

            {ready && previewPhase === "ready" && (
              <section className="panel">
                <h2>2. Review page labels</h2>
                <p className="muted" style={{ marginTop: 0 }}>
                  Solicitor (page 1), apostille (page 2) and the translated notary (last
                  page) are applied automatically. Document pages are auto-detected as{" "}
                  <strong>Academic</strong> or <strong>Other</strong> — please review.
                </p>

                {classifyState === "running" && (
                  <div className="info">Detecting academic documents…</div>
                )}
                {classifyState === "done" && (
                  <div className="info">
                    Academic pages were auto-detected from the document text.{" "}
                    <strong>Please review the highlighted pages</strong> before generating —
                    every label can be changed below.
                  </div>
                )}
                {classifyState === "unavailable" && classifyNote && (
                  <div className="warning">{classifyNote}</div>
                )}

                <div className="legend">
                  {ROLE_ORDER.map((r) => (
                    <span key={r}>
                      <span className="badge" style={{ background: ROLE_META[r].color }} />
                      {ROLE_META[r].label}
                      {ROLE_META[r].translatedOnly ? " (translated only)" : ""}
                    </span>
                  ))}
                </div>
                <div className="grids">
                  <PageGrid
                    projectId={projectId}
                    kind="original"
                    pageCount={pageCounts.original!}
                    classification={classification}
                    suggestionMeta={suggestionMeta}
                    onChange={handleRole}
                    onDismiss={dismissReview}
                    onZoom={(kind, page) => setZoom({ kind, page })}
                  />
                  <PageGrid
                    projectId={projectId}
                    kind="translated"
                    pageCount={pageCounts.translated!}
                    classification={classification}
                    suggestionMeta={suggestionMeta}
                    onChange={handleRole}
                    onDismiss={dismissReview}
                    onZoom={(kind, page) => setZoom({ kind, page })}
                  />
                </div>
              </section>
            )}

            <GeneratePanel
              key={resultKey}
              projectId={projectId}
              classification={classification}
              ready={ready && previewPhase === "ready"}
              reviewPages={reviewPages}
              onGenerated={setGenerateMs}
              onCleared={resetProject}
              onError={setError}
            />
          </>
        )}
      </main>

      {zoom && projectId && (
        <PageZoomModal
          projectId={projectId}
          kind={zoom.kind}
          page={zoom.page}
          onClose={() => setZoom(null)}
        />
      )}

      {/* TEMP DIAGNOSTIC (remove later): analysis + generate timings. */}
      <div className="diag-box">
        <strong>⏱ Diagnostics (temp)</strong>
        <div>
          Analysis:{" "}
          {previewPhase === "preparing"
            ? "running…"
            : analysisMs == null
              ? "—"
              : `${(analysisMs / 1000).toFixed(1)}s`}
        </div>
        <div>
          Generate: {generateMs == null ? "—" : `${(generateMs / 1000).toFixed(1)}s`}
        </div>
      </div>
    </>
  );
}
