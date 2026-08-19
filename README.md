# MagGenBench

MagGenBench is a scientific benchmark repository for analyzing inorganic crystal structures produced by generative models, with emphasis on magnetic-material discovery signals.

The repository goal is to be self-explanatory and reproducible: reusable code lives under `src/mvpipeline`, active run recipes have semantic locations under `runs/`, generated artifacts are separated from source, and the public execution surface is intentionally small.

## Scientific Scope

MagGenBench currently supports the frozen Analysis v1 workflow. Analysis v1 combines validation, Descriptor v1 structural/composition descriptors, CHGNet energy enrichment, DXMag magnetism enrichment, and plotting into one unified analysis table and a fixed set of paper figures/statistics.

Downstream of Analysis v1, the standardized enrichment table, Magnetic Descriptor v2, and Analysis v2 magnetic table are also frozen scientific artifacts. Magnetic Descriptor v2 and Analysis v2 magnetic are separate layers built from the standardized enrichment interface; they do not rewrite or replace frozen Analysis v1.

The benchmark distinguishes these cohort roles:

- Core baseline model families: MatterGen, Con-CDVAE, CrystalFormer, CrystaLLM.
- Adapted cohorts: MatterGen fine-tuned, Con-CDVAE fine-tuned.
- Comparator cohorts: Crys-JEPA Base, Crys-JEPA Refined.

Crys-JEPA is present in shared analysis infrastructure as a comparator cohort. It is not a fifth core baseline model family.

## Repository Layout

Every top-level directory has a specific role:

| Path | Purpose |
| --- | --- |
| `src/` | Current reusable Python package code. New reusable code belongs under `src/mvpipeline`. |
| `scripts/` | Thin semantic command wrappers and compatibility scripts. Active reusable logic should not live here. |
| `runs/` | Human-readable run recipes, provenance, and stage-level READMEs for reproducible workflows. |
| `config/` | Configuration files used by validation and pipeline stages. |
| `registry/` | Registry-style metadata for models, datasets, runs, and artifacts. |
| `datasets/` | Reference datasets used by validation, novelty, and benchmark workflows. |
| `samples/` | Versioned sample CIF inputs included with the repository where appropriate. |
| `tables/` | Table outputs and table-oriented artifacts. Generated tables should be treated as artifacts, not source. |
| `figures/` | Figure outputs. Reproduced figures are generated artifacts, not reusable code. |
| `paper/` | Policy and future location for manuscript-selected publication figures/tables. |
| `reports/` | Generated reports and audit outputs. |
| `docs/` | Supporting documentation beyond the primary README and architecture notes. |
| `archive/` | Historical scripts and superseded paths retained for provenance only. Current code must not depend on this directory. |
| `tests/` | Unit and regression tests for the current package, wrappers, and reproducibility surface. |

Repository metadata and packaging files live at the root, including `pyproject.toml`, `environment.yml`, `Dockerfile`, and `AGENTS.md` for developer/tooling guidance. Historical audit and refactor planning records live under `archive/docs/`.

## Package Areas

The active package is `mvpipeline`:

| Package | Role |
| --- | --- |
| `mvpipeline.analysis` | Cohort registry, unified analysis helpers, figure-generation logic, Analysis v1 plotting conventions, and Analysis v2 magnetic integration/figure helpers. |
| `mvpipeline.annotations` | Production annotation and manifest preparation helpers. |
| `mvpipeline.descriptors` | Descriptor v1 extraction and schema-preserving descriptor code. |
| `mvpipeline.enrichment` | Post-v1 standardized enrichment registry, manifest preparation, and master-table validation helpers. |
| `mvpipeline.energy` | CHGNet-oriented backend adapters and energy result handling. |
| `mvpipeline.magnetism` | DXMag-oriented backend adapters and magnetism result handling. |
| `mvpipeline.io` | Dependency-light CSV, manifest, CIF, and table IO helpers. |
| `mvpipeline.pipeline` | Shared orchestration helpers for batch stages and enrichment runs. |
| `mvpipeline.validation`, `dedup`, `novelty`, `report`, `utils` | Validation, duplicate checks, novelty checks, report creation, and shared utilities. |
| `mvpipeline.reproduction` | Frozen Analysis v1 reproduction from required inputs. |

## Installation

Use an environment suitable for the lightweight analysis and validation code:

```bash
pip install -e .
```

Heavy model backends are intentionally not forced into this same environment. CHGNet, DXMag, MatterGen, Con-CDVAE, CrystalFormer, CrystaLLM, and Crys-JEPA can have incompatible dependency stacks; model execution should use separate documented backend environments rather than one monolithic Python environment.

## Public Commands

The documented public surface is intentionally small:

```bash
maggenbench reproduce analysis-v1
maggenbench figures analysis-v1
mvp
```

`maggenbench` is the current reproducibility CLI. `mvp` is the existing validation CLI retained for compatibility.

The validation CLI accepts root options such as:

