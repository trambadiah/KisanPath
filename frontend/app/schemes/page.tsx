import { ArrowLeft, BookOpenCheck, SlidersHorizontal, Sparkles } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";

import { AppHeader } from "@/components/app-header";
import { SchemeCard } from "@/components/scheme-card";
import { SiteFooter } from "@/components/site-footer";
import { EmptyState } from "@/components/state-panels";
import { createKisanPathClient } from "@/lib/client";

export const metadata: Metadata = { title: "Scheme recommendations" };

export default async function SchemesPage() {
  const schemes = await createKisanPathClient().listRecommendations("demo-conversation-001");
  return (
    <div className="siteShell"><AppHeader /><main id="main-content" className="resultsPage sectionShell">
      <Link className="backLink" href="/assistant"><ArrowLeft size={15} />Back to conversation</Link>
      <header className="resultsHeader"><div><span className="eyebrow"><Sparkles size={13} />Reviewed against your confirmed profile</span><h1>{schemes.length} schemes may match your situation</h1><p>These are guidance results, not official approvals. Open any card to inspect the exact conditions and evidence.</p></div><div className="resultsMeta"><span><BookOpenCheck size={17} />{schemes.reduce((sum, scheme) => sum + scheme.sources.length, 0)} reviewed sources</span><Link className="button buttonSecondary buttonSmall" href="/assistant"><SlidersHorizontal size={15} />Refine profile</Link></div></header>
      <div className="demoBanner"><strong>Demo corpus</strong><span>These fictional schemes use reviewed synthetic policy records. No real farmer data is shown.</span></div>
      <section className="recommendationList" aria-label="Scheme recommendations">{schemes.length ? schemes.map((scheme, index) => <SchemeCard key={scheme.id} scheme={scheme} featured={index === 0} />) : <EmptyState />}</section>
    </main><SiteFooter /></div>
  );
}
