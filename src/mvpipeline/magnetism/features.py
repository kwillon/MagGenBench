from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence, Tuple


class CompositionFeatureProvider(Protocol):
    feature_set: str
    feature_labels: Sequence[str]

    def featurize(self, composition: Any) -> Sequence[float]:
        """Return a composition-only feature vector."""


@dataclass
class MagpieCompositionFeatureProvider:
    """Composition-only Magpie feature provider.

    The optional matminer dependency is imported only when features are built.
    """

    feature_set: str = "composition_magpie"
    _featurizer: object = field(default=None, init=False, repr=False)
    _feature_labels: Tuple[str, ...] = field(default_factory=tuple, init=False)

    @property
    def feature_labels(self) -> Sequence[str]:
        featurizer = self._load_featurizer()
        if not self._feature_labels and hasattr(featurizer, "feature_labels"):
            self._feature_labels = tuple(str(x) for x in featurizer.feature_labels())
        return self._feature_labels

    def _load_featurizer(self) -> object:
        if self._featurizer is None:
            try:
                from matminer.featurizers.composition import ElementProperty
            except ImportError as exc:
                raise ImportError(
                    "Magpie composition features require optional dependency "
                    "'matminer'."
                ) from exc
            self._featurizer = ElementProperty.from_preset("magpie")
        return self._featurizer

    def featurize(self, composition: Any) -> Sequence[float]:
        featurizer = self._load_featurizer()
        return featurizer.featurize(composition)
