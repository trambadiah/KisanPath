import { Menu } from "lucide-react";
import Link from "next/link";

import { LanguageSwitcher } from "@/components/language-switcher";
import { Logo } from "@/components/logo";

export function AppHeader({ variant = "default" }: { variant?: "default" | "assistant" }) {
  return (
    <header className={`appHeader ${variant === "assistant" ? "assistantHeader" : ""}`}>
      <div className="headerInner">
        <Logo />
        <nav className="desktopNav" aria-label="Primary navigation">
          <Link href="/assistant">Assistant</Link>
          <Link href="/schemes">Recommendations</Link>
          <Link href="/demo/evaluation">Evaluation</Link>
        </nav>
        <div className="headerActions">
          <LanguageSwitcher />
          {variant === "default" && (
            <Link className="button buttonSmall buttonPrimary headerCta" href="/assistant">
              Try KisanPath
            </Link>
          )}
          <details className="mobileMenu">
            <summary aria-label="Open navigation">
              <Menu size={21} aria-hidden="true" />
            </summary>
            <nav aria-label="Mobile navigation">
              <Link href="/assistant">Assistant</Link>
              <Link href="/schemes">Recommendations</Link>
              <Link href="/demo/evaluation">Evaluation</Link>
              <Link href="/privacy">Privacy & safety</Link>
            </nav>
          </details>
        </div>
      </div>
    </header>
  );
}
