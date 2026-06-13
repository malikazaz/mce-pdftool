import { api } from "../api/client";
import { ROLE_META, ROLE_ORDER } from "../roles";
import type { Classification, Kind, Role } from "../types/pdf";

interface Props {
  projectId: string;
  kind: Kind;
  pageCount: number;
  classification: Classification;
  onChange: (kind: Kind, page: number, role: Role) => void;
  onZoom: (kind: Kind, page: number) => void;
}

export default function PageGrid({
  projectId,
  kind,
  pageCount,
  classification,
  onChange,
  onZoom,
}: Props) {
  const title = kind === "original" ? "Original / English" : "Translated";
  const pages = Array.from({ length: pageCount }, (_, i) => i + 1);

  return (
    <div>
      <div className="grid-title">
        {title} — {pageCount} page(s)
      </div>
      <div className="thumb-grid">
        {pages.map((page) => {
          const role = classification[kind][page] ?? "unassigned";
          const meta = ROLE_META[role];
          return (
            <div className="thumb" key={page} style={{ borderColor: meta.color }}>
              <div className="thumb-head">
                <span>Page {page}</span>
                <span className="badge" style={{ background: meta.color }} />
              </div>
              <img
                src={api.thumbnailUrl(projectId, kind, page)}
                alt={`Page ${page}`}
                loading="lazy"
                onClick={() => onZoom(kind, page)}
              />
              <select
                value={role}
                style={{ background: meta.color }}
                onChange={(e) => onChange(kind, page, e.target.value as Role)}
              >
                {ROLE_ORDER.filter(
                  // Notary is translated-only.
                  (r) => !(ROLE_META[r].translatedOnly && kind === "original")
                ).map((r) => (
                  <option key={r} value={r}>
                    {ROLE_META[r].label}
                  </option>
                ))}
              </select>
            </div>
          );
        })}
      </div>
    </div>
  );
}
