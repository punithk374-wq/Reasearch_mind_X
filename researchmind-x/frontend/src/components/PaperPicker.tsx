import { Link } from "react-router-dom";
import type { Paper } from "../api";
import { domainLabel } from "../paperDomains";
import PaperBrowser from "./PaperBrowser";
import { selectionReason } from "../paperLibrary";

export default function PaperPicker({ papers, selected, onToggle, disabled, sameDomain = false }: {
  papers: Paper[]; selected: number[]; onToggle: (id: number) => void;
  disabled: boolean; sameDomain?: boolean;
}) {
  const firstDomain = papers.find(p => p.id === selected[0])?.domain;
  return <div className="space-y-4 mb-5">
    {sameDomain && <p className="text-sm text-slate-300">Choose 2–5 papers with the same assigned domain. <Link to="/" className="text-emerald-300 underline">Assign or correct domains in My Papers</Link>. Domain labels describe the primary application area; they do not guarantee identical research topics.</p>}
    <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-3">
      <p className="text-sm text-slate-300 mb-2">Selected {selected.length} / 5 · selections stay when you search or change pages</p>
      {selected.length === 0 ? <p className="text-sm text-slate-400">Choose papers below.</p> : <div className="flex flex-wrap gap-2">
        {selected.map(id => <button key={id} disabled={disabled} onClick={() => onToggle(id)}
          className="text-left text-sm rounded-lg border border-emerald-700 bg-emerald-950 px-3 py-2 disabled:opacity-50"
          aria-label={`Remove ${papers.find(p => p.id === id)?.title ?? id}`}>
          {papers.find(p => p.id === id)?.title ?? `Paper ${id}`} <span aria-hidden="true">×</span>
        </button>)}
      </div>}
    </div>
    <PaperBrowser papers={papers} renderPaper={p => {
      const active = selected.includes(p.id);
      const restriction = selectionReason(p, papers, selected, sameDomain);
      const reason = restriction === "unassigned" ? "Assign a domain in My Papers" :
        restriction === "different_domain" ? `Choose ${domainLabel(firstDomain ?? null)} papers` :
        restriction === "limit" ? "Five-paper limit reached" : "";
      return <button type="button" aria-pressed={active} disabled={disabled || (!active && !!reason)}
        onClick={() => onToggle(p.id)}
        className={`w-full min-h-36 text-left rounded-xl border p-4 transition-colors disabled:opacity-50 ${active ? "border-emerald-400 bg-emerald-500/10" : "border-slate-700 bg-slate-800 hover:border-slate-400"}`}>
        <span className="flex justify-between gap-2 text-xs mb-3 text-slate-300"><span>{domainLabel(p.domain)}</span><span>{active ? "✓ Selected" : "Select"}</span></span>
        <span className="block text-sm font-medium break-words">{p.title}</span>
        <span className="block mt-3 text-xs text-slate-300">{p.page_count} pages{reason && !active ? ` · ${reason}` : ""}</span>
      </button>;
    }} />
  </div>;
}
