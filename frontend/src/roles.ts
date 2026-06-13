import type { Role } from "./types/pdf";

export interface RoleMeta {
  label: string;
  color: string;
  // Roles that only make sense on the translated PDF.
  translatedOnly?: boolean;
}

export const ROLE_META: Record<Role, RoleMeta> = {
  unassigned: { label: "Unassigned", color: "#9ca3af" },
  solicitor: { label: "Solicitor", color: "#2563eb" },
  apostille: { label: "Apostille", color: "#7c3aed" },
  notary: { label: "Notary", color: "#db2777", translatedOnly: true },
  academic: { label: "Academic", color: "#059669" },
  other: { label: "Other", color: "#d97706" },
};

export const ROLE_ORDER: Role[] = [
  "unassigned",
  "solicitor",
  "apostille",
  "notary",
  "academic",
  "other",
];
