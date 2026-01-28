"""Lightweight single-cell RNA-seq analysis pipeline using sklearn + umap-learn.

Replaces scanpy/anndata to avoid heavy C-extension compilation on free hosting tiers.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class SingleCellPipeline:
    """Full single-cell analysis: QC -> normalise -> HVG -> PCA -> UMAP -> clustering -> DE."""

    def run(self, expression: pd.DataFrame) -> dict:
        """Execute the pipeline end-to-end and return a results dict.

        Args:
            expression: genes (rows) x cells (columns) DataFrame

        Returns:
            dict with all analysis results
        """
        logger.info(f"Starting single-cell pipeline: {expression.shape}")

        # Transpose: we want cells as rows, genes as columns
        # GEOparse pivot gives genes-as-rows; we need cells-as-rows
        if expression.shape[0] < expression.shape[1]:
            # More columns than rows -> rows are likely genes
            data = expression.T.copy()
        else:
            data = expression.copy()

        # Ensure numeric
        data = data.apply(pd.to_numeric, errors="coerce").fillna(0)

        result: dict = {
            "n_cells_raw": data.shape[0],
            "n_genes_raw": data.shape[1],
        }

        # ------------------------------------------------------------------
        # Step 1: QC filtering
        # ------------------------------------------------------------------
        logger.info("Step 1: QC filtering")
        genes_per_cell = (data > 0).sum(axis=1)
        cells_per_gene = (data > 0).sum(axis=0)

        # Filter cells with at least 200 genes expressed (adaptive)
        min_genes = min(200, int(data.shape[1] * 0.05))
        cell_mask = genes_per_cell >= min_genes
        data = data.loc[cell_mask]

        # Filter genes expressed in at least 3 cells (adaptive)
        min_cells = min(3, max(1, int(data.shape[0] * 0.01)))
        # Recompute after cell filtering
        cells_per_gene = (data > 0).sum(axis=0)
        gene_mask = cells_per_gene >= min_cells
        data = data.loc[:, gene_mask]

        result["n_cells_filtered"] = data.shape[0]
        result["n_genes_filtered"] = data.shape[1]

        if data.shape[0] < 10 or data.shape[1] < 10:
            raise ValueError(
                f"Too few cells ({data.shape[0]}) or genes ({data.shape[1]}) after filtering"
            )

        # QC metrics
        genes_per_cell_filtered = (data > 0).sum(axis=1)
        result["genes_per_cell"] = genes_per_cell_filtered.tolist()
        result["total_counts"] = data.sum(axis=1).tolist()

        # ------------------------------------------------------------------
        # Step 2: Normalize (CPM + log1p)
        # ------------------------------------------------------------------
        logger.info("Step 2: Normalizing")
        row_sums = data.sum(axis=1)
        row_sums = row_sums.replace(0, 1)
        normalized = data.div(row_sums, axis=0) * 1e4
        log_data = np.log1p(normalized)

        # ------------------------------------------------------------------
        # Step 3: Highly variable genes (top by variance)
        # ------------------------------------------------------------------
        logger.info("Step 3: Selecting variable genes")
        gene_var = log_data.var(axis=0)
        n_hvg = min(2000, log_data.shape[1])
        hvg = gene_var.nlargest(n_hvg).index
        log_data_hvg = log_data[hvg]

        # ------------------------------------------------------------------
        # Step 4: PCA
        # ------------------------------------------------------------------
        logger.info("Step 4: PCA")
        n_components = min(50, log_data_hvg.shape[0] - 1, log_data_hvg.shape[1] - 1)
        n_components = max(n_components, 2)
        scaler = StandardScaler()
        scaled = scaler.fit_transform(log_data_hvg.values)
        pca = PCA(n_components=n_components)
        pca_result = pca.fit_transform(scaled)
        result["pca_embeddings"] = pca_result[:, :2].tolist()
        result["pca_variance_ratio"] = pca.explained_variance_ratio_.tolist()

        # ------------------------------------------------------------------
        # Step 5: UMAP
        # ------------------------------------------------------------------
        logger.info("Step 5: UMAP")
        n_pcs_use = min(30, n_components)
        try:
            import umap

            n_neighbors = min(15, pca_result.shape[0] - 1)
            n_neighbors = max(n_neighbors, 2)
            reducer = umap.UMAP(
                n_components=2, n_neighbors=n_neighbors, random_state=42
            )
            umap_result = reducer.fit_transform(pca_result[:, :n_pcs_use])
            result["umap_embeddings"] = umap_result.tolist()
        except Exception as e:
            logger.warning(f"UMAP failed: {e}, falling back to PCA 2D")
            result["umap_embeddings"] = pca_result[:, :2].tolist()

        # ------------------------------------------------------------------
        # Step 6: Clustering (KMeans as lightweight Leiden alternative)
        # ------------------------------------------------------------------
        logger.info("Step 6: Clustering")
        from sklearn.cluster import KMeans

        n_clusters = min(max(2, int(np.sqrt(data.shape[0] / 10))), 20)
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(pca_result[:, :n_pcs_use])
        result["clusters"] = clusters.tolist()
        result["n_clusters"] = int(n_clusters)
        result["cell_names"] = data.index.tolist()

        # ------------------------------------------------------------------
        # Step 7: Marker genes (top DE genes per cluster via fold-change)
        # ------------------------------------------------------------------
        logger.info("Step 7: Finding marker genes")
        from scipy import stats

        marker_genes: dict[str, list[str]] = {}
        de_records: list[dict] = []

        for c in range(n_clusters):
            cluster_mask = clusters == c
            if cluster_mask.sum() < 2 or (~cluster_mask).sum() < 2:
                continue

            cluster_vals = log_data.loc[data.index[cluster_mask]]
            other_vals = log_data.loc[data.index[~cluster_mask]]

            cluster_means = cluster_vals.mean(axis=0)
            other_means = other_vals.mean(axis=0)
            fold_change = cluster_means - other_means

            # Top 20 genes by fold change for marker list
            top_genes = fold_change.nlargest(20).index.tolist()
            marker_genes[str(c)] = top_genes

            # DE records for the top genes
            for gene in top_genes[:10]:
                try:
                    t_stat, p_val = stats.ttest_ind(
                        cluster_vals[gene].values,
                        other_vals[gene].values,
                        equal_var=False,
                    )
                    de_records.append(
                        {
                            "cluster": str(c),
                            "gene": gene,
                            "log2fc": float(fold_change[gene]),
                            "pvalue": float(p_val) if not np.isnan(p_val) else 1.0,
                            "score": float(t_stat) if not np.isnan(t_stat) else 0.0,
                        }
                    )
                except Exception:
                    continue

        result["marker_genes"] = marker_genes

        # Add adjusted p-values to DE records
        if de_records:
            from statsmodels.stats.multitest import multipletests

            pvals = [r["pvalue"] for r in de_records]
            try:
                _, adj_pvals, _, _ = multipletests(pvals, method="fdr_bh")
                for i, r in enumerate(de_records):
                    r["padj"] = float(adj_pvals[i])
            except Exception:
                for r in de_records:
                    r["padj"] = r["pvalue"]

        result["de_results"] = de_records

        # ------------------------------------------------------------------
        # Step 8: Gene names for heatmap
        # ------------------------------------------------------------------
        all_top: list[str] = []
        for c_genes in marker_genes.values():
            all_top.extend(c_genes[:5])
        # Deduplicate preserving order
        seen: set[str] = set()
        unique_top: list[str] = []
        for g in all_top:
            if g not in seen:
                seen.add(g)
                unique_top.append(g)
        unique_top = unique_top[:50]

        result["top_gene_names"] = unique_top
        if unique_top:
            valid_genes = [g for g in unique_top if g in log_data.columns]
            result["top_gene_expression"] = log_data[valid_genes].values.tolist()
            result["top_gene_names"] = valid_genes
        else:
            result["top_gene_expression"] = []

        logger.info(
            f"Pipeline complete: {data.shape[0]} cells, {n_clusters} clusters"
        )
        return result
