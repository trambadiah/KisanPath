import { ArrowLeft, BookOpenCheck, CalendarCheck, FileCheck2, MapPin, ShieldCheck } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { AppHeader } from "@/components/app-header";
import { EligibilityStatusBadge, RuleResultIcon } from "@/components/status-badge";
import { createKisanPathClient, KisanPathApiError } from "@/lib/client";

export const metadata: Metadata = { title: "Scheme evidence" };

export default async function SchemeDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let scheme;
  try { scheme = await createKisanPathClient().getScheme(id); } catch (error) { if (error instanceof KisanPathApiError && error.code === "SCHEME_NOT_FOUND") notFound(); throw error; }
  return (
    <div className="siteShell"><AppHeader /><main id="main-content" className="detailPage sectionShell">
      <Link className="backLink" href="/schemes"><ArrowLeft size={15} />All recommendations</Link>
      <header className="detailHero"><div><span className="eyebrow"><BookOpenCheck size={13} />Evidence-backed detail</span><h1>{scheme.name}</h1><p>{scheme.benefitSummary}</p></div><EligibilityStatusBadge status={scheme.status} /></header>
      <div className="demoNotice wide"><BookOpenCheck size={18} /><p><strong>Reviewed demo data</strong>This is a fictional scheme record for product demonstration, not an active government benefit.</p></div>
      <div className="detailGrid">
        <div className="detailMain">
          <section className="detailSection"><span className="sectionNumber">01</span><div><h2>Why it matched</h2><p className="detailLead">{scheme.fitReason}</p><div className="nextStepCallout"><strong>Your next step</strong><p>{scheme.nextAction}</p></div></div></section>
          <section className="detailSection"><span className="sectionNumber">02</span><div><h2>Eligibility conditions</h2><ul className="ruleList detailRules">{scheme.rules.map((rule) => <li key={rule.id}><RuleResultIcon result={rule.result} /><div><strong>{rule.label}</strong><p>{rule.explanation}</p><small>Derived from {rule.sourceIds.join(", ")}</small></div></li>)}</ul></div></section>
          <section className="detailSection"><span className="sectionNumber">03</span><div><h2>Document readiness</h2><ul className="documentList">{scheme.documents.map((document) => <li key={document.id}><FileCheck2 size={18} /><div><strong>{document.label}</strong><p>{document.detail}</p></div><span className={`documentState document-${document.status}`}>{document.status}</span></li>)}</ul></div></section>
        </div>
        <aside className="evidenceRail"><div className="evidenceRailHeader"><ShieldCheck size={20} /><div><strong>Source provenance</strong><span>{scheme.sources.length} approved references</span></div></div>{scheme.sources.map((source) => <article className="sourceCard" key={source.id}><div className="sourceCardTop"><span>{source.id}</span><span><CalendarCheck size={13} />{source.reviewedAt}</span></div><h3>{source.title}</h3><p className="sourcePublisher"><MapPin size={14} />{source.publisher}</p><span className="sourceLocator">{source.locator}</span><blockquote>“{source.excerpt}”</blockquote></article>)}</aside>
      </div>
    </main></div>
  );
}
