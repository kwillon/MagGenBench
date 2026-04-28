# Tables directory

This directory contains intermediate and final tabular outputs used in the MagGenBench workflow.

The main purpose of this folder is to collect CSV tables generated during:
1. CIF aggregation from different generative models,
2. construction of unified benchmark datasets,
3. downsampling and cleaning,
4. validation and filtering,
5. benchmarking against reference datasets,
6. preparation of paper-ready tables and figures.

Most CSV files in this directory are generated automatically and should not be treated as manually curated source data.

---

## General logic

The workflow is organized around several stages:

```text
Generated CIFs
    ↓
Per-model CSV tables
    ↓
Unified master dataset
    ↓
Downsampled benchmark subset
    ↓
Validated / cleaned structures
    ↓
Benchmarking and reference matching
    ↓
Paper-ready summary tables and PDF outputs

---

## More

1. master_runs.downsampled.csv - Generation settings
2. mattergen_structures.csv -  Primary table with structures 
3. mattergen_structures.downsampled.csv — reduced subset selected for benchmarking (2000 per model);

* with_status — validation/filtering status added
classes — chemical/material class labels added;
* clean / clean_v2 — cleaned version after fixing labels, statuses, or problematic rows;
* fixed_paths — paths to CIF files were corrected or normalized