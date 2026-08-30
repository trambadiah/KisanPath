"use client";

import { createContext, type ReactNode, useContext, useEffect, useMemo, useState } from "react";
import type { LanguageCode } from "@/lib/contracts";
import { translate, type TranslationKey } from "@/lib/i18n";

type Values = Record<string, string | number>;
type LocaleValue = { language: LanguageCode; setLanguage: (language: LanguageCode) => void; t: (key: TranslationKey, values?: Values) => string };
const LocaleContext = createContext<LocaleValue | null>(null);
const isLanguage = (value: string | null): value is LanguageCode => value === "en" || value === "gu" || value === "hi";

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<LanguageCode>("en");
  useEffect(() => {
    const saved = localStorage.getItem("kisanpath-language");
    const timer = window.setTimeout(() => { if (isLanguage(saved)) setLanguageState(saved); }, 0);
    return () => window.clearTimeout(timer);
  }, []);
  useEffect(() => { document.documentElement.lang = language; }, [language]);
  const value = useMemo<LocaleValue>(() => ({ language, setLanguage(next) { setLanguageState(next); localStorage.setItem("kisanpath-language", next); }, t: (key, values) => translate(language, key, values) }), [language]);
  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale() { const value = useContext(LocaleContext); if (!value) throw new Error("useLocale must be used inside LocaleProvider"); return value; }
export function T({ id, values }: { id: TranslationKey; values?: Values }) { const { t } = useLocale(); return <>{t(id, values)}</>; }
