"use client";

import Link from "next/link";

import { useLocale } from "@/components/locale-provider";
import { Logo } from "@/components/logo";

export function SiteFooter() {
  const { t } = useLocale();
  return (
    <footer className="siteFooter">
      <div className="footerInner">
        <div><Logo /><p>{t("footerTagline")}</p></div>
        <nav aria-label={t("mobileNav")}><Link href="/assistant">{t("assistant")}</Link><Link href="/privacy">{t("privacy")}</Link><Link href="/demo/evaluation">{t("evaluation")}</Link></nav>
        <p className="footerDisclaimer">{t("footerDisclaimer")}</p>
      </div>
    </footer>
  );
}
