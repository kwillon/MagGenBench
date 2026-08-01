"""Pipeline orchestration package."""


def run_validation(*args, **kwargs):
    """Lazily run the validation pipeline."""

    from .runner import run_validation as _run_validation

    return _run_validation(*args, **kwargs)


__all__ = [
    "run_validation",
]
