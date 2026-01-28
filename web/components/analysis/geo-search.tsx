"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";

const GEO_PATTERN = /^GSE\d+$/i;

interface GeoSearchProps {
  initialValue?: string;
  onSubmit: (geoId: string) => void;
  loading?: boolean;
}

export function GeoSearch({
  initialValue = "",
  onSubmit,
  loading = false,
}: GeoSearchProps) {
  const [geoId, setGeoId] = useState(initialValue);
  const [error, setError] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = geoId.trim().toUpperCase();
    if (!trimmed) {
      setError("Please enter a GEO accession ID");
      return;
    }
    if (!GEO_PATTERN.test(trimmed)) {
      setError("Enter a valid GEO ID (e.g., GSE12345)");
      return;
    }
    setError("");
    onSubmit(trimmed);
  }

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl">
      <label
        htmlFor="geo-id"
        className="block text-sm font-medium text-slate-700 mb-2"
      >
        GEO Accession ID
      </label>
      <div className="flex gap-3">
        <div className="flex-1">
          <input
            id="geo-id"
            type="text"
            value={geoId}
            onChange={(e) => {
              setGeoId(e.target.value);
              setError("");
            }}
            placeholder="GSE12345"
            disabled={loading}
            className="w-full px-4 py-3 text-base border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
          />
        </div>
        <Button type="submit" size="lg" loading={loading} className="rounded-xl">
          Analyze
        </Button>
      </div>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      <p className="mt-2 text-xs text-slate-400">
        Enter a GEO Series accession ID starting with GSE followed by digits
      </p>
    </form>
  );
}
