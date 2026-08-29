import { Database, GitCompareArrows } from "lucide-react";
import type { Metadata } from "next";

import { AppHeader } from "@/components/app-header";
import { EvaluationExplorer } from "@/components/evaluation-explorer";
import { createKisanPathClient } from "@/lib/client";

export const metadata: Metadata = { title: "Evaluation demo" };

export default async function EvaluationPage() {
  const report = await createKisanPathClient().getEvaluationReport();
  return (
    <div className="evaluationShell"><AppHeader /><main id="main-content" className="evaluationPage sectionShell">
      <header className="evaluationHero"><div><span className="eyebrow technical"><GitCompareArrows size={13} />Baseline vs final workflow</span><h1>Measured safety,<br />not demo-day intuition.</h1><p>KisanPath runs the baseline and final system against the same frozen synthetic cases. The result stays reproducible and inspectable.</p></div><div className="datasetStamp"><Database size={19} /><div><small>Dataset</small><strong>{report.datasetVersion}</strong><span>{report.generatedAt}</span></div></div></header>
      <div className="evaluationNotice"><span>Evaluation snapshot</span><p>Seed metrics demonstrate the reporting interface and are not a claim about production performance.</p><strong>{report.syntheticOnly ? "Synthetic cases only" : "Mixed dataset"}</strong></div>
      <EvaluationExplorer report={report} />
    </main></div>
  );
}
