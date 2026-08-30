"use client";

import { Languages } from "lucide-react";

import { useLocale } from "@/components/locale-provider";
import type { LanguageCode } from "@/lib/contracts";
import { languageNames } from "@/lib/i18n";

export function LanguageSwitcher({ compact = false }: { compact?: boolean }) {
  const { language, setLanguage, t } = useLocale();

  return (
    <label className="languageControl">
      <Languages size={17} aria-hidden="true" />
      <span className="srOnly">{t("language")}</span>
      <select
        aria-label={t("chooseLanguage")}
        value={language}
        onChange={(event) => setLanguage(event.target.value as LanguageCode)}
      >
        {(Object.keys(languageNames) as LanguageCode[]).map((code) => (
          <option key={code} value={code}>
            {compact ? code.toUpperCase() : languageNames[code]}
          </option>
        ))}
      </select>
    </label>
  );
}
