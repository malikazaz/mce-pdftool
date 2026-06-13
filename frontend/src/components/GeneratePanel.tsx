import { useMemo, useState } from "react";
import { api } from "../api/client";
import { ROLE_META } from "../roles";
import { buildOrderPreview, buildPayload } from "../payload";
import type { Classification, GenerateResponse, OutputSummary } from "../types/pdf";

interface Props {
  projectId: string;
  classification: Classification;
  ready: boolean; // both PDFs uploaded
  onCleared: () => void;
  onError: (message: string) => void;
}

function OrderPreview({
  title,
  filename,
  items,
}: {
  title: string;
  filename: string;
  items: ReturnType<typeof buildOrderPreview>;
}) {
  const translated = items.filter((i) => i.source === "translated");
  const original = items.filter((i) => i.source === "original");
  return (
    <div>
      <div className="grid-title">
        {title} <span className="muted">→ {filename}</span>
      </div>
      {items.length === 0 ? (
        <p className="muted">No pages selected yet.</p>
      ) : (
        <ol className="order-list">
          <li className="section-divider">Translated section</li>
          {translated.map((it, i) => (
            <li key={`t${i}`}>
              <span className="badge" style={{ background: ROLE_META[it.role].color }} />
              Translated p{it.page} — {ROLE_META[it.role].label}
            </li>
          ))}
          <li className="section-divider">English section</li>
          {original.map((it, i) => (
            <li key={`o${i}`}>
              <span className="badge" style={{ background: ROLE_META[it.role].color }} />
              Original p{it.page} — {ROLE_META[it.role].label}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

export default function GeneratePanel({
  projectId,
  classification,
  ready,
  onCleared,
  onError,
}: Props) {
  const [clientName, setClientName] = useState("");
  const [diplomaLabel, setDiplomaLabel] = useState("Diploma");
  const [continuationLabel, setContinuationLabel] = useState("Continuation");
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [busy, setBusy] = useState(false);

  const labels = { diploma: diplomaLabel, continuation: continuationLabel };
  const payload = useMemo(
    () => buildPayload(classification, clientName || "Client", labels),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [classification, clientName, diplomaLabel, continuationLabel]
  );

  const diplomaItems = buildOrderPreview(payload, "academic");
  const continuationItems = buildOrderPreview(payload, "other");

  const issues: string[] = [];
  if (!clientName.trim()) issues.push("Enter the client's full name.");
  if (diplomaItems.length === 0) issues.push("Diploma has no pages selected.");
  if (continuationItems.length === 0)
    issues.push("Continuation has no pages selected.");

  const generate = async () => {
    setBusy(true);
    setResult(null);
    try {
      const res = await api.generate(projectId, buildPayload(classification, clientName.trim(), labels));
      setResult(res);
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const clear = async () => {
    if (!confirm("Clear this project and delete all temporary files?")) return;
    setBusy(true);
    try {
      await api.deleteProject(projectId);
      onCleared();
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="panel">
      <h2>3. Generate &amp; export</h2>

      <div className="row" style={{ marginBottom: 16 }}>
        <div style={{ flex: 2, minWidth: 240 }}>
          <label className="field">Client full name</label>
          <input
            type="text"
            value={clientName}
            placeholder="e.g. John Smith"
            onChange={(e) => setClientName(e.target.value)}
          />
        </div>
        <div style={{ flex: 1, minWidth: 160 }}>
          <label className="field">Diploma label</label>
          <input type="text" value={diplomaLabel} onChange={(e) => setDiplomaLabel(e.target.value)} />
        </div>
        <div style={{ flex: 1, minWidth: 160 }}>
          <label className="field">Continuation label</label>
          <input
            type="text"
            value={continuationLabel}
            onChange={(e) => setContinuationLabel(e.target.value)}
          />
        </div>
      </div>

      <div className="preview-cols">
        <OrderPreview
          title="Diploma (academic)"
          filename={`${clientName || "Client"} - ${diplomaLabel}.pdf`}
          items={diplomaItems}
        />
        <OrderPreview
          title="Continuation (other)"
          filename={`${clientName || "Client"} - ${continuationLabel}.pdf`}
          items={continuationItems}
        />
      </div>

      {ready && issues.length > 0 && (
        <div className="warning">
          <strong>Before generating:</strong>
          <ul style={{ margin: "6px 0 0" }}>
            {issues.map((i) => (
              <li key={i}>{i}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="row" style={{ marginTop: 16, alignItems: "center" }}>
        <button
          className="primary"
          disabled={!ready || issues.length > 0 || busy}
          onClick={generate}
        >
          {busy ? "Working…" : "Generate PDFs"}
        </button>
        {result && (
          <a href={api.downloadUrl(projectId)}>
            <button className="secondary">Download ZIP</button>
          </a>
        )}
        <button className="danger" disabled={busy} onClick={clear} style={{ marginLeft: "auto" }}>
          Clear project
        </button>
      </div>

      {result && (
        <div style={{ marginTop: 12 }}>
          <p className="muted">Generated:</p>
          <ul>
            {result.outputs.map((o: OutputSummary) => (
              <li key={o.filename}>
                {o.filename} — {o.page_count} page(s)
              </li>
            ))}
          </ul>
          {result.warnings.map((w) => (
            <div className="warning" key={w}>
              {w}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
