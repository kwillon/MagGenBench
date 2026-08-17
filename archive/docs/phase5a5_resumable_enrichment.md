# Phase 5A-5: resumable checkpointed enrichment

Phase 5A-5 extends the real batch enrichment runners with persistent
resume and checkpoint behavior suitable for larger enrichment runs.

## Resume semantics

The energy and magnetism stage APIs already support
`resume_success_ids`.

The batch runners now expose:

- `--resume`
- `--checkpoint-every N`

When `--resume` is enabled and the output CSV already exists:

- rows with `status == ok` are treated as completed;
- successful structure IDs are skipped;
- failed structure IDs are eligible for recalculation;
- missing structure IDs are calculated;
- the final CSV follows manifest order;
- duplicate or foreign structure IDs are rejected.

Existing successful rows are preserved rather than recalculated.

## Checkpoint semantics

New results are processed in chunks controlled by
`--checkpoint-every`.

After every completed chunk, the current result table is merged with
the existing checkpoint and written using the atomic stage-table
writer.

This limits loss after interruption to, at most, work completed inside
the currently unfinished chunk.

A resumed run can therefore continue from the latest successfully
written checkpoint rather than restarting the complete enrichment
batch.

## Manual validation

The real DXMag backend was used to validate the behavior on the
Phase 5A-4 10-structure manifest.

### Fully completed result

A second run with `--resume` over an existing 10/10 successful CSV
produced:

- resumed successful rows: 10
- new results: 0
- skipped rows: 10
- planned rows: 0
- final rows: 10

The SHA-256 hash of the CSV was unchanged.

### One failed result

A synthetic checkpoint containing 9 successful rows and 1 failed row
was resumed.

The run produced:

- resumed successful rows: 9
- newly calculated rows: 1
- skipped rows: 9
- planned rows: 1
- final successful rows: 10

Only the failed structure was recalculated.

### Checkpointed batch

A fresh 10-structure DXMag run with

`--checkpoint-every 3`

wrote checkpoints after:

- 3 processed rows
- 6 processed rows
- 9 processed rows
- 10 processed rows

The final table contained 10 unique successful structure IDs.

### Simulated interrupted run

A checkpoint containing only the first 6 successful rows was used to
simulate interruption.

The resumed run produced:

- resumed successful rows: 6
- pending rows: 4
- new results: 4
- checkpoints written: 2
- final rows: 10
- final successful rows: 10

The six previously completed structures were not recalculated.

## Automated tests

`tests/test_stage_tables_resume.py` covers:

- partial checkpoint merging;
- replacement of failed records;
- manifest-order preservation;
- rejection of unknown structure IDs;
- rejection of duplicate structure IDs;
- protection of already successful records;
- completeness requirements for final resume merge;
- replacement of previous failed results in the final merge.

## Scope

Phase 5A-5 validates infrastructure behavior only.

It does not change the scientific meaning of CHGNet energy estimates
or DXMag magnetic-moment predictions, and it does not define the
scientific filtering criteria for a full production enrichment run.
