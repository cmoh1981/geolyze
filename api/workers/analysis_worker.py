"""Background worker that orchestrates the full GEO analysis pipeline.

Heavy CPU work (sklearn, DE) is offloaded to a thread-pool executor so
the async event loop stays responsive.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from config import settings
from services.bulk_pipeline import BulkPipeline
from services.data_detector import DataDetector
from services.geo_downloader import GEODownloader
from services.plot_generator import PlotGenerator
from services.single_cell_pipeline import SingleCellPipeline
from utils.redis_client import get_redis, update_status
from utils.supabase_client import save_error, save_results, update_job_status

logger = logging.getLogger("geolyze.worker")

# Shared executor for CPU-bound work (one per process to avoid over-subscription)
_executor = ThreadPoolExecutor(max_workers=2)


# ======================================================================
# Public entry point (called from the route via BackgroundTasks)
# ======================================================================


async def run_analysis(job_id: str, geo_id: str, user_id: str) -> None:
    """Top-level coroutine: runs the full pipeline, updating status in Redis
    and persisting the final result to Supabase."""

    loop = asyncio.get_running_loop()

    try:
        # The entire pipeline is CPU-bound; run it in a thread
        result = await loop.run_in_executor(
            _executor,
            partial(_run_pipeline_sync, job_id, geo_id),
        )

        # Save to Supabase (I/O, but fast)
        save_results(job_id, result)
        _update(job_id, "completed", 100, "Analysis complete!")

    except ValueError as exc:
        _update(job_id, "failed", 0, str(exc))
        save_error(job_id, str(exc))

    except Exception as exc:
        msg = f"Unexpected error: {exc}"
        logger.exception(msg)
        _update(job_id, "failed", 0, msg)
        save_error(job_id, msg)

    finally:
        _cleanup(geo_id)


# ======================================================================
# Synchronous pipeline (runs inside ThreadPoolExecutor)
# ======================================================================


def _run_pipeline_sync(job_id: str, geo_id: str) -> dict[str, Any]:
    """Execute every pipeline stage and return the result dict."""

    # ------------------------------------------------------------------
    # 1. Download
    # ------------------------------------------------------------------
    _update(job_id, "downloading", 10, "Downloading GEO dataset...")

    downloader = GEODownloader(settings.DATA_DIR)
    data = downloader.download(geo_id)

    _update(job_id, "analyzing", 25, "Dataset downloaded. Detecting data type...")

    # ------------------------------------------------------------------
    # 2. Detect bulk vs single-cell
    # ------------------------------------------------------------------
    detector = DataDetector()
    data_type = detector.detect(data["expression"], data["metadata"])

    _update(job_id, "analyzing", 35, f"Detected {data_type}. Running analysis pipeline...")

    # ------------------------------------------------------------------
    # 3. Run pipeline (returns plain dict now, not AnnData)
    # ------------------------------------------------------------------
    if data_type == "single_cell":
        pipeline = SingleCellPipeline()
        pipeline_result = pipeline.run(data["expression"])
    else:
        pipeline = BulkPipeline()
        pipeline_result = pipeline.run(data["expression"], data.get("gse"))

    _update(job_id, "analyzing", 75, "Analysis done. Generating visualisations...")

    # ------------------------------------------------------------------
    # 4. Generate plots
    # ------------------------------------------------------------------
    plotter = PlotGenerator()
    plots: dict[str, Any] = {}

    if data_type == "single_cell":
        plots["umap"] = plotter.umap_plot(pipeline_result)
        plots["qc_violin"] = plotter.qc_violin_plot(pipeline_result)
        plots["heatmap"] = plotter.heatmap_top_genes(pipeline_result)
        plots["pca_variance"] = plotter.pca_variance_plot(pipeline_result)
        if pipeline_result.get("top_gene_names"):
            plots["dotplot"] = plotter.gene_expression_dotplot(pipeline_result)
    else:
        plots["pca_variance"] = plotter.pca_variance_plot(pipeline_result)
        plots["correlation"] = plotter.sample_correlation_heatmap(pipeline_result)
        if pipeline_result.get("de_results"):
            plots["volcano"] = plotter.volcano_plot(pipeline_result["de_results"])

    _update(job_id, "analyzing", 90, "Building result summary...")

    # ------------------------------------------------------------------
    # 5. Summary statistics
    # ------------------------------------------------------------------
    summary: dict[str, Any] = {
        "data_type": data_type,
        "n_genes": pipeline_result.get(
            "n_genes_filtered", pipeline_result.get("n_genes_raw", 0)
        ),
    }

    if data_type == "single_cell":
        summary["n_samples"] = pipeline_result.get("n_cells_filtered", 0)
        summary["n_clusters"] = pipeline_result.get("n_clusters", 0)
        summary["n_cells_raw"] = pipeline_result.get("n_cells_raw", 0)
        summary["n_cells_filtered"] = pipeline_result.get("n_cells_filtered", 0)
    else:
        summary["n_samples"] = pipeline_result.get("n_samples", 0)

    # ------------------------------------------------------------------
    # 6. Build final result
    # ------------------------------------------------------------------
    result: dict[str, Any] = {
        "plots": plots,
        "summary": summary,
        "metadata": data["metadata"],
        "data_type": data_type,
    }

    # Include DE results (already serialised as list of dicts)
    de_results = pipeline_result.get("de_results")
    if de_results:
        # Sanitise NaN/Inf values
        clean_de = []
        for rec in de_results[:100]:
            clean_rec = {}
            for k, v in rec.items():
                clean_rec[k] = _safe_float(v) if isinstance(v, float) else v
            clean_de.append(clean_rec)
        result["de_results"] = clean_de

    # Include marker genes for single-cell
    if pipeline_result.get("marker_genes"):
        result["marker_genes"] = pipeline_result["marker_genes"]

    return result


# ======================================================================
# Helpers
# ======================================================================


def _safe_float(v: Any) -> float | None:
    """Convert numpy/pandas scalars to plain float, mapping NaN/Inf to None."""
    if v is None:
        return None
    try:
        f = float(v)
        if np.isfinite(f):
            return round(f, 6)
        return None
    except (TypeError, ValueError):
        return None


def _update(job_id: str, status: str, progress: int, message: str) -> None:
    """Update both Redis (fast reads) and Supabase (persistence)."""
    try:
        r = get_redis()
        update_status(r, job_id, status, progress, message)
    except Exception:
        pass  # Redis failure is non-fatal

    try:
        completed_at = (
            datetime.now(timezone.utc).isoformat() if status in ("completed", "failed") else None
        )
        update_job_status(job_id, status, progress, message, completed_at)
    except Exception:
        pass


def _cleanup(geo_id: str) -> None:
    """Remove downloaded dataset files."""
    try:
        path = Path(settings.DATA_DIR) / geo_id
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass
