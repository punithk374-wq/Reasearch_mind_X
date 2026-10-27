import { useState } from "react";
import type { FormEvent } from "react";
import api from "../api";
import type { AskResponse, SearchHit } from "../api";
import NavBar from "../components/NavBar";

interface Turn {
  question: string;
  answer: string;
  sources: SearchHit[];
}

// Splits "...claim [1][2] more text [3]." into plain text and citation markers
function renderAnswer(text: string) {
  const parts = text.split(/(\[\d+\])/g);
  return parts.map((part, i) => {
    const match = part.match(/^\[(\d+)\]$/);
    if (match) {
      return (
        <sup
          key={i}
          className="text-emerald-400 font-semibold ml-0.5"
          title={`Source ${match[1]}`}
        >
          [{match[1]}]
        </sup>
      );
    }
    return <span key={i}>{part}</span>;
  });
}

export default function Ask() {
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleAsk = async (e: FormEvent) => {
    e.preventDefault();
    const q = question.trim();
    if (!q) return;

    setError("");
    setLoading(true);
    setQuestion("");
    try {
      const res = await api.post<AskResponse>("/api/rag/ask", {
        question: q,
        top_k: 5,
      });
      setTurns((prev) => [
        ...prev,
        { question: q, answer: res.data.answer, sources: res.data.sources },
      ]);
    } catch {
      setError("Something went wrong answering that question.");
      setQuestion(q);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      <NavBar />

      <main className="max-w-3xl mx-auto p-6 space-y-6">
        <section>
          <h2 className="text-lg font-semibold mb-1">Ask your papers</h2>
          <p className="text-slate-400 text-sm mb-4">
            Get a synthesized answer grounded in your papers, with numbered
            citations linking back to the exact evidence.
          </p>

          <form onSubmit={handleAsk} className="flex gap-2">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. what are the main limitations of this approach?"
              className="flex-1 p-3 rounded bg-slate-800 text-white placeholder-slate-500 outline-none focus:ring-2 focus:ring-emerald-500"
            />
            <button
              type="submit"
              disabled={loading}
              className="px-5 rounded bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-white font-semibold"
            >
              {loading ? "Thinking..." : "Ask"}
            </button>
          </form>

          {error && (
            <div className="bg-red-500/10 text-red-400 text-sm p-3 rounded mt-3">
              {error}
            </div>
          )}
        </section>

        <section className="space-y-6">
          {turns.length === 0 && !loading && (
            <p className="text-slate-500 text-sm">
              Ask a question above to get started.
            </p>
          )}

          {turns.map((turn, i) => (
            <div key={i} className="space-y-3">
              <div className="bg-slate-800 rounded-xl p-4">
                <p className="text-xs text-slate-500 mb-1">You asked</p>
                <p className="text-sm font-medium">{turn.question}</p>
              </div>

              <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-4">
                <p className="text-xs text-emerald-400 mb-2">Answer</p>
                <p className="text-sm leading-relaxed">
                  {renderAnswer(turn.answer)}
                </p>
              </div>

              {turn.sources.length > 0 && (
                <div>
                  <p className="text-xs text-slate-500 mb-2">Sources</p>
                  <div className="space-y-2">
                    {turn.sources.map((s, idx) => (
                      <div key={s.chunk_id} className="bg-slate-800 rounded p-3">
                        <p className="text-xs text-emerald-400 mb-1">
                          [{idx + 1}] paper #{s.paper_id} · page{" "}
                          {s.page_number}
                          {s.section ? ` · ${s.section}` : ""} · match{" "}
                          {(s.score * 100).toFixed(0)}%
                        </p>
                        <p className="text-xs text-slate-400">{s.text}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </section>
      </main>
    </div>
  );
}