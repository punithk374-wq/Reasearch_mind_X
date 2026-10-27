import { useEffect, useState } from "react";
import { isAxiosError } from "axios";
import api from "../api";
import type { GapResponse, Paper } from "../api";
import NavBar from "../components/NavBar";

const TYPE_LABELS: Record<string, { label: string; style: string }> = {
  recurring_limitation: {
    label: "Recurring limitation",
    style: "bg-amber-500/15 text-amber-400",
  },
  underrepresented_approach: {
    label: "Underrepresented approach",
    style: "bg-sky-500/15 text-sky-400",
  },
  inconsistent_findings: {
    label: "Inconsistent findings",
    style: "bg-red-500/15 text-red-400",
  },
  unaddressed_future_work: {
    label: "Unaddressed future work",
    style: "bg-violet-500/15 text-violet-400",
  },
};

export default function Gaps() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [result, setResult] = useState<GapResponse | null>(null);
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

  const handleFind = async () => {
    setError("");
    setLoading(true);
    setResult(null);
    try {
      const res = await api.post<GapResponse>("/api/gaps", {
        paper_ids: selected,
      });
      setResult(res.data);
    } catch (err) {
      if (isAxiosError(err) && typeof err.response?.data?.detail === "string") {
        setError(err.response.data.detail);
      } else {
        setError("Gap analysis failed. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  const titleFor = (id: number) =>
    result?.papers.find((p) => p.paper_id === id)?.title ?? `Paper #${id}`;

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      <NavBar />

      <main className="max-w-4xl mx-auto p-6 space-y-6">
        <section>
          <h2 className="text-lg font-semibold mb-1">Research gaps</h2>
          <p className="text-slate-400 text-sm mb-4">
            Pick 2 to 5 related papers. The system looks for recurring
            limitations, underrepresented approaches, inconsistent findings and
            unaddressed future work, and links each candidate gap to its
            supporting papers.
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
            onClick={handleFind}
            disabled={selected.length < 2 || loading}
            className="px-5 py-2 rounded bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-white font-semibold text-sm"
          >
            {loading
              ? "Analysing... this can take a minute"
              : `Find gaps across ${selected.length} paper${selected.length === 1 ? "" : "s"}`}
          </button>

          {error && (
            <div className="bg-red-500/10 text-red-400 text-sm p-3 rounded mt-3">
              {error}
            </div>
          )}
        </section>

        {result && (
          <section className="space-y-4">
            <div className="bg-slate-800 border border-slate-700 rounded-lg p-3 text-xs text-slate-400">
              These are candidate gaps based on the selected papers only. They
              are not proof of novelty and should be reviewed by a researcher
              against the wider literature.
            </div>

            {result.note && (
              <div className="bg-amber-500/10 text-amber-300 text-sm p-3 rounded">
                {result.note}
              </div>
            )}

            {result.gaps.length === 0 ? (
              <p className="text-slate-400 text-sm">
                No supported gaps were found for this selection.
              </p>
            ) : (
              result.gaps.map((gap, i) => {
                const meta = TYPE_LABELS[gap.type] ?? {
                  label: gap.type,
                  style: "bg-slate-700 text-slate-300",
                };
                return (
                  <div key={i} className="bg-slate-800 rounded-xl p-5 space-y-3">
                    <div className="flex items-start justify-between gap-3">
                      <h3 className="font-semibold">{gap.title}</h3>
                      <span
                        className={`text-xs px-2 py-1 rounded shrink-0 ${meta.style}`}
                      >
                        {meta.label}
                      </span>
                    </div>

                    <p className="text-sm text-slate-300">{gap.description}</p>

                    <div>
                      <p className="text-xs text-slate-500 mb-1">Evidence</p>
                      <p className="text-sm text-slate-400">{gap.evidence}</p>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      {gap.supporting_paper_ids.map((id) => (
                        <span
                          key={id}
                          className="text-xs px-2 py-1 rounded bg-slate-900 text-emerald-400 max-w-xs truncate"
                          title={titleFor(id)}
                        >
                          {titleFor(id)}
                        </span>
                      ))}
                    </div>

                    <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-lg p-3">
                      <p className="text-xs text-emerald-400 mb-1">
                        Candidate research question
                      </p>
                      <p className="text-sm">{gap.research_question}</p>
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