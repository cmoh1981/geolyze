"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { getJobStatus, type AnalysisJob } from "@/lib/api";

interface JobStatusProps {
  jobId: string;
}

type StepStatus = "complete" | "active" | "pending";

interface Step {
  label: string;
  key: AnalysisJob["status"];
}

const STEPS: Step[] = [
  { label: "Dataset Found", key: "pending" },
  { label: "Downloading", key: "downloading" },
  { label: "Analyzing", key: "analyzing" },
  { label: "Complete", key: "completed" },
];

function getStepStatus(
  stepIndex: number,
  jobStatus: AnalysisJob["status"]
): StepStatus {
  const statusOrder: AnalysisJob["status"][] = [
    "pending",
    "downloading",
    "analyzing",
    "completed",
  ];
  const currentIndex = statusOrder.indexOf(jobStatus);

  if (jobStatus === "failed") {
    return stepIndex <= currentIndex ? "complete" : "pending";
  }

  if (stepIndex < currentIndex) return "complete";
  if (stepIndex === currentIndex) return "active";
  return "pending";
}

function StepIcon({ status }: { status: StepStatus }) {
  if (status === "complete") {
    return (
      <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center">
        <svg
          className="w-4 h-4 text-white"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={3}
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M4.5 12.75l6 6 9-13.5"
          />
        </svg>
      </div>
    );
  }

  if (status === "active") {
    return (
      <div className="w-8 h-8 rounded-full border-2 border-indigo-600 flex items-center justify-center">
        <svg
          className="w-4 h-4 text-indigo-600 animate-spin"
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
    );
  }

  return (
    <div className="w-8 h-8 rounded-full border-2 border-slate-300 flex items-center justify-center">
      <div className="w-2 h-2 rounded-full bg-slate-300" />
    </div>
  );
}

export function JobStatus({ jobId }: JobStatusProps) {
  const [job, setJob] = useState<AnalysisJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const pollStatus = useCallback(async () => {
    try {
      const data = await getJobStatus(jobId);
      setJob(data);

      if (data.status === "completed") {
        router.push(`/results/${jobId}`);
      }

      return data.status;
    } catch {
      setError("Failed to check analysis status. Please try again.");
      return "failed";
    }
  }, [jobId, router]);

  useEffect(() => {
    let timeoutId: ReturnType<typeof setTimeout>;
    let cancelled = false;

    async function poll() {
      const status = await pollStatus();
      if (
        !cancelled &&
        status !== "completed" &&
        status !== "failed"
      ) {
        timeoutId = setTimeout(poll, 3000);
      }
    }

    poll();

    return () => {
      cancelled = true;
      clearTimeout(timeoutId);
    };
  }, [pollStatus]);

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-xl p-6">
        <p className="text-red-700 font-medium">Analysis Error</p>
        <p className="mt-1 text-sm text-red-600">{error}</p>
      </div>
    );
  }

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-8">
      <h2 className="text-lg font-semibold text-slate-900 mb-2">
        Analysis in Progress
      </h2>
      {job?.metadata?.title && (
        <p className="text-sm text-slate-500 mb-6">{job.metadata.title}</p>
      )}

      {/* Stepper */}
      <div className="flex items-center gap-0">
        {STEPS.map((step, index) => {
          const status = job
            ? getStepStatus(index, job.status)
            : index === 0
            ? "active"
            : "pending";

          return (
            <div key={step.key} className="flex items-center flex-1 last:flex-none">
              <div className="flex flex-col items-center">
                <StepIcon status={status} />
                <span
                  className={`mt-2 text-xs font-medium ${
                    status === "complete"
                      ? "text-indigo-600"
                      : status === "active"
                      ? "text-indigo-600"
                      : "text-slate-400"
                  }`}
                >
                  {step.label}
                </span>
              </div>
              {index < STEPS.length - 1 && (
                <div
                  className={`flex-1 h-0.5 mx-2 mb-6 ${
                    status === "complete" ? "bg-indigo-600" : "bg-slate-200"
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>

      {job?.status === "failed" && (
        <div className="mt-6 p-4 bg-red-50 rounded-lg border border-red-200">
          <p className="text-sm text-red-700 font-medium">Analysis failed</p>
          <p className="text-sm text-red-600 mt-1">
            {job.error || "An unexpected error occurred. Please try again."}
          </p>
        </div>
      )}

      {job?.metadata && (
        <div className="mt-6 pt-6 border-t border-slate-100">
          <h3 className="text-sm font-medium text-slate-700 mb-3">
            Dataset Info
          </h3>
          <dl className="grid grid-cols-2 gap-3 text-sm">
            {job.metadata.organism && (
              <>
                <dt className="text-slate-500">Organism</dt>
                <dd className="text-slate-900">{job.metadata.organism}</dd>
              </>
            )}
            {job.metadata.samples && (
              <>
                <dt className="text-slate-500">Samples</dt>
                <dd className="text-slate-900">{job.metadata.samples}</dd>
              </>
            )}
            {job.metadata.type && (
              <>
                <dt className="text-slate-500">Data Type</dt>
                <dd className="text-slate-900">{job.metadata.type}</dd>
              </>
            )}
          </dl>
        </div>
      )}
    </div>
  );
}
