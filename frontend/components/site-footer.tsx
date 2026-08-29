import Link from "next/link";

import { Logo } from "@/components/logo";

export function SiteFooter() {
  return (
    <footer className="siteFooter">
      <div className="footerInner">
        <div><Logo /><p>Evidence-grounded scheme guidance for Indian farmers.</p></div>
        <nav aria-label="Footer navigation"><Link href="/assistant">Assistant</Link><Link href="/privacy">Privacy & safety</Link><Link href="/demo/evaluation">Evaluation</Link></nav>
        <p className="footerDisclaimer">KisanPath provides guidance based on reviewed published conditions. It does not issue official eligibility decisions.</p>
      </div>
    </footer>
  );
}
