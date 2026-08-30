"use client";

import { AudioWaveform, Check, PencilLine } from "lucide-react";

import { useLocale } from "@/components/locale-provider";
import type { PendingConfirmationView } from "@/lib/contracts";

export function ConfirmationCard({
  confirmation,
  onConfirm,
  onCorrect,
}: {
  confirmation: PendingConfirmationView;
  onConfirm: (value: string) => void;
  onCorrect: () => void;
}) {
  const { t } = useLocale();
  const field = confirmation.fieldId === "land_area" ? t("land") : confirmation.label;
  return (
    <section className="confirmationCard" aria-labelledby="confirmation-title">
      <div className="confirmationIcon" aria-hidden="true">
        <AudioWaveform size={21} />
      </div>
      <div className="confirmationBody">
        <span className="eyebrow warm">{t("voiceCheck", { confidence: Math.round(confirmation.confidence * 100) })}</span>
        <h2 id="confirmation-title">{t("heardCorrectly", { field })}</h2>
        <p>{t("ambiguityBody")}</p>
        <div className="confirmationChoices" aria-label={t("chooseValue")}>
          {confirmation.alternatives.map((value, index) => (
            <button
              key={value}
              className={`confirmationChoice ${index === 0 ? "recommendedChoice" : ""}`}
              type="button"
              onClick={() => onConfirm(value)}
            >
              {index === 0 && <Check size={15} aria-hidden="true" />}
              <span>{value === "3 એકર" ? t("threeAcres") : value === "30 એકર" ? t("thirtyAcres") : value}</span>
              <small>{index === 0 ? t("heardClearly") : t("possibleAlternative")}</small>
            </button>
          ))}
        </div>
        <button className="textButton" type="button" onClick={onCorrect}>
          <PencilLine size={15} aria-hidden="true" />
          {t("differentValue")}
        </button>
      </div>
    </section>
  );
}
