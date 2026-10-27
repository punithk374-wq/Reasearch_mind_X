import { useEffect, useRef, useState } from "react";
import type { ChangeEvent } from "react";
import { isAxiosError } from "axios";
import api from "../api";
import type { Chunk, Paper } from "../api";
import NavBar from "../components/NavBar";

const STATUS_STYLES: Record<Paper["status"], string> = {
  ready: "bg-emerald-500/15 text-emerald-400",
  processing: "bg-amber-500/15 text-amber-400",
  failed: "bg-red-500/15 text-red-400",
};

export default function Home() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [openId, setOpenId] = useState<number | null>(null);
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api
      .get<Paper[]>("/api/papers")
      .then((res) => setPapers(res.data))
      .catch(() => setError("Could not load your papers"));
  }, []);

  const reload = async () => {
    const res = await api.get<Paper[]>("/api/papers");
    setPapers(res.data);
  };

  const handleUpload = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setError("");
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      await api.post("/api/papers/upload", form);
      await reload();
    } catch (err) {
      if (isAxiosError(err) && typeof err.response?.data?.detail === "string") {
        setError(err.response.data.detail);
      } else {
        setError("Upload failed. Please try again.");
      }
    } finally {
      setUploading(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  };

  const toggleChunks = async (paperId: number) => {
    if (openId === paperId) {
      setOpenId(null);
      return;
    }
    const res = await api.get<Chunk[]>(`/api/papers/${paperId}/chunks`);
    setChunks(res.data);
    setOpenId(paperId);
  };

  const handleDelete = async (paper: Paper) => {
    if (!window.confirm(`Delete "${paper.title}"?`)) return;
    await api.delete(`/api/papers/${paper.id}`);
    if (openId === paper.id) setOpenId(null);
    await reload();
  };

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      <NavBar />

      <main className="max-w-4xl mx-auto p-6 space-y-6">
        <section className="bg-slate-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold mb-1">Upload a research paper</h2>
          <p className="text-slate-400 text-sm mb-4">
            PDF files only, up to 20 MB. Text is extracted and split into
            searchable chunks.
          </p>

          <input
            ref={fileInput}
            type="file"
            accept="application/pdf"
            onChange={handleUpload}
            disabled={uploading}
            className="block w-full text-sm text-slate-300 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:bg-emerald-500 file:text-white file:font-semibold hover:file:bg-emerald-600 disabled:opacity-50"
          />

          {uploading && (
            <p className="text-amber-400 text-sm mt-3">Processing PDF...</p>
          )}
          {error && (
            <div className="bg-red-500/10 text-red-400 text-sm p-3 rounded mt-3">
              {error}
            </div>
          )}
        </section>

        <section>
          <h2 className="text-lg font-semibold mb-3">
            Your papers ({papers.length})
          </h2>

          {papers.length === 0 ? (
            <p className="text-slate-400 text-sm">
              No papers yet. Upload your first PDF above.
            </p>
          ) : (
            <ul className="space-y-3">
              {papers.map((paper) => (
                <li key={paper.id} className="bg-slate-800 rounded-xl p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <p className="font-medium truncate">{paper.title}</p>
                      <p className="text-slate-400 text-xs mt-1">
                        {paper.filename} · {paper.page_count} pages ·{" "}
                        {paper.chunk_count} chunks
                      </p>
                      {paper.status === "failed" && paper.error_message && (
                        <p className="text-red-400 text-xs mt-1">
                          {paper.error_message}
                        </p>
                      )}
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <span
                        className={`text-xs px-2 py-1 rounded ${STATUS_STYLES[paper.status]}`}
                      >
                        {paper.status}
                      </span>
                      {paper.status === "ready" && (
                        <button
                          onClick={() => toggleChunks(paper.id)}
                          className="text-xs px-2 py-1 rounded bg-slate-700 hover:bg-slate-600"
                        >
                          {openId === paper.id ? "Hide chunks" : "View chunks"}
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(paper)}
                        className="text-xs px-2 py-1 rounded bg-slate-700 hover:bg-red-600"
                      >
                        Delete
                      </button>
                    </div>
                  </div>

                  {openId === paper.id && (
                    <div className="mt-4 max-h-96 overflow-y-auto space-y-2">
                      {chunks.map((c) => (
                        <div key={c.id} className="bg-slate-900 rounded p-3">
                          <p className="text-xs text-emerald-400 mb-1">
                            #{c.chunk_index} · page {c.page_number}
                            {c.section ? ` · ${c.section}` : ""}
                          </p>
                          <p className="text-sm text-slate-300">{c.text}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </div>
  );
}