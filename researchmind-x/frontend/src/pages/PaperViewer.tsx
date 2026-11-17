import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api, { getApiError } from "../api";
import type { Paper } from "../api";
import NavBar from "../components/NavBar";

export default function PaperViewer() {
  const { paperId } = useParams();
  const [view, setView] = useState<{ id: string; url: string; paper: Paper } | null>(null);
  const [error, setError] = useState<{ id: string; message: string } | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    let url = "";
    const load = async () => {
      try {
        const [paper, pdf] = await Promise.all([
          api.get<Paper>(`/api/papers/${paperId}`, { signal: controller.signal }),
          api.get<Blob>(`/api/papers/${paperId}/pdf`, { responseType: "blob", signal: controller.signal }),
        ]);
        if (controller.signal.aborted) return;
        url = URL.createObjectURL(new Blob([pdf.data], { type: "application/pdf" }));
        setView({ id: paperId!, url, paper: paper.data });
      } catch (err) {
        if (!controller.signal.aborted) setError({ id: paperId!, message: getApiError(err, "Could not open this PDF. It may be unavailable or you may not have access.") });
      }
    };
    void load();
    return () => { controller.abort(); if (url) URL.revokeObjectURL(url); };
  }, [paperId]);
  const ready = view?.id === paperId ? view : null;
  const message = error && error.id === paperId ? error.message : "";
  return <div className="min-h-screen bg-slate-900 text-white"><NavBar />
    <main className="max-w-7xl mx-auto p-4 sm:p-6 space-y-4">
      <Link to="/" className="text-emerald-300 underline">← Back to My Papers</Link>
      <h1 className="text-xl font-semibold break-words">{ready?.paper.title ?? "Paper PDF"}</h1>
      {message ? <p role="alert" className="rounded-lg bg-red-950 p-4 text-red-200">{message}</p> : !ready ? <p role="status">Loading original PDF…</p> : <>
        <p className="text-sm text-slate-300">Read the original paper below. If your browser cannot display PDFs, <a className="underline text-emerald-300" href={ready.url} download={ready.paper.filename}>download the PDF</a>.</p>
        <iframe title={`PDF: ${ready.paper.title}`} src={ready.url} className="w-full rounded-xl border border-slate-600 bg-white" style={{ height: "78vh" }} />
      </>}
    </main>
  </div>;
}
