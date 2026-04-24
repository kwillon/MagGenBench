# train_reference for crystalllm

This file is a compact normalized training reference table for novelty comparison.

## Output file
- `train_reference.csv`

## Output columns
- `id`
- `reduced_formula`
- `spacegroup`

## Sources
- `/mnt/tank/scratch/kkapranova/sww-magnetic-validation-pipeline-master/sww-magnetic-validation-pipeline-master/datasets/raw_data/mp_20_train.csv`
- `/mnt/tank/scratch/kkapranova/sww-magnetic-validation-pipeline-master/sww-magnetic-validation-pipeline-master/datasets/raw_data/carbon_24_train.csv`
- `/mnt/tank/scratch/kkapranova/sww-magnetic-validation-pipeline-master/sww-magnetic-validation-pipeline-master/datasets/raw_data/mpts_52_train.csv`
- `/mnt/tank/scratch/kkapranova/sww-magnetic-validation-pipeline-master/sww-magnetic-validation-pipeline-master/datasets/raw_data/perov_5_train.csv`

## Deduplication
- dedup_key: `id`
- rows before dedup: 71963
- rows after dedup: 63113
- removed duplicates: 8850
