import { useEffect, useState } from "react";
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
  const [warning, setWarning] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [zoom, setZoom] = useState<{ kind: Kind; page: number } | null>(null);

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
    api
      .classify(projectId)
      .then((res) => {
        if (cancelled) return;
        if (!res.ocr_available) {
          setClassifyState("unavailable");
          setClassifyNote(res.note);
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
      })
      .catch((e) => {
        if (cancelled) return;
        setClassifyState("idle");
        setError((e as Error).message);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, pageCounts.original, pageCounts.translated]);

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

  const resetProject = async () => {
    setProjectId(null);
    setPageCounts({ original: null, translated: null });
    setClassification(emptyClassification());
    setSuggestionMeta(emptyMeta());
    setClassifyState("idle");
    setClassifyNote(null);
    setWarning(null);
    setResultKey((k) => k + 1);
    const p = await api.createProject();
    setProjectId(p.project_id);
  };

  // Force GeneratePanel to remount (clear its local form state) after a reset.
  const [resultKey, setResultKey] = useState(0);

  return (
    <>
      <header className="app-header">
        <h1>MedConnect Europe — PDF Assembly Tool</h1>
        <p>
          Deterministic, manual page labelling. No AI, no external processing — files stay on
          this server and are cleared on demand.
        </p>
      </header>

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

            {ready && (
              <section className="panel">
                <h2>2. Review page labels</h2>
                <p className="muted" style={{ marginTop: 0 }}>
                  Solicitor (page 1), apostille (page 2) and the translated notary (last
                  page) are applied automatically. Document pages are auto-detected as{" "}
                  <strong>Academic</strong> or <strong>Other</strong> — please review.
                </p>

                {classifyState === "running" && (
                  <div className="warning">Detecting academic documents…</div>
                )}
                {classifyState === "done" && (
                  <div className="warning">
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
                    onZoom={(kind, page) => setZoom({ kind, page })}
                  />
                  <PageGrid
                    projectId={projectId}
                    kind="translated"
                    pageCount={pageCounts.translated!}
                    classification={classification}
                    suggestionMeta={suggestionMeta}
                    onChange={handleRole}
                    onZoom={(kind, page) => setZoom({ kind, page })}
                  />
                </div>
              </section>
            )}

            <GeneratePanel
              key={resultKey}
              projectId={projectId}
              classification={classification}
              ready={ready}
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
    </>
  );
}
