import { EyeOff, LockKeyhole, ShieldCheck } from "lucide-react";
import type { Metadata } from "next";

import { AppHeader } from "@/components/app-header";
import { SiteFooter } from "@/components/site-footer";

export const metadata: Metadata = { title: "Privacy and safety" };

export default function PrivacyPage() {
  return <div className="siteShell"><AppHeader /><main id="main-content" className="privacyPage sectionShell"><span className="eyebrow"><ShieldCheck size={13} />Clear by design</span><h1>Privacy and safety,<br />in plain language.</h1><p className="privacyLead">KisanPath only needs facts relevant to scheme discovery. Do not share Aadhaar numbers, bank credentials, or unrelated personal information.</p><div className="privacyGrid"><article><LockKeyhole size={23} /><h2>Minimum necessary facts</h2><p>Farm location, land area, crop, tenure, and the kind of support you need may affect reviewed conditions.</p></article><article><EyeOff size={23} /><h2>No hidden reasoning</h2><p>We keep operational audit records—sources, rule results, and state changes—not private chain-of-thought.</p></article><article><ShieldCheck size={23} /><h2>Guidance, never approval</h2><p>The responsible authority makes the final decision. KisanPath does not submit applications or take financial action.</p></article></div></main><SiteFooter /></div>;
}
