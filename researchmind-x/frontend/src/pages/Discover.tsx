import { useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { isAxiosError } from "axios";
import api from "../api";
import type { DiscoveredPaper } from "../api";
import NavBar from "../components/NavBar";

type SortKey = "relevance" | "cited" | "newest";

interface ImportState {
  status: "importing" | "done" | "error";
  message?: string;
}

const YEAR_OPTIONS = [
  { value: "", label: "Any year" },
  { value: "2024", label: "Since 2024" },
  { value: "2022", label: "Since 2022" },
  { value: "2020", label: "Since 2020" },
  { value: "2015", label: "Since 2015" },
];

export default function Discover() {
  const [query, setQuery] = useState("");
  const [yearFrom, setYearFrom] = useState("");
  const [openOnly, setOpenOnly] = useState(true);
  const [source, setSource] = useState("openalex");
  const [sort, setSort] = useState<SortKey>("relevance");
  const [results, setResults] = useState<DiscoveredPaper[]>([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [imports, setImports] = useState<Record<string, ImportState>>({});

  const handleSearch = async (e: FormEvent) => {
    e.preventDefault();
    if (query.trim().length < 3) {
      setError("Enter at least 3 characters to search.");
      return;
    }

    setError("");
    setLoading(true);
    try {
      const res = await api.post<DiscoveredPaper[]>("/api/discover/search", {
        query: query.trim(),
        per_page: 15,
        year_from: yearFrom ? Number(yearFrom) : null,
        open_access_only: openOnly,
        source,

      });
      setResults(res.data);
      setSearched(true);
      setImports({});
    } catch (err) {
      if (isAxiosError(err) && typeof err.response?.data?.detail === "string") {
        setError(err.response.data.detail);
      } else {
        setError("Search failed. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleImport = async (paper: DiscoveredPaper) => {
    setImports((prev) => ({
      ...prev,
      [paper.source_id]: { status: "importing" },
    }));
    try {
      await api.post("/api/discover/import", {
        source: paper.source,
        source_id: paper.source_id,
      });
      setImports((prev) => ({
        ...prev,
        [paper.source_id]: { status: "done", message: "Added to your library" },
      }));
    } catch (err) {
      if (isAxiosError(err) && err.response?.status === 409) {
        setImports((prev) => ({
          ...prev,
          [paper.source_id]: {
            status: "done",
            message: "Already in your library",
          },
        }));
        return;
      }
      const detail =
        isAxiosError(err) && typeof err.response?.data?.detail === "string"
          ? err.response.data.detail
          : "Import failed. Please try again.";
      setImports((prev) => ({
        ...prev,
        [paper.source_id]: { status: "error", message: detail },
      }));
    }
  };

  const sorted = [...results].sort((a, b) => {
    if (sort === "cited") return b.cited_by_count - a.cited_by_count;
    if (sort === "newest") return (b.year ?? 0) - (a.year ?? 0);
    return 0; // relevance: keep the order the source returned
  });

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      <NavBar />

      <main className="max-w-4xl mx-auto p-6 space-y-6">
        <section>
          <h2 className="text-lg font-semibold mb-1">Discover papers</h2>
          <p className="text-slate-400 text-sm mb-4">
            Search the scholarly literature by topic, then import open-access
            papers straight into your library. Imported papers go through the
            same processing as uploads, so you can search, compare and analyse
            them right away.
          </p>

          <form onSubmit={handleSearch} className="space-y-3">
            <div className="flex gap-2">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="e.g. retrieval augmented generation evaluation"
                className="flex-1 p-3 rounded bg-slate-800 text-white placeholder-slate-500 outline-none focus:ring-2 focus:ring-emerald-500"
              />
              <button
                type="submit"
                disabled={loading}
                className="px-5 rounded bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-white font-semibold"
              >
                {loading ? "Searching..." : "Search"}
              </button>
            </div>

            <div className="flex flex-wrap items-center gap-4 text-sm text-slate-300">
            <select
                value={source}
                onChange={(e) => setSource(e.target.value)}
                className="bg-slate-800 rounded px-3 py-2 outline-none"
              >
                <option value="openalex">OpenAlex</option>
                <option value="semanticscholar">Semantic Scholar</option>
                <option value="both">Both (merged)</option>
              </select>
              <select
                value={yearFrom}
                onChange={(e) => setYearFrom(e.target.value)}
                className="bg-slate-800 rounded px-3 py-2 outline-none"
              >
                {YEAR_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>

              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={openOnly}
                  onChange={(e) => setOpenOnly(e.target.checked)}
                />
                Open access only
              </label>
            </div>
          </form>

          {error && (
            <div className="bg-red-500/10 text-red-400 text-sm p-3 rounded mt-3">
              {error}
            </div>
          )}
        </section>

        {searched && (
          <section className="space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-slate-400 text-sm">
                {results.length} result{results.length === 1 ? "" : "s"}
              </p>
              <label className="flex items-center gap-2 text-sm text-slate-300">
                Sort by
                <select
                  value={sort}
                  onChange={(e) => setSort(e.target.value as SortKey)}
                  className="bg-slate-800 rounded px-3 py-1.5 outline-none"
                >
                  <option value="relevance">Relevance</option>
                  <option value="cited">Most cited</option>
                  <option value="newest">Newest</option>
                </select>
              </label>
            </div>

            {results.length === 0 ? (
              <p className="text-slate-500 text-sm">
                No papers found. Try different words, or untick "Open access
                only".
              </p>
            ) : (
              sorted.map((paper) => {
                const state = imports[paper.source_id];
                const externalLink = paper.landing_page_url ?? paper.doi;
                return (
                  <div
                    key={paper.source_id}
                    className="bg-slate-800 rounded-xl p-5 space-y-3"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <h3 className="font-semibold">{paper.title}</h3>
                      <div className="flex gap-2 shrink-0">
                        <span className="text-xs px-2 py-1 rounded bg-slate-700 text-slate-300">
                          {paper.source === "openalex"
                            ? "OpenAlex"
                            : "Semantic Scholar"}
                        </span>
                        {paper.is_open_access && (
                          <span className="text-xs px-2 py-1 rounded bg-emerald-500/15 text-emerald-400">
                            Open access
                          </span>
                        )}
                      </div>
                    </div>

                    <p className="text-xs text-slate-400">
                      {paper.authors.slice(0, 4).join(", ")}
                      {paper.authors.length > 4 ? " et al." : ""}
                      {paper.year ? ` · ${paper.year}` : ""}
                      {paper.venue ? ` · ${paper.venue}` : ""}
                      {` · cited ${paper.cited_by_count} time${
                        paper.cited_by_count === 1 ? "" : "s"
                      }`}
                    </p>

                    {paper.abstract ? (
                      <details>
                        <summary className="text-xs text-slate-400 cursor-pointer hover:text-slate-200">
                          Abstract
                        </summary>
                        <p className="text-sm text-slate-300 mt-2">
                          {paper.abstract}
                        </p>
                      </details>
                    ) : (
                      <p className="text-xs text-slate-500">
                        No abstract available.
                      </p>
                    )}

                    <div className="flex flex-wrap items-center gap-3">
                      {paper.pdf_url ? (
                        <button
                          onClick={() => handleImport(paper)}
                          disabled={
                            state?.status === "importing" ||
                            state?.status === "done"
                          }
                          className="text-sm px-4 py-1.5 rounded bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-white font-semibold"
                        >
                          {state?.status === "importing"
                            ? "Importing..."
                            : state?.status === "done"
                              ? "Imported"
                              : "Import"}
                        </button>
                      ) : (
                        <span className="text-xs text-slate-500">
                          No open-access PDF
                        </span>
                      )}

                      {externalLink && (
                        <a
                          href={externalLink}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-slate-400 hover:text-slate-200 underline"
                        >
                          Open publisher page
                        </a>
                      )}

                      {state?.status === "done" && (
                        <span className="text-xs text-emerald-400">
                          {state.message}.{" "}
                          <Link to="/" className="underline">
                            View in library
                          </Link>
                        </span>
                      )}
                      {state?.status === "error" && (
                        <span className="text-xs text-red-400">
                          {state.message}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </section>
        )}
      </main>
    </div>
  );
}