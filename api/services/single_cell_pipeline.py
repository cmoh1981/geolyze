"""Scanpy-based single-cell RNA-seq analysis pipeline."""

from __future__ import annotations

import warnings

import anndata as ad
import numpy as np
import pandas as pd
import scanpy as sc

# Suppress non-critical scanpy / anndata warnings during pipeline runs
warnings.filterwarnings("ignore", category=FutureWarning)


class SingleCellPipeline:
    """Full single-cell analysis: QC -> normalise -> HVG -> PCA -> UMAP -> clustering -> DE."""

    def run(self, expression: pd.DataFrame) -> ad.AnnData:
        """Execute the pipeline end-to-end and return a fully-annotated AnnData."""

        adata = self._build_anndata(expression)
        adata = self._qc_filter(adata)
        adata = self._normalise(adata)
        adata = self._hvg_pca(adata)
        adata = self._embed_cluster(adata)
        adata = self._rank_genes(adata)

        return adata

    # ------------------------------------------------------------------
    # Pipeline steps
    # ------------------------------------------------------------------

    @staticmethod
    def _build_anndata(expression: pd.DataFrame) -> ad.AnnData:
        """Create AnnData from a genes-by-samples DataFrame (transpose so
        obs = cells/samples, var = genes)."""
        # GEOparse pivot gives genes-as-rows; scanpy wants cells-as-rows
        mat = expression.T.copy()

        # Ensure numeric
        mat = mat.apply(pd.to_numeric, errors="coerce").fillna(0)

        adata = ad.AnnData(X=mat.values.astype(np.float32))
        adata.obs_names = mat.index.astype(str)
        adata.var_names = mat.columns.astype(str)
        adata.var_names_make_unique()
        adata.obs_names_make_unique()

        return adata

    @staticmethod
    def _qc_filter(adata: ad.AnnData) -> ad.AnnData:
        """Basic quality-control filtering."""
        # Flag mitochondrial genes
        adata.var["mt"] = adata.var_names.str.upper().str.startswith("MT-")

        sc.pp.calculate_qc_metrics(
            adata, qc_vars=["mt"], percent_top=None, log1p=False, inplace=True
        )

        # Adaptive thresholds -- avoid wiping the entire dataset
        min_genes = min(200, int(adata.n_vars * 0.05))
        min_cells = min(3, max(1, int(adata.n_obs * 0.01)))

        sc.pp.filter_cells(adata, min_genes=min_genes)
        sc.pp.filter_genes(adata, min_cells=min_cells)

        # Remove high-mito cells if we detected any MT genes
        if adata.var["mt"].any():
            pct_mito = adata.obs["pct_counts_mt"]
            upper = min(pct_mito.quantile(0.95), 20)
            adata = adata[pct_mito < upper].copy()

        return adata

    @staticmethod
    def _normalise(adata: ad.AnnData) -> ad.AnnData:
        """Total-count normalise to 1e4, then log1p."""
        sc.pp.normalize_total(adata, target_sum=1e4)
        sc.pp.log1p(adata)

        # Keep raw counts for DE later
        adata.raw = adata.copy()

        return adata

    @staticmethod
    def _hvg_pca(adata: ad.AnnData) -> ad.AnnData:
        """Select highly-variable genes and run PCA."""
        n_hvg = min(2000, adata.n_vars)
        if adata.n_vars > n_hvg:
            sc.pp.highly_variable_genes(
                adata, n_top_genes=n_hvg, flavor="seurat", subset=False
            )
        else:
            adata.var["highly_variable"] = True

        # PCA on HVG
        n_pcs = min(50, adata.n_obs - 1, adata.n_vars - 1)
        n_pcs = max(n_pcs, 2)  # need at least 2
        sc.tl.pca(adata, n_comps=n_pcs, use_highly_variable=True)

        return adata

    @staticmethod
    def _embed_cluster(adata: ad.AnnData) -> ad.AnnData:
        """Compute neighbours, UMAP, and Leiden clustering."""
        n_neighbors = min(15, adata.n_obs - 1)
        n_neighbors = max(n_neighbors, 2)
        n_pcs_use = min(adata.obsm["X_pca"].shape[1], 30)

        sc.pp.neighbors(adata, n_neighbors=n_neighbors, n_pcs=n_pcs_use)
        sc.tl.umap(adata)
        sc.tl.leiden(adata, flavor="igraph", n_iterations=2)

        return adata

    @staticmethod
    def _rank_genes(adata: ad.AnnData) -> ad.AnnData:
        """Rank genes per Leiden cluster (Wilcoxon)."""
        if len(adata.obs["leiden"].unique()) < 2:
            return adata  # need >= 2 groups

        try:
            sc.tl.rank_genes_groups(adata, groupby="leiden", method="wilcoxon")
        except Exception:
            # Fall back to t-test if wilcoxon fails (e.g. very small groups)
            try:
                sc.tl.rank_genes_groups(adata, groupby="leiden", method="t-test")
            except Exception:
                pass

        return adata
