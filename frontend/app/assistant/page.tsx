import type { Metadata } from "next";

import { AppHeader } from "@/components/app-header";
import { AssistantExperience } from "@/components/assistant-experience";

export const metadata: Metadata = { title: "Voice assistant" };

export default function AssistantPage() {
  return <div className="assistantShell"><AppHeader variant="assistant" /><div id="main-content"><AssistantExperience /></div></div>;
}
