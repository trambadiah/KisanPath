"use client";

import { AudioLines, Mic, RotateCcw, Square } from "lucide-react";

import { useLocale } from "@/components/locale-provider";
import type { VoiceState } from "@/lib/contracts";
import type { TranslationKey } from "@/lib/i18n";

const labels: Record<VoiceState, TranslationKey> = { idle: "voiceStart", listening: "voiceStop", processing: "voiceProcessingLabel", speaking: "voiceStopResponse", error: "voiceRetryLabel" };

export function VoiceOrb({ state, onPress, caption }: { state: VoiceState; onPress: () => void; caption: string }) {
  const { t } = useLocale();
  const Icon = state === "listening" ? Square : state === "error" ? RotateCcw : state === "speaking" ? AudioLines : Mic;
  return (
    <div className={`voiceOrbWrap voice-${state}`}>
      <div className="orbStatus" role="status" aria-live="polite">
        <span className="statusDot" />
        {caption}
      </div>
      <button
        className="voiceOrb"
        type="button"
        onClick={onPress}
        aria-label={t(labels[state])}
        aria-pressed={state === "listening"}
        disabled={state === "processing"}
      >
        <span className="orbHalo orbHaloOne" aria-hidden="true" />
        <span className="orbHalo orbHaloTwo" aria-hidden="true" />
        <span className="orbCore" aria-hidden="true">
          <span className="orbGrid" />
          <Icon size={state === "listening" ? 25 : 30} strokeWidth={1.75} />
        </span>
        <span className="orbWaveform" aria-hidden="true">
          {Array.from({ length: 9 }).map((_, index) => (
            <i key={index} />
          ))}
        </span>
      </button>
      <p className="voiceHint">
        {state === "listening" ? t("voiceFinishHint") : t("transcriptHint")}
      </p>
    </div>
  );
}
