"use client";

import { RefreshCw, TriangleAlert } from "lucide-react";
import { useEffect } from "react";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => { console.error("KisanPath UI error", { name: error.name, digest: error.digest }); }, [error]);
  return <main className="fullPageState" role="alert"><TriangleAlert size={30} /><span className="eyebrow warm">Something went wrong</span><h1>We couldn’t load this view.</h1><p>No profile facts were changed. Retry the safe request when you’re ready.</p><button className="button buttonPrimary" type="button" onClick={reset}><RefreshCw size={16} />Try again</button></main>;
}
