import { createClient } from "@/lib/supabase/client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function getAuthHeaders(): Promise<HeadersInit> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (session?.access_token) {
    headers["Authorization"] = `Bearer ${session.access_token}`;
  }

  return headers;
}

export interface AnalysisJob {
  id: string;
  geo_id: string;
  status: "pending" | "downloading" | "analyzing" | "completed" | "failed";
  result_data: Record<string, unknown> | null;
  metadata: {
    title?: string;
    summary?: string;
    organism?: string;
    platform?: string;
    samples?: number;
    type?: string;
  } | null;
  error: string | null;
  created_at: string;
  completed_at: string | null;
}

export async function submitAnalysis(geoId: string): Promise<AnalysisJob> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/api/analyze`, {
    method: "POST",
    headers,
    body: JSON.stringify({ geo_id: geoId }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to submit analysis");
  }

  return response.json();
}

export async function getJobStatus(jobId: string): Promise<AnalysisJob> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/api/analyze/${jobId}`, {
    headers,
  });

  if (!response.ok) {
    throw new Error("Failed to fetch job status");
  }

  return response.json();
}

export async function getJobResults(jobId: string): Promise<AnalysisJob> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/api/analyze/${jobId}/results`, {
    headers,
  });

  if (!response.ok) {
    throw new Error("Failed to fetch job results");
  }

  return response.json();
}

export async function getUserJobs(): Promise<AnalysisJob[]> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/api/jobs`, {
    headers,
  });

  if (!response.ok) {
    throw new Error("Failed to fetch jobs");
  }

  return response.json();
}
