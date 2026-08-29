import { AlertTriangle, Check, CircleHelp, ShieldQuestion, X } from "lucide-react";

import type { EligibilityStatus, RuleResult } from "@/lib/contracts";

const eligibilityLabels: Record<EligibilityStatus, string> = {
  LIKELY_ELIGIBLE: "Likely eligible",
  NOT_ELIGIBLE: "Not eligible by a published condition",
  INSUFFICIENT_INFORMATION: "Need more information",
  MANUAL_REVIEW: "Manual review recommended",
};

export function EligibilityStatusBadge({ status }: { status: EligibilityStatus }) {
  const Icon = {
    LIKELY_ELIGIBLE: Check,
    NOT_ELIGIBLE: X,
    INSUFFICIENT_INFORMATION: CircleHelp,
    MANUAL_REVIEW: ShieldQuestion,
  }[status];
  return (
    <span className={`statusBadge status-${status.toLowerCase()}`}>
      <Icon size={14} strokeWidth={2.4} aria-hidden="true" />
      {eligibilityLabels[status]}
    </span>
  );
}

export function RuleResultIcon({ result }: { result: RuleResult }) {
  const Icon = {
    PASS: Check,
    FAIL: X,
    UNKNOWN: CircleHelp,
    MANUAL_REVIEW: AlertTriangle,
  }[result];
  return (
    <span className={`ruleIcon rule-${result.toLowerCase()}`} aria-label={result.replace("_", " ")}>
      <Icon size={16} aria-hidden="true" />
    </span>
  );
}
