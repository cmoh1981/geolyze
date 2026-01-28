"""Generate Plotly JSON dicts for every supported visualisation."""

from __future__ import annotations

from typing import Any

import anndata as ad
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


class PlotGenerator:
    """Stateless helpers that each return a Plotly figure dict (JSON-ready)."""

    # ------------------------------------------------------------------
    # Single-cell plots
    # ------------------------------------------------------------------

    @staticmethod
    def umap_plot(adata: ad.AnnData) -> dict[str, Any]:
        """UMAP coloured by Leiden cluster."""
        df = pd.DataFrame(
            {
                "UMAP1": adata.obsm["X_umap"][:, 0],
                "UMAP2": adata.obsm["X_umap"][:, 1],
                "Cluster": adata.obs["leiden"].astype(str).values,
            }
        )
        fig = px.scatter(
            df,
            x="UMAP1",
            y="UMAP2",
            color="Cluster",
            title="UMAP - Leiden Clusters",
            template="plotly_white",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_traces(marker=dict(size=3, opacity=0.7))
        fig.update_layout(width=800, height=600)
        return fig.to_dict()

    @staticmethod
    def qc_violin_plot(adata: ad.AnnData) -> dict[str, Any]:
        """Violin plots for key QC metrics (n_genes, total_counts, pct_mito)."""
        metrics = []
        values = []

        if "n_genes_by_counts" in adata.obs.columns:
            metrics += ["n_genes"] * adata.n_obs
            values += adata.obs["n_genes_by_counts"].tolist()

        if "total_counts" in adata.obs.columns:
            metrics += ["total_counts"] * adata.n_obs
            values += adata.obs["total_counts"].tolist()

        if "pct_counts_mt" in adata.obs.columns:
            metrics += ["pct_mito"] * adata.n_obs
            values += adata.obs["pct_counts_mt"].tolist()

        if not metrics:
            return PlotGenerator._empty_figure("No QC metrics available")

        df = pd.DataFrame({"metric": metrics, "value": values})
        fig = px.violin(
            df,
            x="metric",
            y="value",
            color="metric",
            box=True,
            title="QC Metrics",
            template="plotly_white",
        )
        fig.update_layout(showlegend=False, width=700, height=500)
        return fig.to_dict()

    @staticmethod
    def heatmap_top_genes(
        adata: ad.AnnData, n_genes: int = 10
    ) -> dict[str, Any]:
        """Heatmap of the top *n_genes* marker genes per cluster."""
        if "rank_genes_groups" not in adata.uns:
            return PlotGenerator._empty_figure("No DE results for heatmap")

        rgg = adata.uns["rank_genes_groups"]
        groups = list(rgg["names"].dtype.names)

        gene_names: list[str] = []
        for g in groups:
            names = rgg["names"][g][:n_genes].tolist()
            gene_names.extend(names)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_genes: list[str] = []
        for gn in gene_names:
            if gn not in seen:
                seen.add(gn)
                unique_genes.append(gn)

        # Subset expression matrix
        valid_genes = [g for g in unique_genes if g in adata.var_names]
        if not valid_genes:
            return PlotGenerator._empty_figure("Marker genes not found in var_names")

        mat = adata[:, valid_genes].X
        if hasattr(mat, "toarray"):
            mat = mat.toarray()
        mat = np.asarray(mat, dtype=np.float64)

        # Mean expression per cluster
        clusters = adata.obs["leiden"].values
        unique_clusters = sorted(set(clusters), key=lambda c: int(c) if c.isdigit() else c)

        z: list[list[float]] = []
        for cl in unique_clusters:
            mask = clusters == cl
            z.append(mat[mask].mean(axis=0).tolist())

        fig = go.Figure(
            data=go.Heatmap(
                z=z,
                x=valid_genes,
                y=[f"Cluster {c}" for c in unique_clusters],
                colorscale="Viridis",
            )
        )
        fig.update_layout(
            title="Top Marker Genes per Cluster",
            template="plotly_white",
            width=900,
            height=500,
            xaxis_tickangle=-45,
        )
        return fig.to_dict()

    @staticmethod
    def gene_expression_dotplot(
        adata: ad.AnnData, genes: list[str] | None = None
    ) -> dict[str, Any]:
        """Dot plot of gene expression across clusters.

        If *genes* is ``None``, the top-3 markers per cluster are used.
        """
        if genes is None:
            if "rank_genes_groups" not in adata.uns:
                return PlotGenerator._empty_figure("No genes for dot plot")
            rgg = adata.uns["rank_genes_groups"]
            groups = list(rgg["names"].dtype.names)
            genes = []
            for g in groups:
                genes.extend(rgg["names"][g][:3].tolist())
            # Deduplicate
            seen: set[str] = set()
            genes = [g for g in genes if g not in seen and not seen.add(g)]  # type: ignore[func-returns-value]

        valid_genes = [g for g in genes if g in adata.var_names]
        if not valid_genes:
            return PlotGenerator._empty_figure("No valid genes for dot plot")

        clusters = adata.obs["leiden"].values
        unique_clusters = sorted(set(clusters), key=lambda c: int(c) if c.isdigit() else c)

        mat = adata[:, valid_genes].X
        if hasattr(mat, "toarray"):
            mat = mat.toarray()
        mat = np.asarray(mat, dtype=np.float64)

        rows: list[dict] = []
        for ci, cl in enumerate(unique_clusters):
            mask = clusters == cl
            sub = mat[mask]
            for gi, gene in enumerate(valid_genes):
                mean_expr = float(sub[:, gi].mean())
                pct_expr = float((sub[:, gi] > 0).mean() * 100)
                rows.append(
                    {
                        "Cluster": str(cl),
                        "Gene": gene,
                        "Mean Expression": mean_expr,
                        "% Expressing": pct_expr,
                    }
                )

        df = pd.DataFrame(rows)
        fig = px.scatter(
            df,
            x="Gene",
            y="Cluster",
            size="% Expressing",
            color="Mean Expression",
            title="Gene Expression Dot Plot",
            template="plotly_white",
            color_continuous_scale="Viridis",
        )
        fig.update_layout(width=900, height=500, xaxis_tickangle=-45)
        return fig.to_dict()

    # ------------------------------------------------------------------
    # Shared / bulk plots
    # ------------------------------------------------------------------

    @staticmethod
    def pca_variance_plot(adata: ad.AnnData) -> dict[str, Any]:
        """Scree plot: variance explained by each PC."""
        if "pca" not in adata.uns:
            return PlotGenerator._empty_figure("PCA not computed")

        variance_ratio = adata.uns["pca"]["variance_ratio"]
        n = len(variance_ratio)
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=[f"PC{i+1}" for i in range(n)],
                y=variance_ratio,
                marker_color="steelblue",
                name="Individual",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[f"PC{i+1}" for i in range(n)],
                y=np.cumsum(variance_ratio).tolist(),
                mode="lines+markers",
                name="Cumulative",
                marker_color="firebrick",
            )
        )
        fig.update_layout(
            title="PCA Variance Explained",
            yaxis_title="Proportion of Variance",
            template="plotly_white",
            width=800,
            height=500,
        )
        return fig.to_dict()

    @staticmethod
    def sample_correlation_heatmap(adata: ad.AnnData) -> dict[str, Any]:
        """Sample-sample Pearson correlation matrix."""
        mat = adata.X
        if hasattr(mat, "toarray"):
            mat = mat.toarray()
        mat = np.asarray(mat, dtype=np.float64)

        corr = np.corrcoef(mat)
        sample_names = list(adata.obs_names)

        # Truncate labels if too many samples
        labels = sample_names if len(sample_names) <= 50 else [
            s[:12] for s in sample_names
        ]

        fig = go.Figure(
            data=go.Heatmap(
                z=corr,
                x=labels,
                y=labels,
                colorscale="RdBu_r",
                zmin=-1,
                zmax=1,
            )
        )
        fig.update_layout(
            title="Sample Correlation Matrix",
            template="plotly_white",
            width=800,
            height=700,
            xaxis_tickangle=-45,
        )
        return fig.to_dict()

    @staticmethod
    def volcano_plot(de_results: pd.DataFrame) -> dict[str, Any]:
        """Volcano plot from a DE results DataFrame."""
        if de_results is None or de_results.empty:
            return PlotGenerator._empty_figure("No DE results for volcano")

        df = de_results.copy()

        # Ensure required columns
        if "log2fc" not in df.columns or "pvalue" not in df.columns:
            return PlotGenerator._empty_figure("DE results missing log2fc / pvalue")

        df["neg_log10p"] = -np.log10(df["pvalue"].clip(lower=1e-300))

        padj_col = "padj" if "padj" in df.columns else "pvalue"
        df["significant"] = (df[padj_col] < 0.05) & (df["log2fc"].abs() > 1)
        df["category"] = "NS"
        df.loc[df["significant"] & (df["log2fc"] > 0), "category"] = "Up"
        df.loc[df["significant"] & (df["log2fc"] < 0), "category"] = "Down"

        color_map = {"NS": "grey", "Up": "red", "Down": "blue"}

        fig = px.scatter(
            df,
            x="log2fc",
            y="neg_log10p",
            color="category",
            color_discrete_map=color_map,
            hover_data=["gene"] if "gene" in df.columns else None,
            title="Volcano Plot",
            template="plotly_white",
            labels={"log2fc": "log2 Fold Change", "neg_log10p": "-log10(p-value)"},
        )
        fig.update_traces(marker=dict(size=4, opacity=0.6))

        # Significance thresholds
        fig.add_hline(y=-np.log10(0.05), line_dash="dash", line_color="grey")
        fig.add_vline(x=-1, line_dash="dash", line_color="grey")
        fig.add_vline(x=1, line_dash="dash", line_color="grey")

        fig.update_layout(width=800, height=600)
        return fig.to_dict()

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _empty_figure(message: str) -> dict[str, Any]:
        """Return a minimal Plotly figure dict with an annotation."""
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16),
        )
        fig.update_layout(template="plotly_white", width=600, height=400)
        return fig.to_dict()
