"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { GeoSearch } from "@/components/analysis/geo-search";
import { JobStatus } from "@/components/analysis/job-status";
import { submitAnalysis } from "@/lib/api";

function AnalyzeContent() {
  const searchParams = useSearchParams();
  const initialGeo = searchParams.get("geo") || "";

  const [jobId, setJobId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(geoId: string) {
    setLoading(true);
    setError(null);
    try {
      const job = await submitAnalysis(geoId);
      setJobId(job.id);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to start analysis"
      );
    } finally {
      setLoading(false);
    }
  }

  // Auto-submit if geo param is present
  useEffect(() => {
    if (initialGeo && /^GSE\d+$/i.test(initialGeo) && !jobId) {
      handleSubmit(initialGeo.toUpperCase());
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-3xl mx-auto px-4 py-16">
        <div className="text-center mb-10">
          <h1 className="text-3xl font-bold text-slate-900">
            Analyze a GEO Dataset
          </h1>
          <p className="mt-2 text-slate-600">
            Enter a GEO accession ID to start automated analysis
          </p>
        </div>

        {!jobId && (
          <div className="flex justify-center">
            <GeoSearch
              initialValue={initialGeo}
              onSubmit={handleSubmit}
              loading={loading}
            />
          </div>
        )}

        {error && (
          <div className="mt-6 bg-red-50 border border-red-200 rounded-xl p-4 max-w-2xl mx-auto">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {jobId && (
          <div className="mt-8">
            <JobStatus jobId={jobId} />
          </div>
        )}

        {/* Recent analyses hint */}
        {!jobId && !loading && (
          <div className="mt-16 text-center">
            <p className="text-sm text-slate-400">
              Popular datasets to try:
            </p>
            <div className="mt-3 flex flex-wrap justify-center gap-2">
              {["GSE164073", "GSE150728", "GSE135893", "GSE156063"].map(
                (id) => (
                  <button
                    key={id}
                    onClick={() => handleSubmit(id)}
                    className="px-3 py-1.5 text-sm text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors font-mono"
                  >
                    {id}
                  </button>
                )
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function AnalyzePage() {
  return (
    <Suspense>
      <AnalyzeContent />
    </Suspense>
  );
}
