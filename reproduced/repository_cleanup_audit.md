# Repository cleanup audit

Pre-change audit, 2026-11-09. Branch main at 79adeb33; origin https://github.com/kwillon/MagGenBench.git; cached origin/main equals local main. Remote freshness will be checked before integration. No tracked modifications at start; untracked Figure 5/SI and Figure 8/SI work is scientific work to preserve in a checkpoint.

## Inventory and SHA256 duplicates

{
  "paper": {
    "files": 83,
    "bytes": 13060747
  },
  "tables": {
    "files": 64,
    "bytes": 184423845
  },
  "reproduced": {
    "files": 72552,
    "bytes": 1402944278
  },
  "docs": {
    "files": 9,
    "bytes": 37564
  },
  "scripts": {
    "files": 60,
    "bytes": 280454
  },
  "src": {
    "files": 132,
    "bytes": 672223
  }
}

72900 files inspected; 34064 exact SHA256 duplicate groups; 22 filesystem access errors. Caches, virtual environments and Git internals excluded; inaccessible generated/test directories are explicitly recorded, not removed. Duplicate candidates were grouped by size then hashed; all accessible paper/tables files were hashed.

Detailed per-file classification, Git status, proposed action and current dependencies: `repository_cleanup/suspected_files_plan.csv`. Full inventory: `repository_cleanup/inventory_before.csv`; duplicates: `repository_cleanup/duplicates_before.json`; references: `repository_cleanup/path_references_before.json`; errors: `repository_cleanup/access_errors.json`.

## Planned bounded changes (before any cleanup)

1. Create chore/paper-structure-cleanup and checkpoint reviewed scientific work, including small ignored Figure 5/8 inputs needed for reproducibility. Exclude environments, caches, raw generated data and unrelated files.
2. Archive original Figure 8 as legacy/fig08_multiobjective_presence_original.pdf; archive hybrid v1/v2; copy identical v2 bytes to canonical fig08_multiobjective.pdf. Move previews to reproduced/figureN/previews.
3. Move nine figure-source CSVs to tables/figure_sources, preserving bytes. Preserve numbered frozen table stages. Move scenario/criteria/ablation CSVs to tables/figure_sources/figure8; OVL/SWD frozen results to tables/figure_sources/figure5_overlap. Update current loaders; do not synthesize scientific results.
4. Consolidate verified captions in paper/figure_captions.md; move reproduction docs to docs/figures. Keep historical conflicting Figure 8 caption archived. Preserve Figure 4 audits under reproduced and technical SI files outside publication tables.
5. Keep semantic SI documents and tables under paper/supporting_information; numbering S7-S9 remains provisional because manuscript unavailable.
6. Update links, reproduction defaults and checksums; test Figure 5/8, SI, links, source hashes. Do not delete unique data or unused historical code without dependency evidence.
7. Review commits, fetch origin/main, integrate locally and push normally only after all checks pass.

## Figure source map before cleanup

Figure 1: supplied source under reproduced/figure1; pipeline plotting implementations retained for provenance. Figure 2: manuscript_figure2_v2.py and complete QC status tables. Figure 3: manuscript_figure3_v2.py, frozen analysis and two FT descriptors. Figure 4: filter/scripts/plot_mp_only_publication.py and restyle_figure4_original_vectors.py; original vectors retained, recalculated previews differ scientifically. Figure 5: manuscript_figure5_v2.py and fig05_energy_magnetism.csv; OVL/SWD uses figure5_overlap.py. Figure 6: ten-cohort palette preview script and fig06 source CSVs; permanent implementation limitation documented. Figure 7: no publication artifact found; do not invent. Figure 8: hybrid Art Nouveau v2, saved scenario CSVs and build_paper_figure08_hybrid.py; original presence analysis remains build_paper_figure08.py. Supplementary PCA: plot_paper_pca.py with the same two FT descriptor sources.

## Completed changes and verification (2026-11-10)

Scientific checkpoint: `0f76fdb4` on `chore/paper-structure-cleanup`, based on
`main` / `origin/main` at `79adeb33`. Origin was fetched successfully from
`https://github.com/kwillon/MagGenBench.git` and showed no initial divergence.
No unrelated working-tree changes were present; all initial untracked files
were the reviewed Figure 5/8 scientific work. Caches/environments were excluded.

### Structure before / after

| Before | After |
|---|---|
| paper/figures: current PDF plus PNGs, hybrid candidates, caption/reproduction MDs and Figure 4 audits | Current publication PDFs, README, SHA256SUMS and legacy/ only |
| paper/tables/figure_sources (9 CSVs), root numbered frozen tables, ignored Figure 5/8 results | Single tables/figure_sources with original 9 CSVs, figure8/ and figure5_overlap/; numbered stages unchanged |
| Separate figure2–5 captions and obsolete original Figure 8 caption | paper/figure_captions.md for verified captions 2–5/8; original presence caption archived in docs/figures/legacy/ |
| Reproduction MDs inside paper/figures | docs/figures plus figure/source map |
| SI prose mixed with Python, audit JSON and diagnostic CSV | Publication SI/proposed inserts retained in paper/supporting_information; reusable audit scripts in scripts/analysis; technical provenance in reproduced/ |
| Unsorted intermediate Figure 8 preview directories | reproduced/figure8/previews and reproduced/figure8/legacy |

