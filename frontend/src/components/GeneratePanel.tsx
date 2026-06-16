import { useMemo, useState } from "react";
import { api } from "../api/client";
import { ROLE_META } from "../roles";
import { buildOrderPreview, buildPayload } from "../payload";
import type { Classification, GenerateResponse, Kind, OutputSummary } from "../types/pdf";

interface Props {
  projectId: string;
  classification: Classification;
  ready: boolean; // both PDFs uploaded
  reviewPages: { kind: Kind; page: number }[];
  onGenerated?: (ms: number) => void; // TEMP DIAGNOSTIC: report generate duration
  onCleared: () => void;
  onError: (message: string) => void;
}

const pageLabel = (r: { kind: Kind; page: number }) =>
  `${r.kind === "original" ? "Original" : "Translated"} p${r.page}`;

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
  reviewPages,
  onGenerated,
  onCleared,
  onError,
}: Props) {
  const [clientName, setClientName] = useState("");
  const [diplomaLabel, setDiplomaLabel] = useState("Diploma");
  const [continuationLabel, setContinuationLabel] = useState("Continuation");
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [ack, setAck] = useState(false);
  // GOOGLE-DRIVE: state for the Save to Google Drive action (endpoint is a stub for now).
  const [driveBusy, setDriveBusy] = useState(false);
  const [driveMsg, setDriveMsg] = useState<string | null>(null);

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

  const hasFlagged = reviewPages.length > 0;

  const openConfirm = () => {
    setAck(false);
    setShowConfirm(true);
  };

  const generate = async () => {
    setShowConfirm(false);
    setBusy(true);
    setResult(null);
    try {
      const t0 = performance.now(); // TEMP DIAGNOSTIC
      const res = await api.generate(projectId, buildPayload(classification, clientName.trim(), labels));
      onGenerated?.(performance.now() - t0); // TEMP DIAGNOSTIC
      setResult(res);
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  // GOOGLE-DRIVE: call the (stub) backend endpoint. Once implemented it should report the
  // saved file link(s); for now it surfaces the backend's "not configured" message.
  const saveToDrive = async () => {
    setDriveBusy(true);
    setDriveMsg(null);
    try {
      const res = await api.saveToDrive(projectId);
      setDriveMsg(res.message ?? "Saved to Google Drive.");
    } catch (e) {
      setDriveMsg((e as Error).message);
    } finally {
      setDriveBusy(false);
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
          onClick={openConfirm}
        >
          {busy ? "Working…" : "Generate PDFs"}
        </button>
        {result && (
          <a href={api.downloadUrl(projectId)}>
            <button className="secondary">Download ZIP</button>
          </a>
        )}
        {/* GOOGLE-DRIVE: saves the generated outputs straight to Drive (backend stub for now). */}
        {result && (
          <button className="secondary" onClick={saveToDrive} disabled={driveBusy}>
            {driveBusy ? "Saving…" : "Save to Google Drive"}
          </button>
        )}
        <button className="danger" disabled={busy} onClick={clear} style={{ marginLeft: "auto" }}>
          Clear project
        </button>
      </div>

      {driveMsg && <div className="info">{driveMsg}</div>}

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

      {showConfirm && (
        <div className="modal-backdrop" onClick={() => setShowConfirm(false)}>
          <div
            className={`modal confirm-modal${hasFlagged ? " danger" : ""}`}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="confirm-head">
              {hasFlagged ? "⚠ Pages still flagged for review" : "Generate documents?"}
            </div>
            <div className="confirm-body">
              {hasFlagged ? (
                <>
                  <p style={{ marginTop: 0 }}>
                    These documents are used for <strong>visa applications</strong> — an
                    incorrect label can have serious consequences. The auto-detection flagged
                    the following page(s) as needing a human check:
                  </p>
                  <div className="flagged-list">
                    {reviewPages.map(pageLabel).join(", ")}
                  </div>
                  <label className="confirm-check">
                    <input
                      type="checkbox"
                      checked={ack}
                      onChange={(e) => setAck(e.target.checked)}
                    />
                    <span>
                      I have reviewed the flagged page(s) above and confirm every label is
                      correct.
                    </span>
                  </label>
                </>
              ) : (
                <p style={{ marginTop: 0 }}>
                  Generate the Diploma and Continuation PDFs for{" "}
                  <strong>{clientName || "Client"}</strong>?
                </p>
              )}
            </div>
            <div className="confirm-actions">
              <button className="secondary" onClick={() => setShowConfirm(false)}>
                Cancel
              </button>
              <button
                className="primary"
                disabled={hasFlagged && !ack}
                onClick={generate}
              >
                {hasFlagged ? "Confirm & generate" : "Generate"}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