```bash
mvp \
  --input-dir samples/mattergen_cifs \
  --out-dir outputs/mattergen \
  --train-reference datasets/mattergen/train_reference.csv \
  --thresholds config/thresholds.yaml \
  --model-name MatterGen \
  --no-pretty
```

Former phase-style `mvp` subcommands are not packaged entry points in the current repository.

## Reproduce Analysis v1

Analysis v1 can be regenerated from frozen required inputs without rerunning expensive generation, CHGNet, DXMag, descriptor extraction, or model inference:

```bash
maggenbench reproduce analysis-v1 \
  --repo-root . \
  --artifact-root /path/to/artifacts \
  --baseline-joined /path/to/baseline_joined.csv \
  --output-dir reproduced/analysis_v1
```

The reproducer resolves required artifacts in this order:

1. `<repo-root>/<relative-path>`
2. `<artifact-root>/<relative-path>`
3. explicit failure if the artifact is missing

The historical baseline joined table came from a machine-specific production location and is not a good primary user path. Supply it with `--baseline-joined` when reproducing from a fresh clone.

Expected output:

```text
reproduced/analysis_v1/
    unified_analysis_v1.csv
    figures/
        ...
```

The frozen unified table contract is:

- `10684` rows.
- `124` columns.
- `sample_uid` is unique.
- `sample_uid == structure_id`.
- Production cohort identities and counts are frozen: `baseline_master = 4702`, `mattergen_finetuned = 1376`, `concdvae_finetuned = 1299`, `crysjepa_base = 1764`, `crysjepa_refined = 1543`.
- Production status counts are frozen: Descriptor v1 `ok = 10681`, Descriptor v1 `partial = 3`; energy `ok = 10680`, energy `error = 4`; magnetism `ok = 10684`.
- Production cohort order, Descriptor v1 semantics, CHGNet semantics, and DXMag semantics are frozen.
- Expected SHA-256 for `unified_analysis_v1.csv`: `a559a092755a91ea2c9035a08a61a41b8279a81b8dbe2ba52cb888cb17b4cb6c`.

## Generate Analysis v1 Figures

Figures can also be regenerated from an existing unified Analysis v1 CSV:

```bash
maggenbench figures analysis-v1 \
  --input-csv runs/analysis_v1/unified_analysis_v1.csv \
  --output-dir figures/unified_analysis_v1
```

The output directory may already exist. Without `--force`, the command fails only when one or more owned Analysis v1 output files already exist. With `--force`, only those known Analysis v1-owned files are replaced; unrelated files in the directory are preserved, and no recursive directory deletion occurs.

The complete Analysis v1 figure/statistics output set contains 15 files:

- `01_crystal_system_core_baseline.png`
- `02_crystal_system_finetuning.png`
- `03_crystal_system_crysjepa.png`
- `structural_distribution_summary.csv`
- `04_density_distribution.png`
- `05_volume_per_site_distribution.png`
- `06_sites_per_cell_distribution.png`
- `compound_class_distribution_percent.csv`
- `07_compound_class_heatmap.png`
- `3d_4f_fraction_by_cohort.csv`
- `08_3d_4f_fraction_by_cohort.png`
- `magnetic_screening_element_fraction_summary.csv`
- `09_magnetic_screening_element_fraction.png`
- `dxmag_predicted_moment_summary.csv`
- `10_dxmag_predicted_moment_distribution.png`

## Standardized Enrichment

The recommended current per-structure interface for energy and magnetism data
is:

```text
tables/08_standardized_enrichment/standardized_enrichment.csv
```

This post-v1 reference table keeps frozen Analysis v1 unchanged while
publishing symmetric CHGNet and DXMag artifacts for all eight current cohorts:
MatterGen baseline/fine-tuned, Con-CDVAE baseline/fine-tuned, CrystalFormer
baseline, CrystaLLM baseline, Crys-JEPA Base, and Crys-JEPA Refined.

The standardized master has `10684` rows, `87` columns, populated
`formula_reduced` and `formula_full_canonical` for every row, CHGNet status
counts `ok = 10680` and `error = 4`, and DXMag status count `ok = 10684`.
Its SHA-256 is:

`8a62cc9720de9249cdb2c6ce929fa3f98e065ef93c881c1c1160d330940db02d`

See `runs/enrichment/standardized/README.md` and
`tables/README.md` for the standardized run contract and coverage map.

## Run Recipes

Active run recipes live under semantic paths in `runs/`:

- `runs/validation/`
- `runs/annotations/`
- `runs/enrichment/`
- `runs/descriptors/magnetic/`
- `runs/descriptor_v1_full/`
- `runs/analysis_v1/`
- `runs/analysis_v2_magnetic/`

These directories document how frozen production artifacts were prepared and how current workflows are orchestrated. They are not a substitute for reusable package code; shared behavior belongs in `src/mvpipeline`.

Historical phase-based scripts and superseded layouts belong under `archive/` for provenance. Current code must not depend on `archive/` or `scripts/legacy`.

