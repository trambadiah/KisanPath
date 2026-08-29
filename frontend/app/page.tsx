import { ArrowRight, AudioLines, BookOpenCheck, Check, LockKeyhole, MessageSquareText, SearchCheck, ShieldCheck, Sparkles } from "lucide-react";
import Link from "next/link";

import { AppHeader } from "@/components/app-header";
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
            <h1>Find the schemes<br />meant for <em>your farm.</em></h1>
            <p>Speak naturally. KisanPath checks reviewed conditions, keeps unknowns honest, and shows the evidence behind every recommendation.</p>
            <div className="heroActions">
              <Link className="button buttonPrimary buttonLarge" href="/assistant"><AudioLines size={19} />Start with your voice <ArrowRight size={17} /></Link>
              <Link className="button buttonSecondary buttonLarge" href="/assistant#message-input"><MessageSquareText size={18} />Type instead</Link>
            </div>
            <div className="heroTrust"><span><ShieldCheck size={16} />Reviewed evidence</span><span><LockKeyhole size={16} />No sensitive IDs needed</span></div>
          </div>
          <div className="heroOrbComposition" aria-label="Voice assistant preview">
            <div className="ambientRing ringOne" /><div className="ambientRing ringTwo" />
            <div className="heroOrb"><span className="heroOrbLines" /><AudioLines size={42} strokeWidth={1.3} /></div>
            <div className="heroTranscript"><span className="transcriptWave" aria-hidden="true"><i /><i /><i /><i /><i /></span><div><small>You said</small><p lang="gu">“મારે ટપક સિંચાઈ માટે સહાય જોઈએ છે.”</p></div><Check size={16} /></div>
            <div className="heroConfirmation"><small>Profile fact</small><strong>આણંદ, ગુજરાત</strong><span><Check size={13} />confirmed</span></div>
          </div>
        </section>

        <section className="processSection sectionShell" aria-labelledby="process-title">
          <div className="sectionIntro"><span className="eyebrow">A clearer path</span><h2 id="process-title">Speak. Check. Understand.</h2><p>One calm conversation, with deterministic checks and reviewed evidence working underneath.</p></div>
          <ol className="processSteps">
            <li><span>01</span><AudioLines size={23} /><div><h3>Speak naturally</h3><p>Use Gujarati, Hindi, English, or a comfortable mix.</p></div></li>
            <li><span>02</span><SearchCheck size={23} /><div><h3>Confirm what matters</h3><p>We show uncertain location and land values before using them.</p></div></li>
            <li><span>03</span><BookOpenCheck size={23} /><div><h3>See the reason</h3><p>Every important result maps back to a reviewed condition.</p></div></li>
          </ol>
        </section>

        <section className="sampleSection sectionShell" aria-labelledby="sample-title">
          <div className="sampleCopy"><span className="eyebrow">Not a black box</span><h2 id="sample-title">A recommendation you can inspect.</h2><p>See which facts matched, what is still unknown, which document comes next, and exactly where the condition came from.</p><Link className="textLink" href="/schemes">Explore all demo results <ArrowRight size={15} /></Link></div>
          <SchemeCard scheme={sample} featured />
        </section>

        <section className="trustSection sectionShell">
          <div><span className="trustIcon"><ShieldCheck size={24} /></span><h2>Guidance, not an official approval.</h2></div>
          <p>KisanPath helps you understand reviewed published conditions. The responsible government authority makes the final decision.</p>
          <ul><li><Check size={15} />Unknown stays unknown</li><li><Check size={15} />Sources stay visible</li><li><Check size={15} />No automatic applications</li></ul>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}
