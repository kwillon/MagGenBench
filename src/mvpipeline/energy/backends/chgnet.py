from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ..formation import formation_energy_proxy, formation_energy_proxy_per_atom
from ..proxies import positive_formation_energy_proxy
from ..references import ReferenceEnergyProvider
from ..schema import EnergyInput, EnergyResult, EnergyStatus
from ._normalization import normalize_energy

ModelLoader = Callable[[str, str], Any]


def _default_model_loader(model_selector: str, device: str) -> Any:
    try:
        from chgnet.model import CHGNet
    except ImportError as exc:
        raise ImportError(
            "CHGNet backend requires optional dependency 'chgnet'."
        ) from exc

    if model_selector and model_selector != "default":
        model = CHGNet.load(model_selector)
    else:
        model = CHGNet.load()
    if device != "auto" and hasattr(model, "to"):
        model = model.to(device)
    return _CHGNetLoadedModel(model=model)


@dataclass
class _CHGNetLoadedModel:
    model: Any

    def predict_energy(self, structure: Any) -> Any:
        out = self.model.predict_structure(structure)
        if not isinstance(out, dict):
            raise ValueError("CHGNet output must be a dict")
        if "e" not in out:
            raise ValueError("CHGNet output dict has no 'e' field")
        return out["e"]


@dataclass
class CHGNetBackend:
    model_name: str = "default"
    model_selector: str = "default"
    device: str = "auto"
    output_semantics: str = "energy_per_atom_eV"
    model_loader: ModelLoader = _default_model_loader
    reference_provider: Optional[ReferenceEnergyProvider] = None
    name: str = "chgnet"
    _model: Any = field(default=None, init=False, repr=False)

    def _load_model(self) -> Any:
        if self._model is None:
            self._model = self.model_loader(self.model_selector, self.device)
        return self._model

    def predict(self, item: EnergyInput) -> EnergyResult:
        if item.n_atoms <= 0:
            return self._error(
                item.structure_id,
                "invalid_n_atoms",
                "n_atoms must be positive",
            )

        try:
            model = self._load_model()
        except ImportError as exc:
            return self._error(
                item.structure_id,
                "missing_optional_dependency",
                str(exc),
            )

        try:
            raw_energy = model.predict_energy(item.structure)
            total, per_atom = normalize_energy(
                raw_energy, self.output_semantics, item.n_atoms
            )
            form_proxy = None
            form_proxy_per_atom = None
            stability_proxy = None
            if self.reference_provider is not None:
                refs = {
                    element: self.reference_provider.get_reference_energy_eV(element)
                    for element in item.composition
                }
                form_proxy = formation_energy_proxy(
                    total_energy_eV=total,
                    composition=item.composition,
                    isolated_atom_reference_eV=refs,
                )
                form_proxy_per_atom = formation_energy_proxy_per_atom(
                    formation_energy_proxy_eV=form_proxy,
                    n_atoms=item.n_atoms,
                )
                stability_proxy = positive_formation_energy_proxy(form_proxy_per_atom)
        except ValueError as exc:
            return self._error(item.structure_id, "model_output_error", str(exc))

        return EnergyResult(
            structure_id=item.structure_id,
            status=EnergyStatus.OK,
            backend=self.name,
            model_name=self.model_name,
            energy_unit="eV",
            total_energy_eV=total,
            total_energy_eV_per_atom=per_atom,
            formation_energy_proxy_eV=form_proxy,
            formation_energy_proxy_eV_per_atom=form_proxy_per_atom,
            stability_energy_proxy_eV_per_atom=stability_proxy,
            details={
                "device": self.device,
                "model_selector": self.model_selector,
                "output_semantics": self.output_semantics,
            },
        )

    def _error(self, structure_id: str, code: str, message: str) -> EnergyResult:
        return EnergyResult(
            structure_id=structure_id,
            status=EnergyStatus.ERROR,
            error_code=code,
            error_message=message,
            backend=self.name,
            model_name=self.model_name,
        )
