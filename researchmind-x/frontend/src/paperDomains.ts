export const DOMAINS = [
  ["computing", "Computer science & AI"],
  ["medicine", "Medicine & healthcare"],
  ["agriculture", "Agriculture & food science"],
  ["environment", "Environment & climate"],
  ["civil_engineering", "Civil engineering & construction"],
  ["engineering", "Other engineering"],
  ["natural_sciences", "Natural sciences"],
  ["business", "Business & economics"],
  ["education", "Education"],
  ["social_sciences", "Social sciences"],
  ["humanities", "Humanities"],
] as const;

export const domainLabel = (domain: string | null) =>
  DOMAINS.find(([key]) => key === domain)?.[1] ?? "Unassigned";
