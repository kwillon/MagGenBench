# MagGenBench

MagGenBench is a scientific benchmark for evaluating inorganic crystal
structures produced by generative models, with particular attention to signals
relevant to magnetic-material discovery. It provides a common workflow for
structure harmonization, quality control, property enrichment, descriptor
analysis, and comparison across model families.

The repository separates reusable code, accepted scientific tables, run
provenance, regenerated outputs, and manuscript-selected artifacts so that the
reported analyses can be inspected and reproduced without conflating source
code with generated results.

## Overview

Generative crystal models produce structures in different formats and under
different sampling or adaptation regimes. MagGenBench places these outputs in a
shared CIF-based representation, applies consistent structural checks, and
compares the retained structures using energy, magnetic-moment, composition,
local-environment, symmetry, and chemical-diversity descriptors.

The accepted downstream dataset contains eight generated sets and is represented
by the integrated table at
[`tables/10_analysis_v2_magnetic/analysis_v2_magnetic.csv`](tables/10_analysis_v2_magnetic/analysis_v2_magnetic.csv).
Scientific interpretation conventions are documented in
[`docs/SCIENTIFIC_CONVENTIONS.md`](docs/SCIENTIFIC_CONVENTIONS.md).

## Evaluated Generative Models

| Model | Sets in the accepted downstream analysis | Status and interpretation |
| --- | --- | --- |
| MatterGen | Base, Fine-tuned | Both sets are analyzed; Fine-tuned is the magnetically adapted variant. |
| Con-CDVAE | Base, Fine-tuned | Both sets are analyzed; Fine-tuned is the magnetically adapted variant. |
| CrystalFormer | Base | Fine-tuned generation is ongoing and is not included in the accepted downstream dataset. |
| CrystaLLM | Base | Fine-tuned generation is ongoing and is not included in the accepted downstream dataset. |
| Crys-JEPA | Base, Refined | Both sets are analyzed. Refined is a generatively refined comparator, not a geometry relaxation of paired Base structures. |

## Workflow

The study workflow is summarized in
[manuscript Figure 1](paper/figures/fig01_pipeline.pdf):

1. Collect generated structures and model-native outputs.
2. Harmonize structures into a common CIF-based representation.
3. Apply structural quality control and retain accepted structures.
4. Enrich retained structures with CHGNet-predicted energy per atom and a
   DXMag-derived, composition-based predicted magnetic moment.
5. Calculate magnetic-composition, local magnetic-geometry, and symmetry
   descriptors.
6. Compare generated structures with magnetic reference spaces using descriptor
   construction, nearest-neighbor distances, and a magnetic-versus-nonmagnetic
   distance contrast.
7. Integrate structural, magnetic, descriptor-space, energy-magnetism, and
   chemical-diversity analyses at the generated-set level.

The reference-space branches in Figure 1 represent similarity or affinity to
AFM, FM, FiM, and NM reference subsets; they are not predictions of magnetic
ground state. Figure 1 also shows selected-candidate DFT validation as a study
continuation. Reference-space and DFT calculations are not currently exposed as
packaged run recipes or accepted result tables in this repository.

### Interpretation Notes

- CHGNet values used here are predicted energies per atom. They are not
  automatically formation energies, energies above hull, or thermodynamic
  stability labels.
- The DXMag-derived model is composition-based. It does not predict AFM, FM, or
  FiM order and cannot distinguish polymorphs with the same composition.
- PCA and generated-set shifts are descriptive population summaries, not paired
  structure trajectories or causal effects.

## Main Analyses

- Structural validation, retention, and rejection profiles
- Magnetic-element composition and local magnetic environments
- Magnetic-site and crystallographic symmetry descriptors
- Magnetic reference-space screening in the broader study design
- Descriptor-space PCA
- Predicted energy-magnetism landscapes
- Chemical composition, compound classes, and diversity
- Candidate-level DFT validation as a study-design continuation; no packaged
  result table is currently included

## Repository Layout

| Path | Contents |
| --- | --- |
| [`src/`](src/) | Reusable Python package code under `src/mvpipeline`. |
| [`scripts/`](scripts/) | Thin command-line wrappers for validation, enrichment, analysis, and figures. |
| [`runs/`](runs/) | Run recipes, configuration records, checksums, and execution provenance. |
| [`config/`](config/) | Structural validation, energy, magnetism, and descriptor configuration. |
| [`datasets/`](datasets/) | Versioned training-reference and supporting datasets. |
| [`samples/`](samples/) | Versioned generated CIF sets used by the benchmark. |
| [`tables/`](tables/) | Canonical scientific tables and documented stage outputs. |
| [`paper/`](paper/) | Manuscript-selected figures and publication metadata. |
| [`docs/`](docs/) | Scientific contracts, conventions, provenance, and stage documentation. |
| [`tests/`](tests/) | Unit, regression, artifact-contract, and figure-generation tests. |
| [`archive/`](archive/) | Historical provenance retained outside the active workflow. |

