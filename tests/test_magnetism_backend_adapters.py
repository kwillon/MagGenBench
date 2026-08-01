import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from mvpipeline.magnetism import MagnetismInput, MagnetismStatus
from mvpipeline.magnetism.backends import (
    FakeMagnetismBackend,
    SklearnMagnetismBackend,
    create_magnetism_backend,
)
from mvpipeline.magnetism.config import (
    MagnetismBackendSettings,
    MagnetismModelMetadata,
)
from mvpipeline.magnetism.predictor import (
    confidence_from_uncertainty_proxy,
    risk_level_from_confidence,
)


class LinearModel:
    def __init__(self):
        self.calls = 0
        self.n_features_in_ = 3

    def predict(self, rows):
        self.calls += 1
        return [sum(rows[0])]


class NoPredictModel:
    pass


class StubFeaturizer:
    feature_set = "composition_magpie"
    feature_labels = ("f1", "f2", "f3")

    def featurize(self, composition):
        return [composition.get("Fe", 0.0), composition.get("O", 0.0), 1.0]


def metadata(**overrides):
    values = {
        "model_name": "stub-magnetism",
        "artifact_path": "models/magnetism/stub.pkl",
        "feature_set": "composition_magpie",
        "feature_labels": ("f1", "f2", "f3"),
        "feature_count": 3,
        "moment_unit": "unknown",
        "moment_normalization": "unknown",
    }
    values.update(overrides)
    return MagnetismModelMetadata(**values)


def settings(**overrides):
    values = {
        "name": "sklearn",
        "model_name": "stub-magnetism",
        "artifact_path": "models/magnetism/stub.pkl",
        "uncertainty_samples": 0,
        "metadata": metadata(),
    }
    values.update(overrides)
    return MagnetismBackendSettings(**values)


def item(features=None):
    return MagnetismInput(
        structure_id="mag-1",
        structure=object(),
        composition={"Fe": 2, "O": 3},
        features=features,
    )


def test_magnetism_backend_module_imports_without_optional_dependencies():
    repo_root = Path(__file__).resolve().parents[1]
    script = textwrap.dedent(
        """
        import builtins
        import importlib
        import sys

        blocked = {"matminer", "sklearn", "joblib", "pymatgen", "numpy"}
        real_import = builtins.__import__

        def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
            root = name.split(".", 1)[0]
            if level == 0 and root in blocked:
                raise AssertionError(
                    f"{name} must not be imported at module import time"
                )
            return real_import(name, globals, locals, fromlist, level)

        builtins.__import__ = guarded_import
        importlib.import_module("mvpipeline.magnetism")
        importlib.import_module("mvpipeline.magnetism.backends.sklearn")
        assert not [m for m in sys.modules if m.split(".", 1)[0] in blocked]
        """
    )
    env = dict(os.environ)
    src_path = str(repo_root / "src")
    env["PYTHONPATH"] = (
        src_path
        if not env.get("PYTHONPATH")
        else src_path + os.pathsep + env["PYTHONPATH"]
    )

    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        env=env,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stderr


def test_factory_selects_fake_and_sklearn_backends():
    fake = create_magnetism_backend("fake")
    sklearn = create_magnetism_backend(settings())

    assert isinstance(fake, FakeMagnetismBackend)
    assert isinstance(sklearn, SklearnMagnetismBackend)


def test_injectable_model_loader_and_featurizer_are_used_once():
    model = LinearModel()
    loader_calls = []

    def loader(path):
        loader_calls.append(path)
        return model

    backend = SklearnMagnetismBackend(
        settings=settings(),
        model_loader=loader,
        featurizer=StubFeaturizer(),
    )

    first = backend.predict(item())
    second = backend.predict(item())

    assert loader_calls == ["models/magnetism/stub.pkl"]
    assert model.calls == 2
    assert first == second
    assert first.status == MagnetismStatus.OK
    assert first.predicted_moment_value == 6.0
    assert first.moment_unit == "unknown"
    assert first.moment_normalization == "unknown"
    assert first.details["feature_set"] == "composition_magpie"


def test_feature_count_mismatch_returns_structured_error():
    backend = SklearnMagnetismBackend(
        settings=settings(),
        model_loader=lambda path: LinearModel(),
    )

    result = backend.predict(item(features=[1.0, 2.0]))

    assert result.status == MagnetismStatus.ERROR
    assert result.error_code == "prediction_contract_error"
    assert "Feature count mismatch" in result.error_message


