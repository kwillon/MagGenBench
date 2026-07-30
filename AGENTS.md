# MagGenBench agent instructions

## Primary repository

The only writable repository is MagGenBench.

The following repositories are read-only donor sources:

- ../_donors/energies_updated
- ../_donors/magm_updated

Do not edit, commit, reformat, rename, or delete files in donor repositories.

## Integration goal

Refactor useful energy and magnetism functionality into the existing
MagGenBench architecture.

The final MagGenBench repository must not depend on donor repository paths,
nested Git repositories, copied virtual environments, generated CSV files,
logs, CIF datasets, or donor CLI scripts.

## Safety

Do not:

- install dependencies without confirmation;
- run model downloads;
- run CUDA, GPU, DFT, relaxation, or large CIF jobs;
- process the full samples directory;
- modify Conda environments;
- use git reset --hard or git clean;
- commit or push without confirmation;
- add secrets, API keys, tokens, absolute user paths, or server-specific paths;
- add .venv, .idea, result CSV files, logs, or model caches.

## Development rules

- Keep reusable logic under src/mvpipeline.
- Keep scripts as thin wrappers only.
- Keep paths and model settings in YAML configuration.
- Reuse the existing CIF discovery and parsing code.
- Use one shared structure identifier across all stages.
- Add unit tests with mocks or fake backends.
- Heavy model execution belongs on aichem.
- Local Windows checks must not download models.
- Preserve backward compatibility where practical.
- Report every modified file and show git diff --stat after each phase.

## Scientific terminology

- Do not label max(formation_energy_per_atom, 0) as e_above_hull.
- Clearly distinguish predicted magnetic moment from magnetic ordering,
  saturation magnetization, Curie temperature, and DFT magnetic moment.
- Record units and normalization: total per structure, per atom, or per volume.

## Donor data exclusion

Donor repositories are source-code references only.

Do not copy, move, enumerate, process, or add to MagGenBench:

- donor CIF files;
- processed structure directories;
- CSV prediction results;
- logs and debug outputs;
- virtual environments;
- caches;
- model download caches;
- generated figures;
- temporary files.

Inspect donor Python code, configuration, documentation, dependency files,
model metadata, and output schemas only.

Do not run donor scripts on their CIF collections.
Do not process more than one explicitly approved fixture CIF.