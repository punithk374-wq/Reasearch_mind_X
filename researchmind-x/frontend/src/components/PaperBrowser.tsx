import { useId, useState } from "react";
import type { ReactNode } from "react";
import type { Paper } from "../api";
import { DOMAINS } from "../paperDomains";
import { filterPapers } from "../paperLibrary";

const PAGE_SIZE = 12;
const control = "w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-400";

export default function PaperBrowser({ papers, renderPaper }: {
  papers: Paper[]; renderPaper: (paper: Paper) => ReactNode;
}) {
  const id = useId();
  const [query, setQuery] = useState("");
  const [domain, setDomain] = useState("");
  const [sort, setSort] = useState("newest");
  const [page, setPage] = useState(1);
  const filtered = filterPapers(papers, query, domain, sort);
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const current = Math.min(page, pages);
  return <div className="space-y-4">
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <div className="sm:col-span-2">
        <label className="block text-sm text-slate-300 mb-1" htmlFor={`${id}-search`}>Search papers</label>
        <input id={`${id}-search`} type="search" value={query} placeholder="Search by paper title or filename…"
          onChange={e => { setQuery(e.target.value); setPage(1); }} className={control} />
      </div>
      <div>
        <label className="block text-sm text-slate-300 mb-1" htmlFor={`${id}-domain`}>Domain filter</label>
        <select id={`${id}-domain`} className={control} value={domain} onChange={e => { setDomain(e.target.value); setPage(1); }}>
          <option value="">All domains</option><option value="unassigned">Unassigned</option>
          {DOMAINS.map(([key, label]) => <option key={key} value={key}>{label}</option>)}
        </select>
      </div>
      <div>
        <label className="block text-sm text-slate-300 mb-1" htmlFor={`${id}-sort`}>Sort by</label>
        <select id={`${id}-sort`} className={control} value={sort} onChange={e => { setSort(e.target.value); setPage(1); }}>
          <option value="newest">Newest first</option><option value="title">Title A–Z</option>
        </select>
      </div>
    </div>
    <div className="flex items-center justify-between gap-3 text-sm text-slate-300">
      <p role="status">{filtered.length} of {papers.length} papers{filtered.length > 0 ? ` · showing ${(current - 1) * PAGE_SIZE + 1}–${Math.min(current * PAGE_SIZE, filtered.length)}` : ""}</p>
      {(query || domain) && <button className="text-emerald-300 underline" onClick={() => { setQuery(""); setDomain(""); setPage(1); }}>Clear filters</button>}
    </div>
    {!filtered.length ? <p className="rounded-xl border border-slate-700 p-6 text-slate-300">{papers.length ? "No papers match your search. Try another title or clear the filters." : "No papers available yet."}</p> :
      <ul className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 items-start">
        {filtered.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE).map(p => <li key={p.id} className="min-w-0">{renderPaper(p)}</li>)}
      </ul>}
    {pages > 1 && <nav aria-label="Paper pages" className="flex items-center justify-center gap-4 text-sm">
      <button className="rounded bg-slate-700 px-4 py-2 disabled:opacity-40" disabled={current === 1} onClick={() => setPage(current - 1)}>Previous</button>
      <span>Page {current} of {pages}</span>
      <button className="rounded bg-slate-700 px-4 py-2 disabled:opacity-40" disabled={current === pages} onClick={() => setPage(current + 1)}>Next</button>
    </nav>}
  </div>;
}