## Data And Artifact Policy

Small, versioned fixtures and metadata can live in Git. Large or machine-specific artifacts should be supplied externally and mounted or passed by path, including:

- Full generated CIF collections.
- Large model checkpoints and binary model artifacts.
- CHGNet, DXMag, and model-backend caches.
- Generated production CSVs when they are too large or are frozen publication artifacts.
- Logs, temporary files, and local reproduction outputs.

Generated outputs should go under explicit artifact locations such as `reproduced/`, `outputs/`, `reports/`, `tables/`, or `figures/` depending on their role. Reproduced outputs are artifacts, not source code. See `tables/README.md`, `paper/README.md`, and `archive/README.md` for artifact and provenance policy details.

## Docker Reproducibility

The repository includes a lightweight Docker/Compose configuration for the Analysis v1 reproducibility surface. It installs MagGenBench as a normal package, exposes the packaged `maggenbench` and `mvp` console commands, and sets Matplotlib to a noninteractive backend for headless figure generation.

The lightweight image is only for package installation, CLI smoke checks, Analysis v1 figure generation, Analysis v1 reproduction from frozen inputs, and the Phase 6 analysis/reproduction tests. It does not contain model checkpoints or heavy model runtimes.

Local runtime acceptance requires Docker/Compose on the host; if Docker is unavailable, treat the container files as implemented but not locally smoke-tested.

Build the image:

```bash
docker compose build analysis
```

Help smoke checks:

```bash
docker compose run --rm analysis maggenbench --help
docker compose run --rm analysis maggenbench figures analysis-v1 --help
docker compose run --rm analysis maggenbench reproduce analysis-v1 --help
```

Run the lightweight container regression target:

```bash
docker compose run --rm analysis python -m pytest -q \
  tests/test_analysis_v1_figures.py \
  tests/test_maggenbench_cli.py \
  tests/test_reproduction_analysis_v1.py \
  tests/test_unified_analysis.py \
  tests/test_analysis_cohorts.py \
  tests/test_analysis_plotting.py \
  tests/test_dependency_light_imports.py
```

For real Analysis v1 reproduction, mount externally supplied frozen artifacts and write outputs to a host-visible directory:

```bash
MAGGENBENCH_ARTIFACT_ROOT=/path/to/artifacts \
MAGGENBENCH_OUTPUT_ROOT=./reproduced \
docker compose run --rm analysis \
  maggenbench reproduce analysis-v1 \
    --repo-root /workspace \
    --artifact-root /artifacts \
    --baseline-joined /artifacts/baseline_joined.csv \
    --output-dir /output/analysis_v1
```

The historical absolute baseline path in `runs/analysis_v1/final_sha256.txt` is provenance only. The mounted `--baseline-joined` file is the runtime input, and its checksum is still validated against the frozen manifest digest.

`MAGGENBENCH_ARTIFACT_ROOT` is required and must point to the directory containing the frozen Analysis v1 artifacts. For the command above, that directory must contain `baseline_joined.csv` at its root. `MAGGENBENCH_OUTPUT_ROOT` is optional and defaults to `./reproduced`.

Do not force all model ecosystems into a single Python environment.

## Tests

Run lightweight tests from an installed development environment:

```bash
python -m pytest -q
```

Some production workflows require server-side environments and external artifacts. Local tests should not download models, run GPU workloads, or process the full production sample directories.

## Adding A Model

To add a model to the current architecture:

1. Add cohort metadata to the canonical registry only when the cohort is part of a supported analysis surface.
2. Keep model-specific execution in a thin script or run recipe.
3. Put reusable parsing, annotation, enrichment, or analysis logic under `src/mvpipeline`.
4. Document required external artifacts and environment constraints.
5. Add lightweight tests with fixtures or fake backends.

## Adding A Descriptor

Descriptor changes must preserve the frozen Descriptor v1 contract unless a new descriptor version is explicitly introduced. New descriptor code should document schema, units, missing-value behavior, and provenance.

## Scientific Interpretation Caveats

- CHGNet outputs in this repository are machine-learning energy predictions. They are not DFT formation energies, hull distances, or thermodynamic stability labels unless explicitly transformed and documented.
- DXMag outputs are predicted magnetic moments in `muB/f.u.`. They are not magnetic ordering, saturation magnetization, Curie temperature, or structure-dependent DFT magnetic moments.
- Composition screens for magnetic elements indicate chemical plausibility, not a verified magnetic ground state.
- Magnetic Descriptor v2 describes composition, magnetic-site geometry, and symmetry proxies. It does not establish magnetic order.
- Descriptor v1 is frozen for Analysis v1 reproducibility. Changes require a new versioned descriptor contract.

## Provenance

Analysis v1 provenance is captured in the run recipes, checksum manifests, canonical cohort registry, and tests. Reproduction should start from a fresh clone plus documented external artifacts and should not require inspecting implementation files to understand the repository layout or public commands.
