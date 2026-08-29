import { Compass } from "lucide-react";
import Link from "next/link";

import { AppHeader } from "@/components/app-header";

export default function NotFound() {
  return <div className="siteShell"><AppHeader /><main id="main-content" className="fullPageState"><Compass size={30} /><span className="eyebrow">404 · Path not found</span><h1>This route doesn’t lead to a reviewed result.</h1><p>Return to the assistant and continue your conversation.</p><Link className="button buttonPrimary" href="/assistant">Open assistant</Link></main></div>;
}
