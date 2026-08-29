"use client";

import { BookOpenCheck, CalendarCheck, ExternalLink, FileCheck2, MapPin, X } from "lucide-react";
import { useEffect, useRef } from "react";

import { RuleResultIcon } from "@/components/status-badge";
import type { SchemeRecommendation } from "@/lib/contracts";

export function EvidenceDrawer({
  scheme,
  open,
  onClose,
}: {
  scheme: SchemeRecommendation;
  open: boolean;
  onClose: () => void;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={dialogRef}
      className="evidenceDialog"
      aria-labelledby={`evidence-title-${scheme.id}`}
      onClose={onClose}
      onClick={(event) => {
        if (event.target === dialogRef.current) onClose();
      }}
    >
      <div className="evidenceDrawer">
        <header className="drawerHeader">
          <div>
            <span className="eyebrow">Evidence detail</span>
            <h2 id={`evidence-title-${scheme.id}`}>{scheme.name}</h2>
          </div>
          <button className="iconButton" type="button" onClick={onClose} aria-label="Close evidence detail">
            <X size={20} aria-hidden="true" />
          </button>
        </header>

        {scheme.demo && (
          <div className="demoNotice">
            <BookOpenCheck size={18} aria-hidden="true" />
            <p><strong>Reviewed demo data</strong>This fictional record demonstrates provenance. It is not an active government scheme.</p>
          </div>
        )}

        <section className="drawerSection" aria-labelledby="why-heading">
          <h3 id="why-heading">Why this matched</h3>
          <p className="drawerLead">{scheme.fitReason}</p>
        </section>

        <section className="drawerSection" aria-labelledby="conditions-heading">
          <div className="sectionHeadingRow">
            <h3 id="conditions-heading">Published conditions</h3>
            <span>{scheme.conditionsPassed}/{scheme.conditionsTotal} resolved</span>
          </div>
          <ul className="ruleList">
            {scheme.rules.map((rule) => (
              <li key={rule.id}>
                <RuleResultIcon result={rule.result} />
                <div><strong>{rule.label}</strong><p>{rule.explanation}</p><small>Evidence: {rule.sourceIds.join(", ")}</small></div>
              </li>
            ))}
          </ul>
        </section>

        <section className="drawerSection" aria-labelledby="documents-heading">
          <h3 id="documents-heading">Document readiness</h3>
          <ul className="documentList">
            {scheme.documents.map((document) => (
              <li key={document.id}>
                <FileCheck2 size={18} aria-hidden="true" />
                <div><strong>{document.label}</strong><p>{document.detail}</p></div>
                <span className={`documentState document-${document.status}`}>{document.status}</span>
              </li>
            ))}
          </ul>
        </section>

        <section className="drawerSection" aria-labelledby="sources-heading">
          <h3 id="sources-heading">Official source evidence</h3>
          <div className="sourceStack">
            {scheme.sources.map((source) => (
              <article className="sourceCard" key={source.id}>
                <div className="sourceCardTop"><span>{source.id}</span><span><CalendarCheck size={13} />Reviewed {source.reviewedAt}</span></div>
                <h4>{source.title}</h4>
                <p className="sourcePublisher"><MapPin size={14} />{source.publisher} · {source.locator}</p>
                <blockquote>“{source.excerpt}”</blockquote>
                {source.url && <a href={source.url} target="_blank" rel="noreferrer">Open source <ExternalLink size={13} /></a>}
              </article>
            ))}
          </div>
        </section>
      </div>
    </dialog>
  );
}
