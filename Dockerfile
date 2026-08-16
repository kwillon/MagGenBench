FROM python:3.11-slim AS runtime

ENV MPLBACKEND=Agg \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

RUN python -m pip install --upgrade pip setuptools wheel && \
    python -m pip install \
        matplotlib \
        numpy \
        pandas \
        pytest \
        pyyaml \
        rich \
        typer

COPY pyproject.toml README.md ./
COPY src ./src

RUN python -m pip install .

WORKDIR /workspace

CMD ["maggenbench", "--help"]


FROM runtime AS test

WORKDIR /build

COPY tests ./tests
COPY scripts ./scripts

CMD ["python", "-m", "pytest", "-q", \
    "tests/test_analysis_v1_figures.py", \
    "tests/test_maggenbench_cli.py", \
    "tests/test_reproduction_analysis_v1.py", \
    "tests/test_unified_analysis.py", \
    "tests/test_analysis_cohorts.py", \
    "tests/test_analysis_plotting.py", \
    "tests/test_dependency_light_imports.py"]
