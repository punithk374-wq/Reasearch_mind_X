import { useEffect, useState } from "react";
import { isAxiosError } from "axios";
import api from "../api";
import type { Paper, ResearchReport, VerifiedGap } from "../api";
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

const STATUS_STYLES: Record<string, string> = {
  verified: "bg-emerald-500/15 text-emerald-400",
  "partially verified": "bg-amber-500/15 text-amber-400",
  unverified: "bg-slate-600/40 text-slate-300",
};

function toMarkdown(report: ResearchReport): string {
  const lines: string[] = ["# ResearchMind X report", "", "## Papers analysed", ""];
  report.papers.forEach((p) => lines.push(`- ${p.title} (paper #${p.paper_id})`));
  lines.push(
    "",
    "## Candidate research gaps",
    "",
    "_Candidate gaps for human review. These are not proof of novelty._",
    ""
  );
  report.gaps.forEach((g, i) => {
    lines.push(`### ${i + 1}. ${g.title}`, "");
    lines.push(`- **Type:** ${g.type.replace(/_/g, " ")}`);
    lines.push(`- **Status:** ${g.status}`);
    lines.push(`- **Cited papers:** ${g.supporting_paper_ids.join(", ")}`);
    lines.push(
      `- **Verified by papers:** ${g.verified_paper_ids.join(", ") || "none"}`,
      ""
    );
    lines.push(g.description, "");
    lines.push(`**Evidence:** ${g.evidence}`, "");
    lines.push(`**Verification:** ${g.verification_reason}`, "");
    lines.push(`**Candidate research question:** ${g.research_question}`, "");
  });
  if (report.dropped_count > 0) {
    lines.push(
      `_${report.dropped_count} candidate gap(s) were dropped because the papers did not support them._`
    );
  }
  return lines.join("\n");
}

