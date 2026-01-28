"use client";

import dynamic from "next/dynamic";
import { useCallback, useRef } from "react";
import { Button } from "@/components/ui/button";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

interface PlotViewerProps {
  data: Array<Record<string, unknown>>;
  layout?: Record<string, unknown>;
  title?: string;
  className?: string;
}

export function PlotViewer({
  data,
  layout = {},
  title,
  className = "",
}: PlotViewerProps) {
  const plotRef = useRef<HTMLDivElement>(null);

  const defaultLayout: Record<string, unknown> = {
    autosize: true,
    margin: { t: 40, r: 20, b: 40, l: 60 },
    paper_bgcolor: "transparent",
    plot_bgcolor: "#fafafa",
    font: { family: "Inter, sans-serif", color: "#334155" },
    ...layout,
  };

  const downloadPlot = useCallback(
    async (format: "png" | "svg") => {
      if (!plotRef.current) return;
      const Plotly = await import("plotly.js-dist-min");
      const graphDiv = plotRef.current.querySelector(
        ".js-plotly-plot"
      ) as HTMLElement | null;
      if (!graphDiv) return;

      await Plotly.downloadImage(graphDiv, {
        format,
        filename: title?.toLowerCase().replace(/\s+/g, "_") || "plot",
        width: 1200,
        height: 800,
        scale: 2,
      });
    },
    [title]
  );

  return (
    <div className={`bg-white border border-slate-200 rounded-xl overflow-hidden ${className}`}>
      {title && (
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <h3 className="font-semibold text-slate-900">{title}</h3>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => downloadPlot("png")}
            >
              PNG
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => downloadPlot("svg")}
            >
              SVG
            </Button>
          </div>
        </div>
      )}
      <div ref={plotRef} className="w-full">
        <Plot
          data={data}
          layout={defaultLayout}
          config={{
            responsive: true,
            displayModeBar: true,
            modeBarButtonsToRemove: ["lasso2d", "select2d"],
            displaylogo: false,
          }}
          style={{ width: "100%", height: "500px" }}
          useResizeHandler
        />
      </div>
    </div>
  );
}
