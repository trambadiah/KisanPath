import { ArrowLeft, BookOpenCheck, SlidersHorizontal, Sparkles } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";

import { AppHeader } from "@/components/app-header";
import { T } from "@/components/locale-provider";
import { SchemeCard } from "@/components/scheme-card";
import { SiteFooter } from "@/components/site-footer";
import { EmptyState } from "@/components/state-panels";
import { createKisanPathClient } from "@/lib/client";

export const metadata: Metadata = { title: "Scheme recommendations" };

export default async function SchemesPage() {
  const schemes = await createKisanPathClient().listRecommendations("demo-conversation-001");
  return (
    <div className="siteShell"><AppHeader /><main id="main-content" className="resultsPage sectionShell">
      <Link className="backLink" href="/assistant"><ArrowLeft size={15} /><T id="backConversation" /></Link>
      <header className="resultsHeader"><div><span className="eyebrow"><Sparkles size={13} /><T id="reviewedProfile" /></span><h1><T id="matches" values={{ count: schemes.length }} /></h1><p><T id="resultsGuidance" /></p></div><div className="resultsMeta"><span><BookOpenCheck size={17} /><T id="reviewedSources" values={{ count: schemes.reduce((sum, scheme) => sum + scheme.sources.length, 0) }} /></span><Link className="button buttonSecondary buttonSmall" href="/assistant"><SlidersHorizontal size={15} /><T id="refineProfile" /></Link></div></header>
      <div className="demoBanner"><strong><T id="demoCorpus" /></strong><span><T id="demoCorpusBody" /></span></div>
      <section className="recommendationList">{schemes.length ? schemes.map((scheme, index) => <SchemeCard key={scheme.id} scheme={scheme} featured={index === 0} />) : <EmptyState />}</section>
    </main><SiteFooter /></div>
  );
}