function GapCard({
  gap,
  titleFor,
}: {
  gap: VerifiedGap;
  titleFor: (id: number) => string;
}) {
  const typeMeta = TYPE_LABELS[gap.type] ?? {
    label: gap.type,
    style: "bg-slate-700 text-slate-300",
  };
  const statusStyle = STATUS_STYLES[gap.status] ?? "bg-slate-700 text-slate-300";

  return (
    <div className="bg-slate-800 rounded-xl p-5 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-semibold">{gap.title}</h3>
        <div className="flex gap-2 shrink-0">
          <span className={`text-xs px-2 py-1 rounded ${typeMeta.style}`}>
            {typeMeta.label}
          </span>
          <span className={`text-xs px-2 py-1 rounded ${statusStyle}`}>
            {gap.status}
          </span>
        </div>
      </div>

      <p className="text-xs text-slate-500">
        Supported by {gap.verified_paper_ids.length} of{" "}
        {gap.supporting_paper_ids.length} cited paper
        {gap.supporting_paper_ids.length === 1 ? "" : "s"}
      </p>

      <p className="text-sm text-slate-300">{gap.description}</p>

      <div>
        <p className="text-xs text-slate-500 mb-1">Evidence</p>
        <p className="text-sm text-slate-400">{gap.evidence}</p>
      </div>

      <div>
        <p className="text-xs text-slate-500 mb-1">Verification</p>
        <p className="text-sm text-slate-400">{gap.verification_reason}</p>
      </div>

      <div className="flex flex-wrap gap-2">
        {gap.supporting_paper_ids.map((id) => (
          <span
            key={id}
            className={`text-xs px-2 py-1 rounded bg-slate-900 max-w-xs truncate ${
              gap.verified_paper_ids.includes(id)
                ? "text-emerald-400"
                : "text-slate-500 line-through"
            }`}
            title={
              gap.verified_paper_ids.includes(id)
                ? titleFor(id)
                : `${titleFor(id)} (cited, but not confirmed by its text)`
            }
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

      {gap.passages.length > 0 && (
        <details>
          <summary className="text-xs text-slate-400 cursor-pointer hover:text-slate-200">
            View evidence passages ({gap.passages.length})
          </summary>
          <div className="mt-2 space-y-2">
            {gap.passages.map((p, j) => (
              <div key={j} className="bg-slate-900 rounded p-3">
                <p className="text-xs text-emerald-400 mb-1">
                  {titleFor(p.paper_id)} · page {p.page_number}
                  {p.section ? ` · ${p.section}` : ""}
                </p>
                <p className="text-xs text-slate-400">{p.text}</p>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}

export default function Research() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [report, setReport] = useState<ResearchReport | null>(null);
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

  const handleRun = async () => {
    setError("");
    setLoading(true);
    setReport(null);
    try {
      const res = await api.post<ResearchReport>("/api/research/run", {
        paper_ids: selected,
      });
      setReport(res.data);
    } catch (err) {
      if (isAxiosError(err) && typeof err.response?.data?.detail === "string") {
        setError(err.response.data.detail);
      } else {
        setError("The research workflow failed. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (!report) return;
    const blob = new Blob([toMarkdown(report)], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "researchmind-report.md";
    a.click();
    URL.revokeObjectURL(url);
  };

  const titleFor = (id: number) =>
    report?.papers.find((p) => p.paper_id === id)?.title ?? `Paper #${id}`;

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      <NavBar />

      <main className="max-w-4xl mx-auto p-6 space-y-6">
        <section>
          <h2 className="text-lg font-semibold mb-1">Research workflow</h2>
          <p className="text-slate-400 text-sm mb-4">
            Pick 2 to 5 related papers and run the full pipeline: summarise each
            paper, detect candidate gaps, verify every gap against the papers'
            own text, and produce a report.
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
            onClick={handleRun}
            disabled={selected.length < 2 || loading}
            className="px-5 py-2 rounded bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-white font-semibold text-sm"
          >
            {loading
              ? "Running workflow..."
              : `Run research on ${selected.length} paper${selected.length === 1 ? "" : "s"}`}
          </button>

          {loading && (
            <p className="text-amber-400 text-sm mt-3">
              Extract summaries, detect gaps, verify evidence, build report. This
              can take up to a minute.
            </p>
          )}

          {error && (
            <div className="bg-red-500/10 text-red-400 text-sm p-3 rounded mt-3">
              {error}
            </div>
          )}
        </section>

        {report && (
          <section className="space-y-4">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-lg font-semibold">Report</h2>
              <button
                onClick={handleDownload}
                className="text-sm px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700"
              >
                Download (.md)
              </button>
            </div>

            <div className="bg-slate-800 border border-slate-700 rounded-lg p-3 text-xs text-slate-400">
              These are candidate gaps based on the selected papers only. They
              are not proof of novelty and should be reviewed by a researcher
              against the wider literature.
            </div>

            {report.note && (
              <div className="bg-amber-500/10 text-amber-300 text-sm p-3 rounded">
                {report.note}
              </div>
            )}

            {report.gaps.length === 0 ? (
              <p className="text-slate-400 text-sm">
                No supported gaps were found for this selection.
              </p>
            ) : (
              report.gaps.map((gap, i) => (
                <GapCard key={i} gap={gap} titleFor={titleFor} />
              ))
            )}

            {report.dropped_count > 0 && (
              <p className="text-xs text-slate-500">
                {report.dropped_count} candidate gap
                {report.dropped_count === 1 ? " was" : "s were"} dropped because
                the cited papers did not support them.
              </p>
            )}

            <div className="bg-slate-800 rounded-xl p-4">
              <p className="text-xs text-slate-500 mb-2">
                How this report was produced
              </p>
              <ol className="text-xs text-slate-400 space-y-1 list-decimal list-inside">
                {report.trace.map((line, i) => (
                  <li key={i}>{line}</li>
                ))}
              </ol>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}