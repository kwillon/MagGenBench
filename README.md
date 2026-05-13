# MagGenBench

MagGenBench is a research pipeline for benchmarking generative models for inorganic crystal structures with a focus on magnetic-material discovery.

The project collects generated CIF structures from several generative models, validates them, builds unified benchmark tables, performs structural and chemical filtering, extracts descriptors, screens for magnetic candidates, prepares structures for relaxation, and produces paper-ready summary tables and figures.

## Supported generative models

- MatterGen
- Con-CDVAE
- CrystalFormer
- CrystalLLM / CrystaLLM

## Pipeline overview

```text
Generated CIFs
    ↓
CIF parsing and registration
    ↓
Validation and filtering
    ↓
Unified master table
    ↓
Composition and structural descriptors
    ↓
Magnetic screening
    ↓
Relaxation input preparation
    ↓
# Structure relaxation
    ↓
# Energy and stability calculation
    ↓
# Magnetic descriptors
    ↓
Benchmark tables and figures
```

## Repository structure

config/       Pipeline configuration files.
registry/     Metadata about models, runs, datasets, and generated artifacts.
samples/      Generated CIF files from each model.
datasets/     Training/reference datasets used for novelty and matching.
derived/      Generated intermediate structure files.
tables/       Generated and paper-ready CSV tables.
figures/      Generated plots and paper figures.
reports/      JSON, Markdown, and PDF reports.
scripts/      Legacy scripts and lightweight command wrappers.
src/          Python source code for the pipeline.


## Main outputs

- tables/01_master/master_structures.csv
- tables/02_validation/validation_status.csv
- tables/04_magnetic_screening/magnetic_screening.csv
- tables/05_relaxation/relaxation_results.csv
- tables/06_energy/e_above_hull_results.csv
- tables/08_benchmarking/benchmarking_baseline_table.csv
- tables/09_paper/table_1_benchmarking.csv

## Installation

```
conda env create -f environment.yml
conda activate mvpipeline
pip install -e .
```

## Basic usage

Validate generated CIF structures:
```
mvp validate \
  --input-dir samples/mattergen_cifs_2000 \
  --out-dir outputs/mattergen \
  --train-reference datasets/mattergen/train_reference.csv \
  --thresholds config/thresholds.yaml
```

## Basic usage

```
mvp build-master \
  --config config/paths.yaml
```

## Run magnetic screening

```
mvp magnetic-screen \
  --input tables/03_features/composition_features.csv \
  --output tables/04_magnetic_screening/magnetic_screening.csv \
  --config config/magnetism.yaml
```

## Run magnetic screening

```
mvp prepare-relaxation \
  --input tables/04_magnetic_screening/magnetic_screening.csv \
  --output tables/05_relaxation/relaxation_input.csv \
  --config config/relaxation.yaml
```

## Build tables

```
  mvp build-paper-tables \
  --config config/benchmark.yaml
```