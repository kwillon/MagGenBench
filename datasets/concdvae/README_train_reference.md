# train_reference for concdvae

This file is a compact normalized training reference table for novelty comparison.

## Output file
- `train_reference.csv`

## Output columns
- `id`
- `reduced_formula`
- `spacegroup`

## Sources
- `/mnt/tank/scratch/kkapranova/sww-magnetic-validation-pipeline-master/sww-magnetic-validation-pipeline-master/datasets/raw_data/mp4conz_train.csv`
- `/mnt/tank/scratch/kkapranova/sww-magnetic-validation-pipeline-master/sww-magnetic-validation-pipeline-master/datasets/raw_data/mp_20_train.csv`

## Deduplication
- dedup_key: `id`
- rows before dedup: 54272
- rows after dedup: 27136
- removed duplicates: 27136
