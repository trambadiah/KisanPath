"use client";

import { ArrowDown, ArrowUp, Check, ChevronRight, FlaskConical, ShieldCheck } from "lucide-react";
import { useMemo, useState } from "react";

import { EligibilityStatusBadge } from "@/components/status-badge";
import { useLocale } from "@/components/locale-provider";
import type { EvaluationReport, LanguageCode } from "@/lib/contracts";

export function EvaluationExplorer({ report }: { report: EvaluationReport }) {
  const { t } = useLocale();
  const [language, setLanguage] = useState<LanguageCode | "all">("all");
  const [selectedId, setSelectedId] = useState(report.cases[0]?.id ?? "");
  const cases = useMemo(
    () => report.cases.filter((item) => language === "all" || item.language === language),
    [language, report.cases],
  );
  const selected = cases.find((item) => item.id === selectedId) ?? cases[0];

  return (
    <>
      <section className="metricGrid" aria-label={t("evalMetrics")}>
        {report.metrics.map((metric, index) => {
          const improvement = metric.lowerIsBetter ? metric.baseline - metric.final : metric.final - metric.baseline;
          const Arrow = improvement >= 0 ? ArrowUp : ArrowDown;
          return (
            <article className={`metricCard ${index === 0 ? "metricPrimary" : ""}`} key={metric.id}>
              <div className="metricHeader"><span>{metric.label}</span><span className="metricDelta"><Arrow size={13} />{Math.abs(improvement).toFixed(1)} pts</span></div>
              <div className="metricValues"><div><small>{t("baseline")}</small><strong>{metric.baseline}{metric.unit}</strong></div><span /><div><small>{t("kisanPath")}</small><strong>{metric.final}{metric.unit}</strong></div></div>
              <p>{metric.description}</p>
            </article>
          );
        })}
      </section>

      <section className="safetyStrip">
        <ShieldCheck size={23} aria-hidden="true" />
        <div><strong>{t("safetyTitle")}</strong><p>{t("safetyBody")}</p></div>
        <span>{t("safetyPassed")}</span>
      </section>

      <section className="caseExplorer" aria-labelledby="case-explorer-title">
        <header className="caseExplorerHeader">
          <div><span className="eyebrow"><FlaskConical size={13} />{t("frozenDataset")}</span><h2 id="case-explorer-title">{t("caseExplorer")}</h2></div>
          <div className="filterPills" aria-label={t("filterLanguage")}>
            {(["all", "gu", "hi", "en"] as const).map((value) => <button type="button" className={language === value ? "active" : ""} aria-pressed={language === value} onClick={() => setLanguage(value)} key={value}>{value === "all" ? t("all") : value.toUpperCase()}</button>)}
          </div>
        </header>
        <div className="caseExplorerBody">
          <div className="caseList" role="list" aria-label={t("evalCases")}>
            {cases.map((item) => (
              <button className={selected?.id === item.id ? "selected" : ""} type="button" onClick={() => setSelectedId(item.id)} key={item.id} role="listitem">
                <span className="casePass"><Check size={14} aria-hidden="true" /></span>
                <span><strong>{item.title}</strong><small>{item.id} · {item.language.toUpperCase()}</small></span>
                <ChevronRight size={16} aria-hidden="true" />
              </button>
            ))}
          </div>
          {selected && (
            <article className="caseDetail">
              <span className="eyebrow">{t("sanitizedInput")}</span>
              <blockquote lang={selected.language}>“{selected.input}”</blockquote>
              <div className="caseOutcomes"><div><small>{t("expected")}</small><EligibilityStatusBadge status={selected.expected} /></div><div><small>{t("actual")}</small><EligibilityStatusBadge status={selected.actual} /></div></div>
              <div className="auditNote"><strong>{t("auditNote")}</strong><p>{selected.note}</p></div>
              <div className="traceLine"><span /><span /><span /><span /><span /></div>
              <p className="traceCaption">{t("trace")}</p>
            </article>
          )}
        </div>
      </section>
    </>
  );
}
