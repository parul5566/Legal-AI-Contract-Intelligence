export const SEVERITY_ORDER = ["critical", "high", "medium", "low"];
export const SEV_STYLE = {
  critical: { bg: "#7f1d1d", label: "CRITICAL" },
  high: { bg: "#dc2626", label: "HIGH" },
  medium: { bg: "#d97706", label: "MEDIUM" },
  low: { bg: "#2563eb", label: "LOW" },
};

export const CLAUSE_LABELS = {
  payment_terms: "Payment Terms",
  term_termination: "Term & Termination",
  confidentiality: "Confidentiality",
  indemnification: "Indemnification",
  liability: "Liability",
  intellectual_property: "Intellectual Property",
  data_protection: "Data Protection",
  governing_law: "Governing Law",
  dispute_resolution: "Dispute Resolution",
  non_compete: "Non-Compete",
  non_solicitation: "Non-Solicitation",
  renewal: "Renewal",
  warranty: "Warranty",
  force_majeure: "Force Majeure",
  assignment: "Assignment",
  insurance: "Insurance",
  compliance: "Compliance Obligations",
};

export const RISK_LABELS = {
  financial: "Financial Risk",
  legal: "Legal Risk",
  compliance: "Compliance Risk",
  operational: "Operational Risk",
  data_privacy: "Data Privacy Risk",
  liability_exposure: "Liability Exposure",
  unfavorable_termination: "Unfavorable Termination",
  unlimited_liability: "Unlimited Liability",
  one_sided_indemnity: "One-sided Indemnification",
  auto_renewal: "Automatic Renewal",
  missing_clause: "Missing Clauses",
  ambiguity: "Ambiguous Language",
  unusual_obligation: "Unusual Obligations",
};

export const clauseLabel = (c) => CLAUSE_LABELS[c] || c.replaceAll("_", " ");
export const riskLabel = (c) => RISK_LABELS[c] || c.replaceAll("_", " ");

export const STATUS_STYLE = {
  pending: "#9ca3af",
  parsing: "#3b82f6",
  analyzing: "#8b5cf6",
  ready: "#16a34a",
  failed: "#dc2626",
};

export function fmtDate(d) {
  if (!d) return "—";
  try {
    return new Date(d).toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return d;
  }
}

export function fmtBytes(n) {
  if (!n && n !== 0) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}
