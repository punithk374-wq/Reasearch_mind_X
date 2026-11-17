import { useEffect, useRef, useState } from "react";
import type { ChangeEvent } from "react";
import { Link } from "react-router-dom";
import api, { getApiError } from "../api";
import type { Chunk, Paper } from "../api";
import NavBar from "../components/NavBar";
import PaperBrowser from "../components/PaperBrowser";
import { DOMAINS } from "../paperDomains";

const STATUS_STYLES: Record<Paper["status"], string> = {
  ready: "bg-emerald-500/15 text-emerald-300", processing: "bg-amber-500/15 text-amber-300", failed: "bg-red-500/15 text-red-300",
};

export default function Home() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState<number[]>([]);
  const [openId, setOpenId] = useState<number | null>(null);
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [chunksLoading, setChunksLoading] = useState(false);
  const chunksRequest = useRef(0);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    api.get<Paper[]>("/api/papers", { signal: controller.signal })
      .then(res => setPapers(res.data))
      .catch(err => { if (!controller.signal.aborted) setError(getApiError(err, "Could not load your papers")); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, []);

  const reload = async () => setPapers((await api.get<Paper[]>("/api/papers")).data);
  const handleUpload = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(""); setUploading(true);
    try {
      const form = new FormData(); form.append("file", file);
      await api.post("/api/papers/upload", form);
      await reload();
      setNotice("Paper uploaded. Assign its primary research domain below before comparison.");
    } catch (err) { setError(getApiError(err, "Upload failed. Please try again.")); }
    finally { setUploading(false); if (fileInput.current) fileInput.current.value = ""; }
  };
  const saveDomain = async (paper: Paper, domain: string) => {
    setSaving(prev => [...prev, paper.id]); setError("");
    try {
      const res = await api.patch<Paper>(`/api/papers/${paper.id}/domain`, { domain: domain || null });
      setPapers(prev => prev.map(p => p.id === paper.id ? res.data : p));
      setNotice(`Domain saved for ${paper.title}`);
    } catch (err) { setError(getApiError(err, "Could not save the domain. Please try again.")); }
    finally { setSaving(prev => prev.filter(id => id !== paper.id)); }
  };
  const toggleChunks = async (paperId: number) => {
    const request = ++chunksRequest.current;
    if (openId === paperId) { setOpenId(null); setChunksLoading(false); return; }
    setOpenId(paperId); setChunks([]); setChunksLoading(true); setError("");
    try {
      const res = await api.get<Chunk[]>(`/api/papers/${paperId}/chunks`);
      if (request === chunksRequest.current) setChunks(res.data);
    } catch (err) { if (request === chunksRequest.current) setError(getApiError(err, "Could not load passages.")); }
    finally { if (request === chunksRequest.current) setChunksLoading(false); }
  };
  const handleDelete = async (paper: Paper) => {
    if (!window.confirm(`Delete "${paper.title}"?`)) return;
    setError("");
    try {
      await api.delete(`/api/papers/${paper.id}`);
      if (openId === paper.id) { ++chunksRequest.current; setOpenId(null); }
      await reload(); setNotice("Paper deleted.");
    } catch (err) { setError(getApiError(err, "Could not delete the paper.")); }
  };
  return <div className="min-h-screen bg-slate-900 text-white">
    <NavBar />
    <main className="max-w-7xl mx-auto p-4 sm:p-6 space-y-6">
      <section className="rounded-xl border border-slate-700 bg-slate-800 p-5">
        <h1 className="text-xl font-semibold mb-2">My Papers</h1>
        <p className="text-slate-300 text-sm mb-4">Your research library. Upload PDFs up to 20 MB, find papers by name, and read the original documents.</p>
        <label className="block text-sm mb-2" htmlFor="paper-upload">Upload a research paper</label>
        <input id="paper-upload" ref={fileInput} type="file" accept="application/pdf" onChange={handleUpload} disabled={uploading}
          className="block w-full text-sm text-slate-300 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:bg-emerald-600 file:text-white disabled:opacity-50" />
        {uploading && <p role="status" className="text-amber-300 text-sm mt-3">Processing PDF…</p>}
      </section>
      {error && <p role="alert" className="bg-red-950 text-red-200 p-3 rounded-lg">{error}</p>}
      {notice && <p role="status" className="text-sm text-emerald-300">{notice}</p>}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Your papers ({papers.length})</h2>
        <p className="text-sm text-slate-300">Assign each paper's primary application domain for comparison. For example, medical image analysis belongs to Medicine &amp; healthcare even when it uses AI. Domains save automatically and can be corrected at any time.</p>
        {loading ? <p role="status">Loading papers…</p> : <PaperBrowser papers={papers} renderPaper={paper =>
          <article className="rounded-xl bg-slate-800 border border-slate-700 p-4 space-y-4">
            <div className="flex items-center justify-between gap-3"><span className={`text-xs px-2 py-1 rounded ${STATUS_STYLES[paper.status]}`}>{paper.status}</span><span className="text-xs text-slate-300">{paper.page_count} pages · {paper.chunk_count} chunks</span></div>
            <h3 className="font-medium break-words leading-relaxed">{paper.title}</h3>
            <p className="text-xs text-slate-400 break-words">{paper.filename}</p>
            <div>
              <label className="block text-xs text-slate-300 mb-1" htmlFor={`domain-${paper.id}`}>Research domain {saving.includes(paper.id) && "· Saving…"}</label>
              <select id={`domain-${paper.id}`} value={paper.domain ?? ""} disabled={saving.includes(paper.id)} onChange={e => void saveDomain(paper, e.target.value)}
                className="w-full text-sm rounded-lg border border-slate-600 bg-slate-900 px-2 py-2 focus:ring-2 focus:ring-emerald-400 disabled:opacity-50">
                <option value="">Unassigned — choose a domain</option>
                {DOMAINS.map(([key, label]) => <option key={key} value={key}>{label}</option>)}
              </select>
            </div>
            {paper.status === "failed" && <p className="text-red-300 text-sm">{paper.error_message}</p>}
            <div className="flex flex-wrap gap-2">
              <Link to={`/papers/${paper.id}/view`} className="rounded-lg bg-emerald-600 hover:bg-emerald-500 px-3 py-2 text-sm font-medium">Open PDF</Link>
              {paper.status === "ready" && <button onClick={() => void toggleChunks(paper.id)} className="rounded-lg bg-slate-700 hover:bg-slate-600 px-3 py-2 text-sm">{openId === paper.id ? "Hide chunks" : "View chunks"}</button>}
              <button onClick={() => void handleDelete(paper)} className="rounded-lg border border-slate-600 hover:bg-red-900 px-3 py-2 text-sm">Delete</button>
            </div>
            {openId === paper.id && <div className="max-h-96 overflow-y-auto space-y-3">
              {chunksLoading ? <p>Loading passages…</p> : chunks.map(c => <div key={c.id} className="bg-slate-900 p-3 rounded-lg">
                <p className="text-xs text-emerald-300 mb-2">#{c.chunk_index} · page {c.page_number}{c.section ? ` · ${c.section}` : ""}</p>
                <p className="text-sm text-slate-300">{c.text}</p>
              </div>)}
            </div>}
          </article>
        } />}
      </section>
    </main>
  </div>;
}
