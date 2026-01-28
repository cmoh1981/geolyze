"""Background worker that orchestrates the full GEO analysis pipeline.

Heavy CPU work (scanpy, DE) is offloaded to a thread-pool executor so
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
    # 3. Run pipeline
    # ------------------------------------------------------------------
    if data_type == "single_cell":
        pipeline = SingleCellPipeline()
        adata = pipeline.run(data["expression"])
    else:
        pipeline = BulkPipeline()
        adata = pipeline.run(data["expression"], data.get("gse"))

    _update(job_id, "analyzing", 75, "Analysis done. Generating visualisations...")

    # ------------------------------------------------------------------
    # 4. Generate plots
    # ------------------------------------------------------------------
    plotter = PlotGenerator()
    plots: dict[str, Any] = {}

    if data_type == "single_cell":
        plots["umap"] = plotter.umap_plot(adata)
        plots["qc_violin"] = plotter.qc_violin_plot(adata)
        plots["heatmap"] = plotter.heatmap_top_genes(adata)
        plots["pca_variance"] = plotter.pca_variance_plot(adata)
        plots["dotplot"] = plotter.gene_expression_dotplot(adata)
    else:
        plots["pca_variance"] = plotter.pca_variance_plot(adata)
        plots["correlation"] = plotter.sample_correlation_heatmap(adata)
        if "de_results" in getattr(adata, "uns", {}):
            de_df = adata.uns["de_results"]
            if isinstance(de_df, pd.DataFrame) and not de_df.empty:
                plots["volcano"] = plotter.volcano_plot(de_df)

    _update(job_id, "analyzing", 90, "Building result summary...")

    # ------------------------------------------------------------------
    # 5. Summary statistics
    # ------------------------------------------------------------------
    summary: dict[str, Any] = {
        "n_genes": int(adata.n_vars),
        "n_samples": int(adata.n_obs),
        "data_type": data_type,
    }
    if data_type == "single_cell" and "leiden" in adata.obs.columns:
        summary["n_clusters"] = int(adata.obs["leiden"].nunique())

    # ------------------------------------------------------------------
    # 6. Serialise DE results
    # ------------------------------------------------------------------
    de_list: list[dict] | None = None
    if data_type == "single_cell":
        de_list = _extract_sc_de_genes(adata)
    elif "de_results" in getattr(adata, "uns", {}):
        de_df = adata.uns["de_results"]
        if isinstance(de_df, pd.DataFrame) and not de_df.empty:
            de_list = (
                de_df.head(100)
                .replace({np.nan: None, np.inf: None, -np.inf: None})
                .to_dict(orient="records")
            )

    result: dict[str, Any] = {
        "plots": plots,
        "summary": summary,
        "metadata": data["metadata"],
        "data_type": data_type,
    }
    if de_list is not None:
        result["de_results"] = de_list

    return result


# ======================================================================
# Helpers
# ======================================================================


def _extract_sc_de_genes(adata, top_n: int = 20) -> list[dict] | None:
    """Extract the top DE genes per cluster from scanpy's rank_genes_groups."""
    if "rank_genes_groups" not in adata.uns:
        return None

    rgg = adata.uns["rank_genes_groups"]
    groups = list(rgg["names"].dtype.names)

    records: list[dict] = []
    for group in groups:
        names = rgg["names"][group][:top_n]
        scores = rgg["scores"][group][:top_n]
        pvals = rgg["pvals"][group][:top_n] if "pvals" in rgg else [None] * top_n
        padj = rgg["pvals_adj"][group][:top_n] if "pvals_adj" in rgg else [None] * top_n
        logfc = rgg["logfoldchanges"][group][:top_n] if "logfoldchanges" in rgg else [None] * top_n

        for i in range(len(names)):
            records.append(
                {
                    "cluster": str(group),
                    "gene": str(names[i]),
                    "score": _safe_float(scores[i]),
                    "pvalue": _safe_float(pvals[i]),
                    "padj": _safe_float(padj[i]),
                    "log2fc": _safe_float(logfc[i]),
                }
            )

    return records if records else None


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
