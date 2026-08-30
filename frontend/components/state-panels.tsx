"use client";

import { CloudOff, Inbox, RefreshCw, TriangleAlert } from "lucide-react";
import { useLocale } from "@/components/locale-provider";

export function LoadingState({ label }: { label?: string }) {
  const { t } = useLocale();
  return (
    <div className="statePanel loadingPanel" role="status">
      <span className="loadingMark" aria-hidden="true"><i /><i /><i /></span>
      <div><strong>{label ?? t("checking")}</strong><p>{t("checkingBody")}</p></div>
    </div>
  );
}

export function EmptyState() {
  const { t } = useLocale();
  return (
    <div className="statePanel centeredState">
      <Inbox size={24} aria-hidden="true" />
      <strong>{t("emptyTitle")}</strong>
      <p>{t("emptyBody")}</p>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  const { t } = useLocale();
  return (
    <div className="statePanel errorPanel" role="alert">
      <TriangleAlert size={22} aria-hidden="true" />
      <div><strong>{t("errorTitle")}</strong><p>{message}</p></div>
      {onRetry && <button className="button buttonSmall buttonSecondary" type="button" onClick={onRetry}><RefreshCw size={15} />{t("retry")}</button>}
    </div>
  );
}

export function OfflineNotice() {
  const { t } = useLocale();
  return (
    <div className="offlineNotice" role="status">
      <CloudOff size={16} aria-hidden="true" />
      {t("offline")}
    </div>
  );
}
