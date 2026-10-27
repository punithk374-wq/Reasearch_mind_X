import axios from "axios";

export interface User {
  id: number;
  full_name: string;
  email: string;
  created_at: string;
}

const api = axios.create({
  baseURL: "http://localhost:8000",
});

// Attach the saved token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;
export interface Paper {
    id: number;
    title: string;
    filename: string;
    page_count: number;
    chunk_count: number;
    status: "processing" | "ready" | "failed";
    error_message: string | null;
    created_at: string;
  }
  
  export interface Chunk {
    id: number;
    chunk_index: number;
    page_number: number;
    section: string | null;
    text: string;
  }
  export interface SearchHit {
    chunk_id: number;
    paper_id: number;
    page_number: number;
    section: string | null;
    text: string;
    score: number;
  }
  export interface AskResponse {
    answer: string;
    sources: SearchHit[];
  }
  export interface PaperSummary {
    paper_id: number;
    title: string;
    methodology: string;
    dataset: string;
    key_findings: string;
    limitations: string;
    future_work: string;
  }
  
  export interface CompareResponse {
    papers: PaperSummary[];
  }

  export interface Gap {
    type: string;
    title: string;
    description: string;
    supporting_paper_ids: number[];
    evidence: string;
    research_question: string;
  }
  
  export interface GapPaper {
    paper_id: number;
    title: string;
  }
  
  export interface GapResponse {
    papers: GapPaper[];
    gaps: Gap[];
    note: string | null;
  }
  export interface Passage {
    paper_id: number;
    page_number: number;
    section: string | null;
    text: string;
  }
  
  export interface VerifiedGap {
    type: string;
    title: string;
    description: string;
    supporting_paper_ids: number[];
    evidence: string;
    research_question: string;
    verdict: string;
    status: string;
    verified_paper_ids: number[];
    verification_reason: string;
    passages: Passage[];
  }
  
  export interface ResearchReport {
    papers: GapPaper[];
    gaps: VerifiedGap[];
    dropped_count: number;
    note: string | null;
    trace: string[];
  }
  export interface DiscoveredPaper {
    source: string;
    source_id: string;
    title: string;
    authors: string[];
    year: number | null;
    venue: string | null;
    doi: string | null;
    abstract: string;
    cited_by_count: number;
    is_open_access: boolean;
    pdf_url: string | null;
    landing_page_url: string | null;
  }