def test_empty_feature_vector_returns_structured_error():
    backend = SklearnMagnetismBackend(
        settings=settings(),
        model_loader=lambda path: LinearModel(),
    )

    result = backend.predict(item(features=[]))

    assert result.status == MagnetismStatus.ERROR
    assert result.error_code == "prediction_contract_error"
    assert "must not be empty" in result.error_message


def test_nan_or_inf_features_return_structured_error():
    backend = SklearnMagnetismBackend(
        settings=settings(),
        model_loader=lambda path: LinearModel(),
    )

    result = backend.predict(item(features=[1.0, float("inf"), 3.0]))

    assert result.status == MagnetismStatus.ERROR
    assert result.error_code == "prediction_contract_error"
    assert "NaN or infinite" in result.error_message


def test_model_without_predict_returns_structured_error():
    backend = SklearnMagnetismBackend(
        settings=settings(),
        model_loader=lambda path: NoPredictModel(),
    )

    result = backend.predict(item(features=[1.0, 2.0, 3.0]))

    assert result.status == MagnetismStatus.ERROR
    assert result.error_code == "prediction_contract_error"
    assert "does not provide predict" in result.error_message


def test_malformed_non_scalar_prediction_returns_structured_error():
    class BadModel:
        n_features_in_ = 3

        def predict(self, rows):
            return [1.0, 2.0]

    backend = SklearnMagnetismBackend(
        settings=settings(),
        model_loader=lambda path: BadModel(),
    )

    result = backend.predict(item(features=[1.0, 2.0, 3.0]))

    assert result.status == MagnetismStatus.ERROR
    assert result.error_code == "prediction_contract_error"
    assert "exactly one value" in result.error_message


def test_metadata_defaults_unknown_unit_and_normalization():
    meta = MagnetismModelMetadata(
        model_name="unknown-target",
        artifact_path="models/magnetism/model.pkl",
        feature_labels=("f1",),
        feature_count=1,
    )

    assert meta.moment_unit == "unknown"
    assert meta.moment_normalization == "unknown"


def test_missing_optional_dependency_returns_structured_error():
    backend = SklearnMagnetismBackend(
        settings=settings(metadata=metadata(feature_labels=("f1",))),
        model_loader=lambda path: (_ for _ in ()).throw(
            ImportError("missing joblib")
        ),
    )

    result = backend.predict(item(features=[1.0]))

    assert result.status == MagnetismStatus.ERROR
    assert result.error_code == "missing_optional_dependency"
    assert "missing joblib" in result.error_message


def test_deterministic_uncertainty_proxy_with_fixed_seed():
    backend = SklearnMagnetismBackend(
        settings=settings(uncertainty_samples=4, uncertainty_noise=0.1),
        model_loader=lambda path: LinearModel(),
        noise_generator=lambda features, scale, rng: [
            value + rng.gauss(0.0, scale) for value in features
        ],
    )

    first = backend.predict(item(features=[1.0, 2.0, 3.0]))
    second = backend.predict(item(features=[1.0, 2.0, 3.0]))

    assert first.uncertainty_proxy == pytest.approx(second.uncertainty_proxy)
    assert first.uncertainty_proxy > 0.0


def test_confidence_and_risk_are_pure_functions():
    confidence = confidence_from_uncertainty_proxy(0.25, 0.25)

    assert confidence == pytest.approx(0.50000001)
    assert risk_level_from_confidence(0.9) == "low"
    assert risk_level_from_confidence(confidence) == "medium"
    assert risk_level_from_confidence(0.1) == "high"


def test_unexpected_model_exception_propagates():
    class ExplodingModel:
        n_features_in_ = 3

        def predict(self, rows):
            raise RuntimeError("model exploded")

    backend = SklearnMagnetismBackend(
        settings=settings(),
        model_loader=lambda path: ExplodingModel(),
    )

    with pytest.raises(RuntimeError, match="model exploded"):
        backend.predict(item(features=[1.0, 2.0, 3.0]))


def test_missing_feature_order_returns_structured_error():
    backend = SklearnMagnetismBackend(
        settings=settings(metadata=metadata(feature_labels=(), feature_count=3)),
        model_loader=lambda path: LinearModel(),
    )

    result = backend.predict(item(features=[1.0, 2.0, 3.0]))

    assert result.status == MagnetismStatus.ERROR
    assert result.error_code == "prediction_contract_error"
    assert "feature order" in result.error_message


def test_importing_sklearn_backend_does_not_load_model():
    calls = []
    backend = SklearnMagnetismBackend(
        settings=settings(),
        model_loader=lambda path: calls.append(path),
    )

    assert backend.model_name == "stub-magnetism"
    assert calls == []
