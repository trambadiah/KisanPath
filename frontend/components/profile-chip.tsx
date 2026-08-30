"use client";

import { Check, Mic2, Pencil, TriangleAlert } from "lucide-react";

import { useLocale } from "@/components/locale-provider";
import type { ProfileFactView } from "@/lib/contracts";
import type { TranslationKey } from "@/lib/i18n";

const labels: Record<string, TranslationKey> = { state: "state", district: "district", land_area: "land", crop: "crop" };
const values: Record<string, TranslationKey> = { "ગુજરાત": "gujarat", "આણંદ": "anand", "3 એકર": "threeAcres", "મગફળી": "groundnut" };

export function ProfileChip({ fact, onEdit }: { fact: ProfileFactView; onEdit?: () => void }) {
  const { t } = useLocale();
  const needsConfirmation = fact.status === "needs_confirmation";
  const label = labels[fact.id] ? t(labels[fact.id]) : fact.label;
  const value = values[fact.value] ? t(values[fact.value]) : fact.value;
  return (
    <button
      className={`profileChip ${needsConfirmation ? "profileChipPending" : ""}`}
      type="button"
      onClick={onEdit}
      aria-label={`${label}: ${value}. ${needsConfirmation ? t("needsConfirmation") : t("confirmed")}`}
    >
      <span className="profileChipIcon" aria-hidden="true">
        {needsConfirmation ? <TriangleAlert size={14} /> : <Check size={14} />}
      </span>
      <span>
        <small>{label}</small>
        <strong>{value}</strong>
      </span>
      {fact.source === "voice" && <Mic2 className="chipSource" size={13} aria-hidden="true" />}
      <Pencil className="chipEdit" size={13} aria-hidden="true" />
    </button>
  );
}
