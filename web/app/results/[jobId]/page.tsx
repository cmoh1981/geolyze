"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getJobResults, type AnalysisJob } from "@/lib/api";
import { PlotViewer } from "@/components/analysis/plot-viewer";
import { Button } from "@/components/ui/button";

type TabKey = "overview" | "umap" | "de" | "qc";

const TABS: { key: TabKey; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "umap", label: "UMAP / Clustering" },
  { key: "de", label: "Differential Expression" },
  { key: "qc", label: "Quality Control" },
];

export default function ResultsPage() {
  const params = useParams();
  const jobId = params.jobId as string;
  const [job, setJob] = useState<AnalysisJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabKey>("overview");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    async function fetchResults() {
      try {
        const data = await getJobResults(jobId);
        setJob(data);
      } catch {
        setError("Failed to load results. The analysis may still be running.");
      } finally {
        setLoading(false);
      }
    }
    fetchResults();
  }, [jobId]);

  function handleShare() {
    navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <svg
            className="w-8 h-8 text-indigo-600 animate-spin mx-auto"
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
          <p className="mt-3 text-slate-600">Loading results...</p>
        </div>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center max-w-md">
          <p className="text-red-600 font-medium">
            {error || "Results not found"}
          </p>
          <Link href="/analyze" className="mt-4 inline-block">
            <Button variant="outline">Back to Analyze</Button>
          </Link>
        </div>
      </div>
    );
  }

  const results = (job.result_data || {}) as Record<string, { data: Array<Record<string, unknown>>; layout?: Record<string, unknown> }>;

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-8">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <Link
                href="/dashboard"
                className="text-sm text-slate-500 hover:text-slate-700"
              >
                Dashboard
              </Link>
              <span className="text-slate-300">/</span>
              <span className="text-sm text-slate-700 font-mono">
                {job.geo_id}
              </span>
            </div>
            <h1 className="text-2xl font-bold text-slate-900">
              {job.metadata?.title || job.geo_id}
            </h1>
            {job.metadata?.summary && (
              <p className="mt-2 text-sm text-slate-600 max-w-3xl leading-relaxed">
                {job.metadata.summary}
              </p>
            )}
            {job.metadata && (
              <div className="mt-3 flex flex-wrap gap-3">
                {job.metadata.organism && (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
                    {job.metadata.organism}
                  </span>
                )}
                {job.metadata.type && (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-700">
                    {job.metadata.type}
                  </span>
                )}
                {job.metadata.samples && (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
                    {job.metadata.samples} samples
                  </span>
                )}
              </div>
            )}
          </div>
          <Button variant="outline" size="sm" onClick={handleShare}>
            {copied ? "Copied!" : "Share Results"}
          </Button>
        </div>

        {/* Tabs */}
        <div className="border-b border-slate-200 mb-6">
          <div className="flex gap-0 overflow-x-auto">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                  activeTab === tab.key
                    ? "border-indigo-600 text-indigo-600"
                    : "border-transparent text-slate-500 hover:text-slate-700"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Tab content */}
        <div className="space-y-6">
          {activeTab === "overview" && (
            <>
              <div className="grid md:grid-cols-2 gap-6">
                {results.umap && (
                  <PlotViewer
                    data={results.umap.data}
                    layout={results.umap.layout}
                    title="UMAP Projection"
                  />
                )}
                {results.heatmap && (
                  <PlotViewer
                    data={results.heatmap.data}
                    layout={results.heatmap.layout}
                    title="Top Genes Heatmap"
                  />
                )}
              </div>
              {results.volcano && (
                <PlotViewer
                  data={results.volcano.data}
                  layout={results.volcano.layout}
                  title="Volcano Plot"
                />
              )}
              {!results.umap &&
                !results.heatmap &&
                !results.volcano && (
                  <div className="bg-white border border-slate-200 rounded-xl p-12 text-center">
                    <p className="text-slate-500">
                      No plot data available yet. Results may still be
                      processing.
                    </p>
                  </div>
                )}
            </>
          )}

          {activeTab === "umap" && (
            <>
              {results.umap ? (
                <PlotViewer
                  data={results.umap.data}
                  layout={{
                    ...results.umap.layout,
                    height: 700,
                  }}
                  title="UMAP Projection"
                />
              ) : (
                <EmptyState label="UMAP" />
              )}
            </>
          )}

          {activeTab === "de" && (
            <>
              {results.volcano ? (
                <PlotViewer
                  data={results.volcano.data}
                  layout={{
                    ...results.volcano.layout,
                    height: 600,
                  }}
                  title="Volcano Plot - Differential Expression"
                />
              ) : (
                <EmptyState label="Differential expression" />
              )}
              {results.heatmap && (
                <PlotViewer
                  data={results.heatmap.data}
                  layout={{
                    ...results.heatmap.layout,
                    height: 600,
                  }}
                  title="Top DE Genes Heatmap"
                />
              )}
            </>
          )}

          {activeTab === "qc" && (
            <>
              {results.qc ? (
                <PlotViewer
                  data={results.qc.data}
                  layout={results.qc.layout}
                  title="Quality Control Metrics"
                />
              ) : (
                <EmptyState label="Quality control" />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function EmptyState({ label }: { label: string }) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-12 text-center">
      <p className="text-slate-500">
        {label} data is not available for this dataset.
      </p>
    </div>
  );
}
