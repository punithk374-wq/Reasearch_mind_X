import type { Paper } from "./api";

export function filterPapers(papers: Paper[], query: string, domain: string, sort: string) {
  const needle = query.trim().toLocaleLowerCase();
  return papers.filter(p =>
    (!needle || `${p.title} ${p.filename}`.toLocaleLowerCase().includes(needle)) &&
    (!domain || (domain === "unassigned" ? !p.domain : p.domain === domain))
  ).sort((a, b) => sort === "title" ? a.title.localeCompare(b.title) : b.created_at.localeCompare(a.created_at) || b.id - a.id);
}

export function selectionReason(paper: Paper, papers: Paper[], selected: number[], sameDomain: boolean) {
  const firstDomain = papers.find(p => p.id === selected[0])?.domain;
  if (sameDomain && !paper.domain) return "unassigned";
  if (sameDomain && firstDomain && paper.domain !== firstDomain) return "different_domain";
  if (selected.length >= 5 && !selected.includes(paper.id)) return "limit";
  return "";
}