`outputs/` and `reproduced/` are generated, untracked working areas. Validation
outputs normally go under `outputs/`; regenerated tables, audits, projections,
and figure previews go under `reproduced/`. Large model artifacts may be supplied
separately under `models/` or through explicit runtime paths.

## Installation

Python 3.10 or newer is required. The repository environment includes the
scientific dependencies used by validation and analysis:

```bash
conda env create -f environment.yml
conda activate mvpipeline
python -m pip install -e .
```

The editable install provides the `mvp` validation command and the
`maggenbench` reproducibility command. CHGNet, DXMag, and the generative models
may require separate backend-specific environments and external model artifacts;
they are intentionally not forced into one monolithic runtime.

A lightweight container for package checks and frozen-input reproduction can be
built with:

```bash
docker compose build analysis
```

The container does not include generative-model runtimes, CHGNet or DXMag model
artifacts, or production datasets.

## Running the Workflow

There is no single command that reruns generation, structural validation,
CHGNet, DXMag, descriptor calculation, integrated analysis, and every manuscript
figure. These stages use different dependency environments and are documented by
the recipes under [`runs/`](runs/).

### Structural Validation

The installed validation command accepts a directory of CIF files:

```bash
mvp \
  --input-dir samples/mattergen_cifs \
  --out-dir outputs/mattergen \
  --train-reference datasets/mattergen/train_reference.csv \
  --thresholds config/thresholds.yaml \
  --model-name MatterGen \
  --no-pretty
```

Use the model-specific recipes in [`runs/validation/`](runs/validation/) for the
accepted production configurations.

### Enrichment and Integrated Analysis

The standardized CHGNet/DXMag workflow requires separate energy and magnetism
environments. Its inputs, environment variables, and acceptance checks are
documented in
[`runs/enrichment/standardized/README.md`](runs/enrichment/standardized/README.md).

Given the accepted standardized enrichment table, the magnetic descriptors and
integrated table can be regenerated with:

```bash
bash runs/descriptors/magnetic/run.sh
bash runs/analysis_v2_magnetic/run.sh
```

These scripts write generated results under `reproduced/`; they do not overwrite
the accepted tables under `tables/`.

### Manuscript Figure Previews

Figure 1 and Figures 2-6 can be regenerated from the accepted repository inputs:

```bash
python scripts/illustrations/plot_paper_pipeline_v3.py
python scripts/illustrations/plot_manuscript_figure2_v2.py
python scripts/illustrations/plot_manuscript_figure3_v2.py
python scripts/illustrations/plot_manuscript_figure4_v2.py
python scripts/illustrations/plot_manuscript_figure5_v2.py
python scripts/illustrations/plot_manuscript_figure6_v2.py
```

The internal filenames retain version suffixes because they are executable paths;
the visible manuscript figures use scientific titles without development labels.

### Packaged Reproduction Command

The `maggenbench` CLI currently exposes a frozen-input compatibility surface:

```bash
maggenbench reproduce analysis-v1 --help
maggenbench figures analysis-v1 --help
```

These commands remain available for exact reproduction of the corresponding
frozen artifact contract. They are not a one-command entry point for the current
eight-set manuscript workflow.

## Manuscript Figures

Reproducible PNG, PDF, and SVG previews are generated under
`reproduced/analysis_v2_magnetic/figures/`. Manuscript-selected PDFs are tracked
under [`paper/figures/`](paper/figures/), whose
[`README.md`](paper/figures/README.md) maps each manuscript figure to its
reproduced source.

Selected publication artifacts are verified by
[`paper/figures/SHA256SUMS.txt`](paper/figures/SHA256SUMS.txt). Figures should be
changed in the plotting code and regenerated rather than edited manually.

## Reproducibility and Provenance

- Model, run, and configuration metadata are versioned under `runs/` and
  `config/`.
- Stable `sample_uid` and `structure_id` values are propagated across manifests,
  enrichment outputs, descriptor tables, and integrated analyses.
- Accepted joins require unique identifiers and agreement of shared identity
  fields.
- Generated artifacts are kept separate from reusable source code and accepted
  tables.
- Frozen and manuscript-selected artifacts are verified using SHA-256 checksum
  manifests stored with the corresponding run or publication metadata.

Relevant documentation includes [`tables/README.md`](tables/README.md),
[`runs/README.md`](runs/README.md), and
[`docs/provenance.md`](docs/provenance.md). The checksum manifests and technical
provenance files remain authoritative; raw digest values are intentionally not
duplicated here.

## Data Availability

Versioned samples, supporting datasets, canonical tables, and manuscript
artifacts are included where their size and licensing permit. Large generated
collections, model checkpoints, backend caches, and machine-specific production
artifacts must be supplied separately using the paths documented by the relevant
run recipe.

Repository data and artifact roles are described in
[`tables/README.md`](tables/README.md), [`runs/README.md`](runs/README.md), and
[`paper/README.md`](paper/README.md). No external archival DOI is declared by the
current repository metadata.

## License

MagGenBench is distributed under the [MIT License](LICENSE).

