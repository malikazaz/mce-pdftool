import { useEffect, useState } from "react";
import { api } from "./api/client";
import UploadPanel from "./components/UploadPanel";
import PageGrid from "./components/PageGrid";
import PageZoomModal from "./components/PageZoomModal";
import GeneratePanel from "./components/GeneratePanel";
import { ROLE_META, ROLE_ORDER } from "./roles";
import { defaultRolesFor } from "./payload";
import type { Classification, Kind, Role } from "./types/pdf";

const emptyClassification = (): Classification => ({ original: {}, translated: {} });

export default function App() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [pageCounts, setPageCounts] = useState<{ original: number | null; translated: number | null }>({
    original: null,
    translated: null,
  });
  const [classification, setClassification] = useState<Classification>(emptyClassification());
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

  const handleRole = (kind: Kind, page: number, role: Role) => {
    setClassification((c) => ({
      ...c,
      [kind]: { ...c[kind], [page]: role },
    }));
  };

  const resetProject = async () => {
    setProjectId(null);
    setPageCounts({ original: null, translated: null });
    setClassification(emptyClassification());
    setWarning(null);
    setResultKey((k) => k + 1);
    const p = await api.createProject();
    setProjectId(p.project_id);
  };

  // Force GeneratePanel to remount (clear its local form state) after a reset.
  const [resultKey, setResultKey] = useState(0);

  const ready = pageCounts.original !== null && pageCounts.translated !== null;

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
                <h2>2. Label every page</h2>
                <p className="muted" style={{ marginTop: 0 }}>
                  Solicitor (page 1), apostille (page 2) and the translated notary (last
                  page) were applied automatically — adjust if needed. Label the remaining
                  pages as <strong>Academic</strong> or <strong>Other</strong>.
                </p>
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
                    onChange={handleRole}
                    onZoom={(kind, page) => setZoom({ kind, page })}
                  />
                  <PageGrid
                    projectId={projectId}
                    kind="translated"
                    pageCount={pageCounts.translated!}
                    classification={classification}
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
