"use client";

import { ArrowLeft, BookOpenCheck, CalendarCheck, FileCheck2, MapPin, ShieldCheck } from "lucide-react";
import Link from "next/link";

import { useLocale } from "@/components/locale-provider";
import { EligibilityStatusBadge, RuleResultIcon } from "@/components/status-badge";
import type { SchemeRecommendation } from "@/lib/contracts";
import { localizeScheme } from "@/lib/scheme-i18n";

export function SchemeDetail({ scheme }: { scheme: SchemeRecommendation }) {
  const { language, t } = useLocale();
  const localized = localizeScheme(scheme, language);
  return <main id="main-content" className="detailPage sectionShell">
    <Link className="backLink" href="/schemes"><ArrowLeft size={15} />{t("allRecommendations")}</Link>
    <header className="detailHero"><div><span className="eyebrow"><BookOpenCheck size={13} />{t("evidenceBacked")}</span><h1>{localized.name}</h1><p>{localized.benefitSummary}</p></div><EligibilityStatusBadge status={localized.status} /></header>
    <div className="demoNotice wide"><BookOpenCheck size={18} /><p><strong>{t("reviewedDemo")}</strong>{t("detailDemoBody")}</p></div>
    <div className="detailGrid">
      <div className="detailMain">
        <section className="detailSection"><span className="sectionNumber">01</span><div><h2>{t("whyMatched")}</h2><p className="detailLead">{localized.fitReason}</p><div className="nextStepCallout"><strong>{t("yourNextStep")}</strong><p>{localized.nextAction}</p></div></div></section>
        <section className="detailSection"><span className="sectionNumber">02</span><div><h2>{t("eligibilityConditions")}</h2><ul className="ruleList detailRules">{localized.rules.map((rule) => <li key={rule.id}><RuleResultIcon result={rule.result} /><div><strong>{rule.label}</strong><p>{rule.explanation}</p><small>{t("derivedFrom", { sources: rule.sourceIds.join(", ") })}</small></div></li>)}</ul></div></section>
        <section className="detailSection"><span className="sectionNumber">03</span><div><h2>{t("documentReadiness")}</h2><ul className="documentList">{localized.documents.map((document) => <li key={document.id}><FileCheck2 size={18} /><div><strong>{document.label}</strong><p>{document.detail}</p></div><span className={`documentState document-${document.status}`}>{t(document.status)}</span></li>)}</ul></div></section>
      </div>
      <aside className="evidenceRail"><div className="evidenceRailHeader"><ShieldCheck size={20} /><div><strong>{t("sourceProvenance")}</strong><span>{t("approvedReferences", { count: localized.sources.length })}</span></div></div>{localized.sources.map((source) => <article className="sourceCard" key={source.id}><div className="sourceCardTop"><span>{source.id}</span><span><CalendarCheck size={13} />{source.reviewedAt}</span></div><h3>{source.title}</h3><p className="sourcePublisher"><MapPin size={14} />{source.publisher}</p><span className="sourceLocator">{source.locator}</span><blockquote>“{source.excerpt}”</blockquote></article>)}</aside>
    </div>
  </main>;
}
