"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getUserJobs, type AnalysisJob } from "@/lib/api";
import { Button } from "@/components/ui/button";

const STATUS_STYLES: Record<
  AnalysisJob["status"],
  { bg: string; text: string; label: string }
> = {
  pending: { bg: "bg-yellow-100", text: "text-yellow-700", label: "Pending" },
  downloading: {
    bg: "bg-blue-100",
    text: "text-blue-700",
    label: "Downloading",
  },
  analyzing: {
    bg: "bg-indigo-100",
    text: "text-indigo-700",
    label: "Analyzing",
  },
  completed: {
    bg: "bg-green-100",
    text: "text-green-700",
    label: "Completed",
  },
  failed: { bg: "bg-red-100", text: "text-red-700", label: "Failed" },
};

export default function DashboardPage() {
  const [jobs, setJobs] = useState<AnalysisJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchJobs() {
      try {
        const data = await getUserJobs();
        setJobs(data);
      } catch {
        setError("Failed to load your analyses. Please try again.");
      } finally {
        setLoading(false);
      }
    }
    fetchJobs();
  }, []);

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">My Analyses</h1>
          <p className="mt-1 text-sm text-slate-500">
            View and manage your GEO dataset analyses
          </p>
        </div>
        <Link href="/analyze">
          <Button>New Analysis</Button>
        </Link>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-20">
          <svg
            className="w-6 h-6 text-indigo-600 animate-spin"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {!loading && !error && jobs.length === 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center">
          <div className="w-12 h-12 bg-slate-100 rounded-lg flex items-center justify-center mx-auto mb-4">
            <svg
              className="w-6 h-6 text-slate-400"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9.75 3.104v5.714a2.25 2.25 0 0 1-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 0 1 4.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0 1 12 15a9.065 9.065 0 0 0-6.23.693L5 14.5m14.8.8 1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0 1 12 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5"
              />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-slate-900">
            No analyses yet
          </h3>
          <p className="mt-2 text-sm text-slate-500 max-w-sm mx-auto">
            Start by entering a GEO accession ID to analyze your first dataset.
          </p>
          <Link href="/analyze" className="mt-6 inline-block">
            <Button>Start Your First Analysis</Button>
          </Link>
        </div>
      )}

      {!loading && jobs.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="text-left py-3 px-4 text-xs font-semibold text-slate-500 uppercase tracking-wide">
                  GEO ID
                </th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-slate-500 uppercase tracking-wide hidden sm:table-cell">
                  Title
                </th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-slate-500 uppercase tracking-wide">
                  Status
                </th>
                <th className="text-left py-3 px-4 text-xs font-semibold text-slate-500 uppercase tracking-wide hidden md:table-cell">
                  Date
                </th>
                <th className="text-right py-3 px-4 text-xs font-semibold text-slate-500 uppercase tracking-wide">
                  Action
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {jobs.map((job) => {
                const status = STATUS_STYLES[job.status];
                return (
                  <tr key={job.id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3 px-4">
                      <span className="text-sm font-mono font-medium text-slate-900">
                        {job.geo_id}
                      </span>
                    </td>
                    <td className="py-3 px-4 hidden sm:table-cell">
                      <span className="text-sm text-slate-600 truncate block max-w-xs">
                        {job.metadata?.title || "—"}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${status.bg} ${status.text}`}
                      >
                        {status.label}
                      </span>
                    </td>
                    <td className="py-3 px-4 hidden md:table-cell">
                      <span className="text-sm text-slate-500">
                        {new Date(job.created_at).toLocaleDateString()}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      {job.status === "completed" ? (
                        <Link href={`/results/${job.id}`}>
                          <Button variant="ghost" size="sm">
                            View
                          </Button>
                        </Link>
                      ) : job.status === "failed" ? (
                        <Link href="/analyze">
                          <Button variant="ghost" size="sm">
                            Retry
                          </Button>
                        </Link>
                      ) : (
                        <span className="text-xs text-slate-400">
                          Processing...
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
