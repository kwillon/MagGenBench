# train_reference for mattergen

This file is a compact normalized training reference table for novelty comparison.

## Output file
- `train_reference.csv`

## Output columns
- `id`
- `reduced_formula`
- `spacegroup`

## Sources
- `/mnt/tank/scratch/kkapranova/sww-magnetic-validation-pipeline-master/sww-magnetic-validation-pipeline-master/datasets/raw_data/mp_20_train.csv`
- `/mnt/tank/scratch/kkapranova/sww-magnetic-validation-pipeline-master/sww-magnetic-validation-pipeline-master/datasets/raw_data/alex_mp_20_train.csv`

## Deduplication
- dedup_key: `id`
- rows before dedup: 634819
- rows after dedup: 614420
- removed duplicates: 20399
