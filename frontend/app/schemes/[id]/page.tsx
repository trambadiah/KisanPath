import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { AppHeader } from "@/components/app-header";
import { SchemeDetail } from "@/components/scheme-detail";
import { createKisanPathClient, KisanPathApiError } from "@/lib/client";

export const metadata: Metadata = { title: "Scheme evidence" };

export default async function SchemeDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let scheme;
  try { scheme = await createKisanPathClient().getScheme(id); } catch (error) { if (error instanceof KisanPathApiError && error.code === "SCHEME_NOT_FOUND") notFound(); throw error; }
  return (
    <div className="siteShell"><AppHeader /><SchemeDetail scheme={scheme} /></div>
  );
}
