"use client";

import { RefreshCw, TriangleAlert } from "lucide-react";
import { useEffect } from "react";
import { useLocale } from "@/components/locale-provider";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const { t } = useLocale();
  useEffect(() => { console.error("KisanPath UI error", { name: error.name, digest: error.digest }); }, [error]);
  return <main className="fullPageState" role="alert"><TriangleAlert size={30} /><span className="eyebrow warm">{t("somethingWrong")}</span><h1>{t("loadFailed")}</h1><p>{t("loadFailedBody")}</p><button className="button buttonPrimary" type="button" onClick={reset}><RefreshCw size={16} />{t("tryAgain")}</button></main>;
}