69 planned file moves preserved SHA256. Nine subsequent history/preview paths
were relabelled/archived with per-file hash checks. Full ledgers:
`approved_moves.json`, `archive_moves.json`, and the current tracked
`tables/figure_sources/path_relocations.json`. Four individual caption files
were removed only after their verified scientific text was consolidated;
original versions remain in checkpoint history. No CSV, NPZ or unique scientific
result was deleted. Original Figure 8, hybrid v1 and hybrid v2 PDFs remain in
paper/figures/legacy/. Canonical Figure 8 and its v2 archive intentionally share
identical content for provenance.

### Duplicate findings

The full pre-change scan found 34064 exact SHA256 duplicate groups, predominantly
repeated generated/test outputs. 27 involved paper artifacts (for example,
selected Figures 2–5 versus their reproduced PDFs and Figure 4 diagnostic copies).
No byte-identical pair was found between the original paper/tables/figure_sources
and root tables: those figure sources were genuinely distinct inputs/results,
so they were relocated rather than discarded. Publication-related groups are
retained in `publication_duplicate_groups.json`. Unique/uncertain generated
outputs were archived or retained, not mass-deleted. Full local inventory and
all duplicate groups remain available in ignored `inventory_before.csv` and
`duplicates_before.json`; these large intermediate audit lists are not committed.

### Reference and reproduction changes

Updated Figure 5, Figure 6 palette preview, publication PCA and both Figure 8
entry points to tables/figure_sources. Scenario and control CSV reads now use
the tracked figure8 subdirectory. Original Figure 8 analysis remains available
but writes only exploratory outputs under reproduced, not competing publication
PDFs. The final generator targets canonical fig08_multiobjective.pdf, writes
PNG outside paper/figures, and refuses existing-output overwrites.

Added a path resolver for historical source metadata; original JSON source paths
and SHA256 values remain unchanged. Historical document hashes can be checked
against checkpoint 0f76fdb4, rather than misleadingly treated as hashes of edited
documentation. Updated moved-document relative links and root README links;
fixed a pre-existing src/README license link. Full reference search and per-file
dependencies are in the audit inventories. Figure 5 CLI now accepts an explicit
--output-dir to isolate reproduction outputs. An initial reproduction exposed
that the old CLI ignored extra arguments and wrote only its exploratory previews;
no publication PDF or numerical source changed. The corrected CLI was then
verified in the intended separate directory.

### Checks performed

- 20 tests passed: tests/test_figure5_overlap.py, test_manuscript_figure5_v2.py,
  test_publication_artifacts.py and test_figure4_vector_design.py.
- Figure 5 rebuilt from its relocated CSV: 12281 rows, 12277 finite pairs;
  Figure 5 publication PDF remained unchanged. Historical scatter artists,
  medians and population contract are covered by tests.
- OVL/SWD SI revalidated, including all 500 saved OVL bootstrap/balanced samples,
  SWD point estimates, stored intervals and saved resampling consistency. Selected
  Table S7 CSV reproduces exactly.
- Figure 8 rebuilt to a separate verification directory from tracked S1 sources;
  the previously selected canonical PDF was not re-rendered/replaced during
  promotion. Its SHA256 equals the original hybrid_v2 artifact exactly.
- Scenario audit: all 9 variants, 90 scores/ranks, 900 pairwise dominance entries
  and 900 rank-frequency entries agree. Full publication CSV and all 50 control
  comparisons reproduce from the relocated sources.
- 114 scientific/publication files verified byte-for-byte against the pre-change
  inventory (using the relocation map); all unchanged main Figures 1–6 retain
  their initial SHA256. All current/archived PDF checksums are updated and PDFs
  pass header/EOF checks.
- 76 tracked/current Markdown documents checked (including this audit): no broken internal file links.
  paper/figures has no PNGs or extra Markdown, and only legacy/ as a subdirectory.
- git diff --check passes. No model training, generation or inference performed.

Canonical Figure 8 SHA256:
`3b7ec054069d739faba5153af3abcda4b22c7c8c5728d9998e3d132095e55b02`.

### Preserved limitations / unresolved questions

- The full manuscript is unavailable locally; provisional SI order is OVL/SWD,
  scenario rankings, alternative criteria/QC ablation. S7–S9 numbering was not
  declared final or automatically changed.
- No current Figure 7 or verified caption text for Figures 1/6 and supplementary
  PCA was found. No scientific caption was invented.
- Figure 4 original statistical vectors and MP-only recalculations differ;
  the documented vector-preserving publication artifact is retained.
- Figure 6 ten-set reproduction still uses the existing palette-preview entry
  point; historical eight-set modules are not deleted merely as old code.
- Twenty-two inaccessible generated/test directories were recorded in
  access_errors.json and left intact. Planned source/publication paths were all
  accessible; no inaccessible path was moved or deleted.
- No bulk deletion of generated CIFs, raw data or historical implementations.

### Integration policy

After these checks, create the reviewed cleanup commit and a separate audit/docs
commit, fetch origin/main again, integrate into local main without rewriting
history, and push normally only if main is compatible and the tree is clean.
The final chat report records the actual commit IDs and verified remote state.
The scientific checkpoint and move ledgers preserve the before state.

Reviewed cleanup commit: `3b89aa9f` (101 files; all scientific data moves detected
as 100% renames). The final audit/evidence is committed separately. CSV/JSON CRLF
endings are preserved with explicit Git attributes; `git diff --cached --check`
also passes without normalizing scientific bytes.
