import { Compass } from "lucide-react";
import Link from "next/link";

import { AppHeader } from "@/components/app-header";
import { T } from "@/components/locale-provider";

export default function NotFound() {
  return <div className="siteShell"><AppHeader /><main id="main-content" className="fullPageState"><Compass size={30} /><span className="eyebrow"><T id="pathMissing" /></span><h1><T id="routeMissing" /></h1><p><T id="routeMissingBody" /></p><Link className="button buttonPrimary" href="/assistant"><T id="openAssistant" /></Link></main></div>;
}
