import { useState } from "react";
import type { FormEvent } from "react";
import api from "../api";
import type { SearchHit } from "../api";
import NavBar from "../components/NavBar";

export default function Search() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchHit[]>([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSearch = async (e: FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setError("");
    setLoading(true);
    try {
      const res = await api.post<SearchHit[]>("/api/search", {
        query,
        top_k: 8,
      });
      setResults(res.data);
      setSearched(true);
    } catch {
      setError("Search failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      <NavBar />

      <main className="max-w-3xl mx-auto p-6 space-y-6">
        <section>
          <h2 className="text-lg font-semibold mb-1">Search your papers</h2>
          <p className="text-slate-400 text-sm mb-4">
            Ask a question in your own words. Results are matched by meaning,
            not just exact keywords.
          </p>

          <form onSubmit={handleSearch} className="flex gap-2">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. why use PostgreSQL instead of MongoDB"
              className="flex-1 p-3 rounded bg-slate-800 text-white placeholder-slate-500 outline-none focus:ring-2 focus:ring-emerald-500"
            />
            <button
              type="submit"
              disabled={loading}
              className="px-5 rounded bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-white font-semibold"
            >
              {loading ? "Searching..." : "Search"}
            </button>
          </form>

          {error && (
            <div className="bg-red-500/10 text-red-400 text-sm p-3 rounded mt-3">
              {error}
            </div>
          )}
        </section>

        {searched && (
          <section>
            <h3 className="text-slate-400 text-sm mb-3">
              {results.length} result{results.length === 1 ? "" : "s"}
            </h3>

            {results.length === 0 ? (
              <p className="text-slate-500 text-sm">
                No matches. Try rephrasing your question, or upload more
                papers.
              </p>
            ) : (
              <ul className="space-y-3">
                {results.map((hit) => (
                  <li key={hit.chunk_id} className="bg-slate-800 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs text-emerald-400">
                        paper #{hit.paper_id} · page {hit.page_number}
                        {hit.section ? ` · ${hit.section}` : ""}
                      </span>
                      <span className="text-xs text-slate-500">
                        match {(hit.score * 100).toFixed(0)}%
                      </span>
                    </div>
                    <p className="text-sm text-slate-300">{hit.text}</p>
                  </li>
                ))}
              </ul>
            )}
          </section>
        )}
      </main>
    </div>
  );
}