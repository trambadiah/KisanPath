"use client";

import { AlertTriangle, Check, CircleHelp, ShieldQuestion, X } from "lucide-react";

import { useLocale } from "@/components/locale-provider";
import type { EligibilityStatus, RuleResult } from "@/lib/contracts";
import type { TranslationKey } from "@/lib/i18n";

const eligibilityLabels: Record<EligibilityStatus, TranslationKey> = {
  LIKELY_ELIGIBLE: "likelyEligible", NOT_ELIGIBLE: "notEligible", INSUFFICIENT_INFORMATION: "needInformation", MANUAL_REVIEW: "manualReview",
};

export function EligibilityStatusBadge({ status }: { status: EligibilityStatus }) {
  const { t } = useLocale();
  const Icon = {
    LIKELY_ELIGIBLE: Check,
    NOT_ELIGIBLE: X,
    INSUFFICIENT_INFORMATION: CircleHelp,
    MANUAL_REVIEW: ShieldQuestion,
  }[status];
  return (
    <span className={`statusBadge status-${status.toLowerCase()}`}>
      <Icon size={14} strokeWidth={2.4} aria-hidden="true" />
      {t(eligibilityLabels[status])}
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
