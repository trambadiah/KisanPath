import { ArrowRight, AudioLines, BookOpenCheck, Check, LockKeyhole, MessageSquareText, SearchCheck, ShieldCheck, Sparkles } from "lucide-react";
import Link from "next/link";

import { AppHeader } from "@/components/app-header";
import { T } from "@/components/locale-provider";
import { SchemeCard } from "@/components/scheme-card";
import { SiteFooter } from "@/components/site-footer";
import { createKisanPathClient } from "@/lib/client";

export default async function LandingPage() {
  const [sample] = await createKisanPathClient().listRecommendations("demo-conversation-001");
  return (
    <div className="siteShell">
      <AppHeader />
      <main id="main-content">
        <section className="hero sectionShell">
          <div className="heroTexture" aria-hidden="true" />
          <div className="heroCopy">
            <span className="eyebrow"><Sparkles size={13} />ગુજરાતી · हिन्दी · English</span>
            <h1><T id="heroTitle" /></h1>
            <p><T id="heroBody" /></p>
            <div className="heroActions">
              <Link className="button buttonPrimary buttonLarge" href="/assistant"><AudioLines size={19} /><T id="startVoice" /> <ArrowRight size={17} /></Link>
              <Link className="button buttonSecondary buttonLarge" href="/assistant#message-input"><MessageSquareText size={18} /><T id="typeInstead" /></Link>
            </div>
            <div className="heroTrust"><span><ShieldCheck size={16} /><T id="reviewedEvidence" /></span><span><LockKeyhole size={16} /><T id="noIds" /></span></div>
          </div>
          <div className="heroOrbComposition">
            <div className="ambientRing ringOne" /><div className="ambientRing ringTwo" />
            <div className="heroOrb"><span className="heroOrbLines" /><AudioLines size={42} strokeWidth={1.3} /></div>
            <div className="heroTranscript"><span className="transcriptWave" aria-hidden="true"><i /><i /><i /><i /><i /></span><div><small><T id="youSaid" /></small><p>“<T id="demoUtterance" />”</p></div><Check size={16} /></div>
            <div className="heroConfirmation"><small><T id="profileFact" /></small><strong><T id="demoLocation" /></strong><span><Check size={13} /><T id="confirmed" /></span></div>
          </div>
        </section>

        <section className="processSection sectionShell" aria-labelledby="process-title">
          <div className="sectionIntro"><span className="eyebrow"><T id="clearerPath" /></span><h2 id="process-title"><T id="processTitle" /></h2><p><T id="processBody" /></p></div>
          <ol className="processSteps">
            <li><span>01</span><AudioLines size={23} /><div><h3><T id="speakTitle" /></h3><p><T id="speakBody" /></p></div></li>
            <li><span>02</span><SearchCheck size={23} /><div><h3><T id="confirmTitle" /></h3><p><T id="confirmBody" /></p></div></li>
            <li><span>03</span><BookOpenCheck size={23} /><div><h3><T id="reasonTitle" /></h3><p><T id="reasonBody" /></p></div></li>
          </ol>
        </section>

        <section className="sampleSection sectionShell" aria-labelledby="sample-title">
          <div className="sampleCopy"><span className="eyebrow"><T id="inspectEyebrow" /></span><h2 id="sample-title"><T id="inspectTitle" /></h2><p><T id="inspectBody" /></p><Link className="textLink" href="/schemes"><T id="exploreDemo" /> <ArrowRight size={15} /></Link></div>
          <SchemeCard scheme={sample} featured />
        </section>

        <section className="trustSection sectionShell">
          <div><span className="trustIcon"><ShieldCheck size={24} /></span><h2><T id="guidanceTitle" /></h2></div>
          <p><T id="guidanceBody" /></p>
          <ul><li><Check size={15} /><T id="unknownStays" /></li><li><Check size={15} /><T id="sourcesVisible" /></li><li><Check size={15} /><T id="noApplications" /></li></ul>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}
