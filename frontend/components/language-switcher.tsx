"use client";

import { Languages } from "lucide-react";
import { useState } from "react";

import type { LanguageCode } from "@/lib/contracts";
import { languageNames } from "@/lib/i18n";

export function LanguageSwitcher({ compact = false }: { compact?: boolean }) {
  const [language, setLanguage] = useState<LanguageCode>("gu");

  function update(value: LanguageCode) {
    setLanguage(value);
    document.documentElement.lang = value;
    window.localStorage.setItem("kisanpath-language", value);
    window.dispatchEvent(new CustomEvent("kisanpath-language", { detail: value }));
  }

  return (
    <label className="languageControl">
      <Languages size={17} aria-hidden="true" />
      <span className="srOnly">Language</span>
      <select
        aria-label="Choose language"
        value={language}
        onChange={(event) => update(event.target.value as LanguageCode)}
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
