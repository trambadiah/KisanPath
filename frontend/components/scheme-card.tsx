"use client";

import { ArrowRight, BookOpen, FileText, Headphones, Pause, Sparkles } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { EvidenceDrawer } from "@/components/evidence-drawer";
import { useLocale } from "@/components/locale-provider";
import { EligibilityStatusBadge } from "@/components/status-badge";
import type { SchemeRecommendation } from "@/lib/contracts";
import { localizeScheme } from "@/lib/scheme-i18n";

export function SchemeCard({ scheme, featured = false }: { scheme: SchemeRecommendation; featured?: boolean }) {
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const { language, t } = useLocale();
  const localized = localizeScheme(scheme, language);

  function toggleSpeech() {
    if (!("speechSynthesis" in window)) return;
    if (speaking) {
      window.speechSynthesis.cancel();
      setSpeaking(false);
      return;
    }
    const utterance = new SpeechSynthesisUtterance(`${localized.name}. ${localized.benefitSummary}. ${localized.nextAction}`);
    utterance.lang = language === "gu" ? "gu-IN" : language === "hi" ? "hi-IN" : "en-IN";
    utterance.onend = () => setSpeaking(false);
    setSpeaking(true);
    window.speechSynthesis.speak(utterance);
  }

  const unresolved = localized.conditionsTotal - localized.conditionsPassed;
  return (
    <>
      <article className={`schemeCard ${featured ? "schemeFeatured" : ""}`}>
        <div className="schemeCardGlow" aria-hidden="true" />
        <header className="schemeCardHeader">
          <div className="schemeMonogram" aria-hidden="true">{localized.shortName.slice(0, 2).toUpperCase()}</div>
          <EligibilityStatusBadge status={localized.status} />
        </header>
        <div className="schemeCardBody">
          {featured && <span className="eyebrow"><Sparkles size={13} />{t("strongestMatch")}</span>}
          <h2>{localized.name}</h2>
          <p className="benefitSummary">{localized.benefitSummary}</p>
          <div className="conditionSummary">
            <div className="conditionBar" aria-hidden="true"><span style={{ width: `${(localized.conditionsPassed / localized.conditionsTotal) * 100}%` }} /></div>
            <span>{t("conditionsPassed", { passed: localized.conditionsPassed })}{unresolved > 0 ? ` · ${t("needsAttention", { count: unresolved })}` : ` · ${t("allReviewed")}`}</span>
          </div>
          <div className="nextAction"><span>{t("nextStep")}</span><p>{localized.nextAction}</p></div>
        </div>
        <footer className="schemeCardActions">
          <button className="button buttonSecondary" type="button" onClick={() => setEvidenceOpen(true)}><BookOpen size={16} />{t("whyThis")}</button>
          <Link className="button buttonGhost" href={`/schemes/${scheme.id}`}><FileText size={16} />{t("details")}</Link>
          <button className="iconButton listenButton" type="button" onClick={toggleSpeech} aria-label={speaking ? t("stopReading", { name: localized.name }) : t("listenTo", { name: localized.name })}>
            {speaking ? <Pause size={18} /> : <Headphones size={18} />}
          </button>
          <Link className="cardArrow" href={`/schemes/${scheme.id}`} aria-label={t("openScheme", { name: localized.name })}><ArrowRight size={19} /></Link>
        </footer>
      </article>
      <EvidenceDrawer scheme={localized} open={evidenceOpen} onClose={() => setEvidenceOpen(false)} />
    </>
  );
}
