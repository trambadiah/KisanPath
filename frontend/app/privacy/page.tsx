import { EyeOff, LockKeyhole, ShieldCheck } from "lucide-react";
import type { Metadata } from "next";

import { AppHeader } from "@/components/app-header";
import { T } from "@/components/locale-provider";
import { SiteFooter } from "@/components/site-footer";

export const metadata: Metadata = { title: "Privacy and safety" };

export default function PrivacyPage() {
  return <div className="siteShell"><AppHeader /><main id="main-content" className="privacyPage sectionShell"><span className="eyebrow"><ShieldCheck size={13} /><T id="privacyEyebrow" /></span><h1><T id="privacyTitle" /></h1><p className="privacyLead"><T id="privacyLead" /></p><div className="privacyGrid"><article><LockKeyhole size={23} /><h2><T id="minimumTitle" /></h2><p><T id="minimumBody" /></p></article><article><EyeOff size={23} /><h2><T id="reasoningTitle" /></h2><p><T id="reasoningBody" /></p></article><article><ShieldCheck size={23} /><h2><T id="neverApproval" /></h2><p><T id="neverApprovalBody" /></p></article></div></main><SiteFooter /></div>;
}
