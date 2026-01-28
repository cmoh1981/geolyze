"""Basic bulk RNA-seq analysis pipeline (normalisation, PCA, simple DE)."""

from __future__ import annotations

import re
import warnings
from typing import Any

import anndata as ad
import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore", category=FutureWarning)


class BulkPipeline:
    """Analyse a bulk expression matrix: normalise -> PCA -> optional DE."""

    def run(
        self,
        expression: pd.DataFrame,
        gse: Any | None = None,
    ) -> ad.AnnData:
        """Execute the pipeline and return an annotated AnnData.

        If two conditions can be inferred from the sample metadata a
        Welch t-test DE table is stored in ``adata.uns["de_results"]``.
        """
        adata = self._build_anndata(expression)
        adata = self._qc_filter(adata)
        adata = self._normalise(adata)
        adata = self._pca(adata)

        # Attempt DE if we can split samples into two groups
        if gse is not None:
            conditions = self._infer_conditions(gse)
            if conditions is not None:
                adata = self._differential_expression(adata, conditions)

        return adata

    # ------------------------------------------------------------------

    @staticmethod
    def _build_anndata(expression: pd.DataFrame) -> ad.AnnData:
        """Genes-as-rows DataFrame -> AnnData (obs = samples)."""
        mat = expression.T.copy()
        mat = mat.apply(pd.to_numeric, errors="coerce").fillna(0)

        adata = ad.AnnData(X=mat.values.astype(np.float32))
        adata.obs_names = mat.index.astype(str)
        adata.var_names = mat.columns.astype(str)
        adata.var_names_make_unique()
        adata.obs_names_make_unique()
        return adata

    @staticmethod
    def _qc_filter(adata: ad.AnnData) -> ad.AnnData:
        """Remove genes with zero variance or expressed in < 2 samples."""
        gene_nonzero = np.asarray((adata.X > 0).sum(axis=0)).flatten()
        keep = gene_nonzero >= min(2, adata.n_obs)
        adata = adata[:, keep].copy()
        return adata

    @staticmethod
    def _normalise(adata: ad.AnnData) -> ad.AnnData:
        """Library-size normalise, then log1p."""
        import scanpy as sc

        sc.pp.normalize_total(adata, target_sum=1e6)  # CPM
        sc.pp.log1p(adata)
        adata.raw = adata.copy()
        return adata

    @staticmethod
    def _pca(adata: ad.AnnData) -> ad.AnnData:
        import scanpy as sc

        n_pcs = min(50, adata.n_obs - 1, adata.n_vars - 1)
        n_pcs = max(n_pcs, 2)
        sc.tl.pca(adata, n_comps=n_pcs)
        return adata

    # ------------------------------------------------------------------
    # Condition inference
    # ------------------------------------------------------------------

    @staticmethod
    def _infer_conditions(gse: Any) -> dict[str, str] | None:
        """Try to split GSM samples into exactly two groups.

        Returns ``{gsm_name: group_label}`` or *None*.
        """
        try:
            gsm_items = list(gse.gsms.items())
        except Exception:
            return None

        # Collect 'title' and characteristic tags per sample
        titles: dict[str, str] = {}
        for name, gsm in gsm_items:
            title = gsm.metadata.get("title", [""])[0]
            chars = gsm.metadata.get("characteristics_ch1", [])
            titles[name] = f"{title} {' '.join(chars)}".lower()

        # Common condition-keyword pairs
        _PATTERNS: list[tuple[str, str]] = [
            (r"\bcontrol\b|\bnormal\b|\bhealthy\b|\bwild.?type\b|\bwt\b", "control"),
            (r"\btreat\w*\b|\bdisease\b|\btumou?r\b|\bcancer\b|\bknock.?out\b|\bko\b|\bmutant\b", "treated"),
        ]

        conditions: dict[str, str] = {}
        for name, text in titles.items():
            for pattern, label in _PATTERNS:
                if re.search(pattern, text):
                    conditions[name] = label
                    break

        if not conditions:
            return None

        unique_labels = set(conditions.values())
        if len(unique_labels) != 2:
            return None

        # Need at least 2 samples per group
        for lbl in unique_labels:
            if sum(1 for v in conditions.values() if v == lbl) < 2:
                return None

        return conditions

    # ------------------------------------------------------------------
    # Differential expression (Welch t-test)
    # ------------------------------------------------------------------

    @staticmethod
    def _differential_expression(
        adata: ad.AnnData,
        conditions: dict[str, str],
    ) -> ad.AnnData:
        """Run per-gene Welch t-test between the two condition groups.

        Stores a DataFrame in ``adata.uns["de_results"]``.
        """
        labels = list(set(conditions.values()))
        group_a_label, group_b_label = labels[0], labels[1]

        # Map only samples that have a condition assignment
        sample_mask = adata.obs_names.isin(conditions.keys())
        if sample_mask.sum() < 4:
            return adata

        adata_sub = adata[sample_mask].copy()
        adata_sub.obs["condition"] = [
            conditions.get(s, "unknown") for s in adata_sub.obs_names
        ]

        idx_a = adata_sub.obs["condition"] == group_a_label
        idx_b = adata_sub.obs["condition"] == group_b_label

        mat = adata_sub.X
        if hasattr(mat, "toarray"):
            mat = mat.toarray()
        mat = np.asarray(mat, dtype=np.float64)

        results: list[dict] = []
        for j in range(adata_sub.n_vars):
            vals_a = mat[idx_a, j]
            vals_b = mat[idx_b, j]

            mean_a = float(np.mean(vals_a))
            mean_b = float(np.mean(vals_b))
            log2fc = mean_b - mean_a  # already log-space (log1p CPM)

            try:
                t_stat, p_val = stats.ttest_ind(vals_a, vals_b, equal_var=False)
                p_val = float(p_val)
            except Exception:
                p_val = 1.0

            results.append(
                {
                    "gene": adata_sub.var_names[j],
                    "log2fc": round(log2fc, 4),
                    "pvalue": p_val,
                    "mean_a": round(mean_a, 4),
                    "mean_b": round(mean_b, 4),
                    "group_a": group_a_label,
                    "group_b": group_b_label,
                }
            )

        de_df = pd.DataFrame(results)

        # Multiple-testing correction (Benjamini-Hochberg)
        from statsmodels.stats.multitest import multipletests  # type: ignore[import-not-found]

        try:
            _, padj, _, _ = multipletests(de_df["pvalue"].values, method="fdr_bh")
            de_df["padj"] = padj
        except Exception:
            de_df["padj"] = de_df["pvalue"]

        de_df = de_df.sort_values("pvalue")
        adata.uns["de_results"] = de_df

        # Also store condition labels on obs for the full AnnData
        adata.obs["condition"] = [conditions.get(s, "unknown") for s in adata.obs_names]

        return adata
