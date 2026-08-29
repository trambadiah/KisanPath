"use client";

import { AudioWaveform, Check, PencilLine } from "lucide-react";

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
  return (
    <section className="confirmationCard" aria-labelledby="confirmation-title">
      <div className="confirmationIcon" aria-hidden="true">
        <AudioWaveform size={21} />
      </div>
      <div className="confirmationBody">
        <span className="eyebrow warm">Voice check · {Math.round(confirmation.confidence * 100)}% confidence</span>
        <h2 id="confirmation-title">Did we hear your {confirmation.label} correctly?</h2>
        <p>
          The recording could mean either value. We will not use it for eligibility until you confirm.
        </p>
        <div className="confirmationChoices" aria-label="Choose the correct value">
          {confirmation.alternatives.map((value, index) => (
            <button
              key={value}
              className={`confirmationChoice ${index === 0 ? "recommendedChoice" : ""}`}
              type="button"
              onClick={() => onConfirm(value)}
            >
              {index === 0 && <Check size={15} aria-hidden="true" />}
              <span>{value}</span>
              <small>{index === 0 ? "heard most clearly" : "possible alternative"}</small>
            </button>
          ))}
        </div>
        <button className="textButton" type="button" onClick={onCorrect}>
          <PencilLine size={15} aria-hidden="true" />
          Enter a different value
        </button>
      </div>
    </section>
  );
}
