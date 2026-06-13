import type { Classification, GeneratePayload, Kind, Role } from "./types/pdf";

// The legal pages sit at predictable positions in every set: page 1 is the
// solicitor certification, page 2 the apostille, and (for the translated set
// only) the final page is the translator's notary stamp. We pre-label these on
// upload so the user only has to classify the document pages in between; any of
// them can still be changed via the per-page dropdown.
export function defaultRolesFor(kind: Kind, pageCount: number): Record<number, Role> {
  const roles: Record<number, Role> = {};
  if (pageCount >= 1) roles[1] = "solicitor";
  if (pageCount >= 2) roles[2] = "apostille";
  // Notary is translated-only and must not collide with solicitor/apostille.
  if (kind === "translated" && pageCount >= 3) roles[pageCount] = "notary";
  return roles;
}

// Pages (1-based, ascending) in a given PDF that carry a given role.
export function pagesWithRole(
  classification: Classification,
  kind: Kind,
  role: Role
): number[] {
  return Object.entries(classification[kind])
    .filter(([, r]) => r === role)
    .map(([p]) => Number(p))
    .sort((a, b) => a - b);
}

export function buildPayload(
  classification: Classification,
  clientName: string,
  labels: { diploma: string; continuation: string }
): GeneratePayload {
  return {
    client_name: clientName,
    labels,
    legal_pages: {
      solicitor: {
        original: pagesWithRole(classification, "original", "solicitor"),
        translated: pagesWithRole(classification, "translated", "solicitor"),
      },
      apostille: {
        original: pagesWithRole(classification, "original", "apostille"),
        translated: pagesWithRole(classification, "translated", "apostille"),
      },
      notary: {
        translated: pagesWithRole(classification, "translated", "notary"),
      },
    },
    academic: {
      original: pagesWithRole(classification, "original", "academic"),
      translated: pagesWithRole(classification, "translated", "academic"),
    },
    other: {
      original: pagesWithRole(classification, "original", "other"),
      translated: pagesWithRole(classification, "translated", "other"),
    },
  };
}

export interface OrderItem {
  source: Kind;
  page: number;
  role: Role;
}

// Mirror of the backend ordering, used for the live preview.
export function buildOrderPreview(
  payload: GeneratePayload,
  bucket: "academic" | "other"
): OrderItem[] {
  const lp = payload.legal_pages;
  const docs = payload[bucket];
  const items: OrderItem[] = [];

  // Translated section
  lp.solicitor.translated.forEach((p) => items.push({ source: "translated", page: p, role: "solicitor" }));
  lp.apostille.translated.forEach((p) => items.push({ source: "translated", page: p, role: "apostille" }));
  docs.translated.forEach((p) => items.push({ source: "translated", page: p, role: bucket }));
  lp.notary.translated.forEach((p) => items.push({ source: "translated", page: p, role: "notary" }));

  // English / original section
  lp.solicitor.original.forEach((p) => items.push({ source: "original", page: p, role: "solicitor" }));
  lp.apostille.original.forEach((p) => items.push({ source: "original", page: p, role: "apostille" }));
  docs.original.forEach((p) => items.push({ source: "original", page: p, role: bucket }));

  return items;
}
