"""Lightweight bulk RNA-seq analysis pipeline using sklearn + scipy.

Replaces scanpy/anndata to avoid heavy C-extension compilation on free hosting tiers.
"""

from __future__ import annotations

import re
import logging
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class BulkPipeline:
    """Analyse a bulk expression matrix: normalise -> PCA -> optional DE."""

    def run(
        self,
        expression: pd.DataFrame,
        gse: Any | None = None,
    ) -> dict:
        """Execute the pipeline and return a results dict.

        Args:
            expression: genes (rows) x samples (columns) DataFrame
            gse: GEOparse GSE object for metadata extraction

        Returns:
            dict with all analysis results
        """
        logger.info(f"Starting bulk pipeline: {expression.shape}")

        data = expression.copy()
        data = data.apply(pd.to_numeric, errors="coerce").fillna(0)

        result: dict = {
            "n_genes_raw": data.shape[0],
            "n_samples": data.shape[1],
            "sample_names": data.columns.tolist(),
        }

        # ------------------------------------------------------------------
        # Step 1: Basic QC - remove zero/low-expression genes
        # ------------------------------------------------------------------
        logger.info("Step 1: QC filtering")
        gene_sums = data.sum(axis=1)
        data = data.loc[gene_sums > 0]

        # Filter genes expressed in fewer than min_samples
        expressed = (data > 0).sum(axis=1)
        data = data.loc[expressed >= min(3, data.shape[1])]

        result["n_genes_filtered"] = data.shape[0]

        if data.shape[0] < 10:
            raise ValueError(f"Too few genes ({data.shape[0]}) after filtering")

        # ------------------------------------------------------------------
        # Step 2: CPM normalization + log1p
        # ------------------------------------------------------------------
        logger.info("Step 2: Normalizing (CPM + log1p)")
        col_sums = data.sum(axis=0)
        col_sums = col_sums.replace(0, 1)
        cpm = data.div(col_sums, axis=1) * 1e6
        log_cpm = np.log1p(cpm)

        # ------------------------------------------------------------------
        # Step 3: PCA
        # ------------------------------------------------------------------
        logger.info("Step 3: PCA")
        # Top variable genes for PCA
        gene_var = log_cpm.var(axis=1)
        n_var = min(5000, log_cpm.shape[0])
        top_var_genes = gene_var.nlargest(n_var).index

        n_components = min(10, log_cpm.shape[1] - 1, len(top_var_genes) - 1)
        n_components = max(n_components, 2)

        scaler = StandardScaler()
        # Transpose: samples as rows, genes as columns
        scaled = scaler.fit_transform(log_cpm.loc[top_var_genes].T.values)

        actual_components = min(n_components, scaled.shape[0] - 1, scaled.shape[1] - 1)
        actual_components = max(actual_components, 2)

        pca = PCA(n_components=actual_components)
        pca_result = pca.fit_transform(scaled)
        result["pca_embeddings"] = pca_result[:, :2].tolist()
        result["pca_variance_ratio"] = pca.explained_variance_ratio_.tolist()

        # ------------------------------------------------------------------
        # Step 4: Sample correlation
        # ------------------------------------------------------------------
        logger.info("Step 4: Sample correlation")
        corr = log_cpm.loc[top_var_genes].corr()
        result["correlation_matrix"] = corr.values.tolist()
        result["correlation_labels"] = corr.columns.tolist()

        # ------------------------------------------------------------------
        # Step 5: Differential expression
        # ------------------------------------------------------------------
        logger.info("Step 5: Differential expression")
        conditions = self._infer_conditions(data.columns, gse)
        result["conditions"] = conditions

        if conditions and len(set(conditions.values())) == 2:
            groups: dict[str, list[str]] = {}
            for sample, cond in conditions.items():
                groups.setdefault(cond, []).append(sample)

            group_names = list(groups.keys())
            g1_samples = groups[group_names[0]]
            g2_samples = groups[group_names[1]]

            if len(g1_samples) >= 2 and len(g2_samples) >= 2:
                de_results: list[dict] = []
                for gene in data.index:
                    g1_vals = log_cpm.loc[gene, g1_samples].values.astype(np.float64)
                    g2_vals = log_cpm.loc[gene, g2_samples].values.astype(np.float64)

                    try:
                        t_stat, p_val = stats.ttest_ind(
                            g1_vals, g2_vals, equal_var=False
                        )
                        log_fc = float(g2_vals.mean() - g1_vals.mean())
                        de_results.append(
                            {
                                "gene": gene,
                                "log2fc": round(log_fc, 4),
                                "pvalue": float(p_val) if not np.isnan(p_val) else 1.0,
                                "t_stat": float(t_stat) if not np.isnan(t_stat) else 0.0,
                                "mean_a": round(float(g1_vals.mean()), 4),
                                "mean_b": round(float(g2_vals.mean()), 4),
                                "group_a": group_names[0],
                                "group_b": group_names[1],
                            }
                        )
                    except Exception:
                        continue

                if de_results:
                    # BH correction
                    from statsmodels.stats.multitest import multipletests

                    pvals = [r["pvalue"] for r in de_results]
                    try:
                        _, adj_pvals, _, _ = multipletests(pvals, method="fdr_bh")
                        for i, r in enumerate(de_results):
                            r["padj"] = float(adj_pvals[i])
                    except Exception:
                        for r in de_results:
                            r["padj"] = r["pvalue"]

                    de_results.sort(key=lambda x: x["pvalue"])
                    result["de_results"] = de_results[:500]
                    result["de_groups"] = group_names
                    n_sig = sum(1 for r in de_results if r.get("padj", 1) < 0.05)
                    logger.info(f"Found {n_sig} DE genes (padj<0.05)")

        # Gene names for display
        gene_var_sorted = gene_var.sort_values(ascending=False)
        result["top_variable_genes"] = gene_var_sorted.head(50).index.tolist()

        logger.info(
            f"Bulk pipeline complete: {data.shape[0]} genes, {data.shape[1]} samples"
        )
        return result

    # ------------------------------------------------------------------
    # Condition inference
    # ------------------------------------------------------------------

    @staticmethod
    def _infer_conditions(sample_names, gse) -> dict[str, str]:
        """Try to infer experimental conditions from GSE metadata."""
        conditions: dict[str, str] = {}

        if gse is None:
            return conditions

        # Common condition-keyword pairs
        _PATTERNS: list[tuple[str, str]] = [
            (r"\bcontrol\b|\bnormal\b|\bhealthy\b|\bwild.?type\b|\bwt\b", "control"),
            (
                r"\btreat\w*\b|\bdisease\b|\btumou?r\b|\bcancer\b|\bknock.?out\b|\bko\b|\bmutant\b",
                "treated",
            ),
        ]

        try:
            for gsm_name, gsm in gse.gsms.items():
                if gsm_name not in sample_names:
                    continue

                title = gsm.metadata.get("title", [""])[0]
                chars = gsm.metadata.get("characteristics_ch1", [])
                text = f"{title} {' '.join(chars)}".lower()

                for pattern, label in _PATTERNS:
                    if re.search(pattern, text):
                        conditions[gsm_name] = label
                        break
        except Exception as e:
            logger.warning(f"Failed to infer conditions: {e}")

        # Need exactly 2 groups with at least 2 samples each
        if conditions:
            unique_labels = set(conditions.values())
            if len(unique_labels) != 2:
                return {}
            for lbl in unique_labels:
                if sum(1 for v in conditions.values() if v == lbl) < 2:
                    return {}

        return conditions
