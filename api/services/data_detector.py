"""Heuristic detection of bulk vs single-cell expression data."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd


# Keywords that strongly suggest single-cell data
_SC_KEYWORDS = re.compile(
    r"single.?cell|scRNA|scrna|10x\s?genomics|drop.?seq|smart.?seq|"
    r"chromium|cel.?seq|indrop|sci.?rna|snRNA|snrna|single.?nucleus",
    re.IGNORECASE,
)


class DataDetector:
    """Classify an expression matrix as ``single_cell`` or ``bulk``."""

    def detect(
        self,
        expression: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> str:
        """Return ``"single_cell"`` or ``"bulk"``."""
        score = 0  # positive = single-cell, negative = bulk

        # 1. Keyword scan across all metadata string values
        meta_text = " ".join(
            str(v) for v in self._flatten_metadata(metadata)
        )
        if _SC_KEYWORDS.search(meta_text):
            score += 3

        # 2. Sample count heuristic
        n_samples = expression.shape[1]
        if n_samples > 500:
            score += 2
        elif n_samples > 100:
            score += 1
        elif n_samples <= 30:
            score -= 2

        # 3. Sparsity heuristic -- single-cell matrices are usually very sparse
        try:
            sparsity = (expression == 0).sum().sum() / expression.size
            if sparsity > 0.7:
                score += 1
        except Exception:
            pass

        return "single_cell" if score >= 2 else "bulk"

    # ------------------------------------------------------------------

    @staticmethod
    def _flatten_metadata(meta: dict) -> list[str]:
        """Recursively collect all string values from metadata."""
        values: list[str] = []
        for v in meta.values():
            if isinstance(v, str):
                values.append(v)
            elif isinstance(v, list):
                values.extend(str(x) for x in v)
            elif isinstance(v, dict):
                values.extend(
                    str(x) for x in v.values()
                )
        return values
