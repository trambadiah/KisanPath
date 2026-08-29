"use client";

import { ArrowRight, BookOpen, FileText, Headphones, Pause, Sparkles } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { EvidenceDrawer } from "@/components/evidence-drawer";
import { EligibilityStatusBadge } from "@/components/status-badge";
import type { SchemeRecommendation } from "@/lib/contracts";

export function SchemeCard({ scheme, featured = false }: { scheme: SchemeRecommendation; featured?: boolean }) {
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [speaking, setSpeaking] = useState(false);

  function toggleSpeech() {
    if (!("speechSynthesis" in window)) return;
    if (speaking) {
      window.speechSynthesis.cancel();
      setSpeaking(false);
      return;
    }
    const utterance = new SpeechSynthesisUtterance(`${scheme.name}. ${scheme.benefitSummary}. ${scheme.nextAction}`);
    utterance.onend = () => setSpeaking(false);
    setSpeaking(true);
    window.speechSynthesis.speak(utterance);
  }

  const unresolved = scheme.conditionsTotal - scheme.conditionsPassed;
  return (
    <>
      <article className={`schemeCard ${featured ? "schemeFeatured" : ""}`}>
        <div className="schemeCardGlow" aria-hidden="true" />
        <header className="schemeCardHeader">
          <div className="schemeMonogram" aria-hidden="true">{scheme.shortName.slice(0, 2).toUpperCase()}</div>
          <EligibilityStatusBadge status={scheme.status} />
        </header>
        <div className="schemeCardBody">
          {featured && <span className="eyebrow"><Sparkles size={13} />Strongest reviewed match</span>}
          <h2>{scheme.name}</h2>
          <p className="benefitSummary">{scheme.benefitSummary}</p>
          <div className="conditionSummary">
            <div className="conditionBar" aria-hidden="true"><span style={{ width: `${(scheme.conditionsPassed / scheme.conditionsTotal) * 100}%` }} /></div>
            <span>{scheme.conditionsPassed} conditions passed{unresolved > 0 ? ` · ${unresolved} needs attention` : " · all reviewed"}</span>
          </div>
          <div className="nextAction"><span>Next step</span><p>{scheme.nextAction}</p></div>
        </div>
        <footer className="schemeCardActions">
          <button className="button buttonSecondary" type="button" onClick={() => setEvidenceOpen(true)}><BookOpen size={16} />Why this?</button>
          <Link className="button buttonGhost" href={`/schemes/${scheme.id}`}><FileText size={16} />Details</Link>
          <button className="iconButton listenButton" type="button" onClick={toggleSpeech} aria-label={speaking ? `Stop reading ${scheme.name}` : `Listen to ${scheme.name}`}>
            {speaking ? <Pause size={18} /> : <Headphones size={18} />}
          </button>
          <Link className="cardArrow" href={`/schemes/${scheme.id}`} aria-label={`Open ${scheme.name}`}><ArrowRight size={19} /></Link>
        </footer>
      </article>
      <EvidenceDrawer scheme={scheme} open={evidenceOpen} onClose={() => setEvidenceOpen(false)} />
    </>
  );
}
