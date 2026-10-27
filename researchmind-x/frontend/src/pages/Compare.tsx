import { useEffect, useState } from "react";
import { isAxiosError } from "axios";
import api from "../api";
import type { CompareResponse, Paper, PaperSummary } from "../api";
import NavBar from "../components/NavBar";

const ATTRIBUTES: { key: keyof PaperSummary; label: string }[] = [
  { key: "methodology", label: "Methodology" },
  { key: "dataset", label: "Dataset" },
  { key: "key_findings", label: "Key Findings" },
  { key: "limitations", label: "Limitations" },
  { key: "future_work", label: "Future Work" },
];

export default function Compare() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [result, setResult] = useState<PaperSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get<Paper[]>("/api/papers")
      .then((res) => setPapers(res.data.filter((p) => p.status === "ready")))
      .catch(() => setError("Could not load your papers"));
  }, []);

  const toggle = (id: number) => {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const handleCompare = async () => {
    setError("");
    setLoading(true);
    setResult([]);
    try {
      const res = await api.post<CompareResponse>("/api/compare", {
        paper_ids: selected,
      });
      setResult(res.data.papers);
    } catch (err) {
      if (isAxiosError(err) && typeof err.response?.data?.detail === "string") {
        setError(err.response.data.detail);
      } else {
        setError("Comparison failed. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      <NavBar />

      <main className="max-w-6xl mx-auto p-6 space-y-6">
        <section>
          <h2 className="text-lg font-semibold mb-1">Compare papers</h2>
          <p className="text-slate-400 text-sm mb-4">
            Pick 2 to 5 papers to compare side by side on methodology, dataset,
            findings, limitations and future work.
          </p>

          <div className="flex flex-wrap gap-2 mb-4">
            {papers.map((p) => (
              <button
                key={p.id}
                onClick={() => toggle(p.id)}
                className={`text-sm px-3 py-2 rounded-lg border text-left max-w-xs truncate ${
                  selected.includes(p.id)
                    ? "bg-emerald-500/20 border-emerald-500 text-emerald-300"
                    : "bg-slate-800 border-slate-700 hover:border-slate-500"
                }`}
                title={p.title}
              >
                {p.title}
              </button>
            ))}
          </div>

          <button
            onClick={handleCompare}
            disabled={selected.length < 2 || loading}
            className="px-5 py-2 rounded bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-white font-semibold text-sm"
          >
            {loading
              ? "Comparing... this can take a minute"
              : `Compare ${selected.length} paper${selected.length === 1 ? "" : "s"}`}
          </button>

          {error && (
            <div className="bg-red-500/10 text-red-400 text-sm p-3 rounded mt-3">
              {error}
            </div>
          )}
        </section>

        {result.length > 0 && (
          <section className="overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr>
                  <th className="text-left p-3 bg-slate-800 border border-slate-700 w-40">
                    Attribute
                  </th>
                  {result.map((p) => (
                    <th
                      key={p.paper_id}
                      className="text-left p-3 bg-slate-800 border border-slate-700 min-w-72"
                    >
                      {p.title}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {ATTRIBUTES.map((attr) => (
                  <tr key={attr.key}>
                    <td className="p-3 border border-slate-800 bg-slate-800/50 font-medium text-emerald-400 align-top">
                      {attr.label}
                    </td>
                    {result.map((p) => (
                      <td
                        key={p.paper_id}
                        className="p-3 border border-slate-800 align-top text-slate-300"
                      >
                        {p[attr.key]}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}
      </main>
    </div>
  );
}