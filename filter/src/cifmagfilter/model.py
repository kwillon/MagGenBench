from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .core import structure_features
from .reference import ReferenceModel


class CIFMagFilter:
    """High-level interface to the bundled magnetic-reference filter.

    The nearest magnetic branch describes affinity to an empirical reference
    manifold. It is not a prediction of the magnetic ground state.
    """

    def __init__(self, reference_model: ReferenceModel):
        self.reference_model = reference_model

    @classmethod
    def from_pretrained(cls, model_dir: str | Path | None = None) -> "CIFMagFilter":
        if model_dir is None:
            model_dir = Path(__file__).resolve().parent / "data" / "model"
        return cls(ReferenceModel.load(model_dir))

    @property
    def feature_names(self) -> list[str]:
        return list(self.reference_model.feature_names)

    def score_features(self, features: pd.DataFrame) -> pd.DataFrame:
        """Score one or more rows of already extracted structure descriptors."""
        missing = [name for name in self.feature_names if name not in features.columns]
        if missing:
            raise ValueError(
                "Input feature table is missing required descriptors: "
                + ", ".join(missing[:10])
                + (" ..." if len(missing) > 10 else "")
            )
        meta_cols = [c for c in ["dataset", "structure_id", "source_path", "formula_reduced"] if c in features.columns]
        meta = features[meta_cols].copy() if meta_cols else pd.DataFrame(index=features.index)
        if "dataset" not in meta:
            meta["dataset"] = "query"
        if "structure_id" not in meta:
            meta["structure_id"] = [f"query_{i}" for i in range(len(features))]
        X, _ = self.reference_model.transform(features)
        return self.reference_model.score(meta, X)

    def score_cif(self, cif: str | Path, *, dataset: str = "query") -> pd.DataFrame:
        """Extract descriptors from a CIF and score it with the bundled model."""
        cif = Path(cif)
        if not cif.exists():
            raise FileNotFoundError(cif)
        _, _, row = structure_features(cif, dataset, pd.DataFrame())
        if row is None or int(row.get("parse_success", 0)) != 1:
            reason = None if row is None else row.get("parse_error")
            raise ValueError(f"Could not extract canonical descriptors from {cif}: {reason}")
        features = pd.DataFrame([row])
        return self.score_features(features)

    def score(self, item: str | Path | pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
        """Score a CIF path or an already extracted feature table."""
        if isinstance(item, pd.DataFrame):
            return self.score_features(item)
        return self.score_cif(item, **kwargs)
