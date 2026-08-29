import { Check, Mic2, Pencil, TriangleAlert } from "lucide-react";

import type { ProfileFactView } from "@/lib/contracts";

export function ProfileChip({ fact, onEdit }: { fact: ProfileFactView; onEdit?: () => void }) {
  const needsConfirmation = fact.status === "needs_confirmation";
  return (
    <button
      className={`profileChip ${needsConfirmation ? "profileChipPending" : ""}`}
      type="button"
      onClick={onEdit}
      aria-label={`${fact.label}: ${fact.value}. ${needsConfirmation ? "Needs confirmation" : "Confirmed"}`}
    >
      <span className="profileChipIcon" aria-hidden="true">
        {needsConfirmation ? <TriangleAlert size={14} /> : <Check size={14} />}
      </span>
      <span>
        <small>{fact.label}</small>
        <strong>{fact.value}</strong>
      </span>
      {fact.source === "voice" && <Mic2 className="chipSource" size={13} aria-hidden="true" />}
      <Pencil className="chipEdit" size={13} aria-hidden="true" />
    </button>
  );
}
