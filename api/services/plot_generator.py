"""Generate Plotly JSON dicts for every supported visualisation.

Works with plain dict results from the lightweight pipelines (no anndata dependency).
"""

from __future__ import annotations

from typing import Any

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
    def umap_plot(result: dict[str, Any]) -> dict[str, Any]:
        """UMAP plot coloured by cluster."""
        embeddings = np.array(result["umap_embeddings"])
        clusters = [str(c) for c in result["clusters"]]

        df = pd.DataFrame(
            {
                "UMAP1": embeddings[:, 0],
                "UMAP2": embeddings[:, 1],
                "Cluster": clusters,
            }
        )
        fig = px.scatter(
            df,
            x="UMAP1",
            y="UMAP2",
            color="Cluster",
            title="UMAP - Cell Clusters",
            template="plotly_white",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_traces(marker=dict(size=3, opacity=0.7))
        fig.update_layout(width=800, height=600)
        return fig.to_dict()

    @staticmethod
    def qc_violin_plot(result: dict[str, Any]) -> dict[str, Any]:
        """QC metrics: genes per cell and total counts distributions."""
        genes = result.get("genes_per_cell", [])
        counts = result.get("total_counts", [])

        fig = go.Figure()
        if genes:
            fig.add_trace(
                go.Violin(
                    y=genes,
                    name="Genes/Cell",
                    box_visible=True,
                    meanline_visible=True,
                )
            )
        if counts:
            fig.add_trace(
                go.Violin(
                    y=counts,
                    name="Total Counts",
                    box_visible=True,
                    meanline_visible=True,
                )
            )

        if not genes and not counts:
            return PlotGenerator._empty_figure("No QC metrics available")

        fig.update_layout(
            title="QC Metrics",
            template="plotly_white",
            showlegend=False,
            width=700,
            height=500,
        )
        return fig.to_dict()

    @staticmethod
    def heatmap_top_genes(result: dict[str, Any]) -> dict[str, Any]:
        """Heatmap of top marker genes across clusters."""
        gene_names = result.get("top_gene_names", [])
        expression = result.get("top_gene_expression", [])
        clusters = result.get("clusters", [])

        if not gene_names or not expression:
            return PlotGenerator._empty_figure("No marker genes found")

        expr_df = pd.DataFrame(expression, columns=gene_names)
        expr_df["cluster"] = clusters

        # Average expression per cluster
        cluster_means = expr_df.groupby("cluster")[gene_names].mean()

        fig = go.Figure(
            data=go.Heatmap(
                z=cluster_means.values,
                x=gene_names,
                y=[f"Cluster {c}" for c in cluster_means.index],
                colorscale="Viridis",
            )
        )
        fig.update_layout(
            title="Top Marker Genes by Cluster",
            template="plotly_white",
            width=900,
            height=500,
            xaxis_title="Gene",
            yaxis_title="Cluster",
            xaxis_tickangle=-45,
        )
        return fig.to_dict()

    @staticmethod
    def gene_expression_dotplot(
        result: dict[str, Any], genes: list[str] | None = None
    ) -> dict[str, Any]:
        """Dot plot of gene expression across clusters."""
        if not genes:
            genes = result.get("top_gene_names", [])[:10]

        expression = result.get("top_gene_expression", [])
        clusters = result.get("clusters", [])
        gene_names = result.get("top_gene_names", [])

        if not expression or not clusters or not gene_names:
            return PlotGenerator._empty_figure("No expression data")

        expr_df = pd.DataFrame(expression, columns=gene_names)
        expr_df["cluster"] = clusters

        # Filter to requested genes that exist
        plot_genes = [g for g in genes if g in gene_names][:10]
        if not plot_genes:
            return PlotGenerator._empty_figure("No matching genes")

        dots: list[dict] = []
        for gene in plot_genes:
            for cluster in sorted(set(clusters)):
                mask = expr_df["cluster"] == cluster
                vals = expr_df.loc[mask, gene]
                dots.append(
                    {
                        "gene": gene,
                        "cluster": f"Cluster {cluster}",
                        "mean_expr": float(vals.mean()),
                        "pct_expressing": float((vals > 0).mean() * 100),
                    }
                )

        dot_df = pd.DataFrame(dots)

        fig = px.scatter(
            dot_df,
            x="gene",
            y="cluster",
            size="pct_expressing",
            color="mean_expr",
            color_continuous_scale="Viridis",
            title="Gene Expression Dot Plot",
            template="plotly_white",
        )
        fig.update_layout(width=900, height=500, xaxis_tickangle=-45)
        return fig.to_dict()

    # ------------------------------------------------------------------
    # Shared / bulk plots
    # ------------------------------------------------------------------

    @staticmethod
    def pca_variance_plot(result: dict[str, Any]) -> dict[str, Any]:
        """Scree plot: variance explained by each PC."""
        variance = result.get("pca_variance_ratio", [])
        if not variance:
            return PlotGenerator._empty_figure("No PCA data")

        cumulative = np.cumsum(variance).tolist()
        n = len(variance)

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=[f"PC{i+1}" for i in range(n)],
                y=[v * 100 for v in variance],
                marker_color="steelblue",
                name="Individual",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[f"PC{i+1}" for i in range(n)],
                y=[c * 100 for c in cumulative],
                mode="lines+markers",
                name="Cumulative",
                marker_color="firebrick",
            )
        )
        fig.update_layout(
            title="PCA Variance Explained",
            yaxis_title="Variance Explained (%)",
            xaxis_title="Principal Component",
            template="plotly_white",
            width=800,
            height=500,
        )
        return fig.to_dict()

    @staticmethod
    def sample_correlation_heatmap(result: dict[str, Any]) -> dict[str, Any]:
        """Sample-sample correlation matrix."""
        corr = result.get("correlation_matrix", [])
        labels = result.get("correlation_labels", [])

        if not corr:
            return PlotGenerator._empty_figure("No correlation data")

        # Truncate labels if too many samples
        display_labels = (
            labels
            if len(labels) <= 50
            else [s[:12] for s in labels]
        )

        fig = go.Figure(
            data=go.Heatmap(
                z=corr,
                x=display_labels,
                y=display_labels,
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
    def volcano_plot(de_results: list[dict] | pd.DataFrame) -> dict[str, Any]:
        """Volcano plot from DE results (list of dicts or DataFrame)."""
        if de_results is None:
            return PlotGenerator._empty_figure("No DE results for volcano")

        if isinstance(de_results, list):
            if not de_results:
                return PlotGenerator._empty_figure("No DE results for volcano")
            df = pd.DataFrame(de_results)
        else:
            df = de_results.copy()
            if df.empty:
                return PlotGenerator._empty_figure("No DE results for volcano")

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
            labels={
                "log2fc": "log2 Fold Change",
                "neg_log10p": "-log10(p-value)",
            },
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
            font=dict(size=16, color="gray"),
        )
        fig.update_layout(
            template="plotly_white",
            width=600,
            height=400,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
        )
        return fig.to_dict()
