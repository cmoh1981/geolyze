"""Download and parse GEO datasets via GEOparse."""

from __future__ import annotations

import os
import urllib.request
from pathlib import Path
from typing import Any

import GEOparse
import pandas as pd


class GEODownloader:
    """Handles fetching a GEO Series and extracting the expression matrix."""

    def __init__(self, data_dir: str) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def download(self, geo_id: str) -> dict[str, Any]:
        """Download *geo_id*, return metadata dict + expression DataFrame.

        Raises ``ValueError`` if no usable expression matrix can be found.
        """
        dest = self.data_dir / geo_id
        dest.mkdir(parents=True, exist_ok=True)

        gse = GEOparse.get_GEO(geo=geo_id, destdir=str(dest), silent=True)

        metadata = self._extract_metadata(gse)
        expression = self._extract_expression(gse, dest)

        if expression is None:
            raise ValueError(
                "No expression matrix found. This dataset may only contain "
                "raw sequencing files (FASTQ/BAM) which are not supported yet."
            )

        return {
            "metadata": metadata,
            "expression": expression,
            "gse": gse,
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_metadata(gse: GEOparse.GEOTypes.GSE) -> dict[str, Any]:
        meta = gse.metadata

        # Organism can live in several places
        organism_raw = meta.get(
            "organism_ch1",
            meta.get("sample_organism_ch1", ["Unknown"]),
        )
        if isinstance(organism_raw, list):
            organism = organism_raw[0] if organism_raw else "Unknown"
        else:
            organism = str(organism_raw)

        return {
            "title": meta.get("title", ["Unknown"])[0],
            "summary": meta.get("summary", ["No summary"])[0],
            "organism": organism,
            "platform": list(gse.gpls.keys()),
            "n_samples": len(gse.gsms),
            "type": meta.get("type", ["Unknown"])[0],
            "pubmed_id": meta.get("pubmed_id", [None])[0],
        }

    @staticmethod
    def _extract_expression(
        gse: GEOparse.GEOTypes.GSE,
        dest: Path,
    ) -> pd.DataFrame | None:
        """Try multiple strategies to build a genes-by-samples DataFrame."""

        # Strategy 1: pivot VALUE column across GSMs
        try:
            pivoted = gse.pivot_samples("VALUE")
            if pivoted is not None and not pivoted.empty:
                # Drop rows that are entirely NaN
                pivoted = pivoted.dropna(how="all")
                if not pivoted.empty:
                    return pivoted
        except Exception:
            pass

        # Strategy 2: download supplementary compressed tables
        suppl_files: list[str] = gse.metadata.get("supplementary_file", [])
        for url in suppl_files:
            if not any(
                url.endswith(ext)
                for ext in (".txt.gz", ".tsv.gz", ".csv.gz", ".tab.gz")
            ):
                continue
            try:
                local_path = str(dest / os.path.basename(url))
                urllib.request.urlretrieve(url, local_path)

                sep = "," if ".csv" in url else "\t"
                df = pd.read_csv(
                    local_path, sep=sep, index_col=0, compression="gzip"
                )
                if df.shape[0] > 1 and df.shape[1] > 1:
                    return df
            except Exception:
                continue

        return None
