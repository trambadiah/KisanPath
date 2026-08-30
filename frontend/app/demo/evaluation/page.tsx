import { Database, GitCompareArrows } from "lucide-react";
import type { Metadata } from "next";

import { AppHeader } from "@/components/app-header";
import { T } from "@/components/locale-provider";
import { EvaluationExplorer } from "@/components/evaluation-explorer";
import { createKisanPathClient } from "@/lib/client";

export const metadata: Metadata = { title: "Evaluation demo" };

export default async function EvaluationPage() {
  const report = await createKisanPathClient().getEvaluationReport();
  return (
    <div className="evaluationShell"><AppHeader /><main id="main-content" className="evaluationPage sectionShell">
      <header className="evaluationHero"><div><span className="eyebrow technical"><GitCompareArrows size={13} /><T id="evalEyebrow" /></span><h1><T id="evalTitle" /></h1><p><T id="evalBody" /></p></div><div className="datasetStamp"><Database size={19} /><div><small><T id="dataset" /></small><strong>{report.datasetVersion}</strong><span>{report.generatedAt}</span></div></div></header>
      <div className="evaluationNotice"><span><T id="evalSnapshot" /></span><p><T id="evalNotice" /></p><strong><T id={report.syntheticOnly ? "syntheticOnly" : "mixedDataset"} /></strong></div>
      <EvaluationExplorer report={report} />
    </main></div>
  );
}
