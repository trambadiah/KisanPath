"use client";

import { Menu } from "lucide-react";
import Link from "next/link";

import { LanguageSwitcher } from "@/components/language-switcher";
import { useLocale } from "@/components/locale-provider";
import { Logo } from "@/components/logo";

export function AppHeader({ variant = "default" }: { variant?: "default" | "assistant" }) {
  const { t } = useLocale();
  return (
    <header className={`appHeader ${variant === "assistant" ? "assistantHeader" : ""}`}>
      <div className="headerInner">
        <Logo />
        <nav className="desktopNav" aria-label={t("primaryNav")}>
          <Link href="/assistant">{t("assistant")}</Link>
          <Link href="/schemes">{t("recommendations")}</Link>
          <Link href="/demo/evaluation">{t("evaluation")}</Link>
        </nav>
        <div className="headerActions">
          <LanguageSwitcher />
          {variant === "default" && (
            <Link className="button buttonSmall buttonPrimary headerCta" href="/assistant">
              {t("tryKisanPath")}
            </Link>
          )}
          <details className="mobileMenu">
            <summary aria-label={t("openNav")}>
              <Menu size={21} aria-hidden="true" />
            </summary>
            <nav aria-label={t("mobileNav")}>
              <Link href="/assistant">{t("assistant")}</Link>
              <Link href="/schemes">{t("recommendations")}</Link>
              <Link href="/demo/evaluation">{t("evaluation")}</Link>
              <Link href="/privacy">{t("privacy")}</Link>
            </nav>
          </details>
        </div>
      </div>
    </header>
  );
}
