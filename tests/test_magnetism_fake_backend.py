from mvpipeline.magnetism import MagnetismInput, MagnetismStatus
from mvpipeline.magnetism.backends import FakeMagnetismBackend


def test_fake_magnetism_backend_is_deterministic_and_structured():
    backend = FakeMagnetismBackend()
    item = MagnetismInput(
        structure_id="mag-1",
        structure=object(),
        composition={"Fe": 2, "O": 3},
    )

    first = backend.predict(item)
    second = backend.predict(item)

    assert first == second
    assert first.structure_id == "mag-1"
    assert first.status == MagnetismStatus.OK
    assert first.error_code == ""
    assert first.predicted_moment_value == 0.5
    assert first.moment_unit == "unknown"
    assert first.moment_normalization == "unknown"
    assert first.uncertainty_proxy == 0.005


def test_fake_magnetism_backend_returns_structured_error():
    backend = FakeMagnetismBackend()
    item = MagnetismInput(
        structure_id="bad-mag",
        structure=object(),
        features=["not-a-number"],
    )

    result = backend.predict(item)

    assert result.structure_id == "bad-mag"
    assert result.status == MagnetismStatus.ERROR
    assert result.error_code == "fake_magnetism_error"
    assert result.error_message
