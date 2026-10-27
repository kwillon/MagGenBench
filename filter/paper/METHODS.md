# Methods — CIF-only magnetic-reference filter

## Scope and interpretation

The method is a CIF-only magnetic-reference enrichment and candidate-ranking framework. It does not predict a magnetic ground state. Labels such as AFM-like, FM-like, FiM-like and MAGNDATA-like refer only to proximity to the corresponding reference manifold in the descriptor space.

## Structural and chemical representation

Each successfully parsed CIF is represented by structural, chemical/local-environment, magnetic-center-support, candidate magnetic-pair geometry and pair-motif descriptors. Space-group number and crystal-system labels are retained as metadata but are excluded from the Euclidean metric because categorical symmetry identifiers are not scalar physical coordinates.

Chemical evidence includes oxidation-state assignment diagnostics, post-hoc bond-valence residual statistics, CrystalNN local coordination/neighbor-composition summaries, and formula-level SMACT validity. The bond-valence residuals are implementation-defined post-hoc descriptors and should not be interpreted as independent experimental observables. Missing values are retained during extraction and are imputed only during reference-space fitting.

## Magnetic-center support layer

For each crystallographic site, the code forms a deterministic heuristic support score (legacy column name `center_confidence`) from ionic/open-shell evidence, a metallic elemental prior, rare-earth support where applicable, and closed-shell suppression. The components are combined by a soft-OR operation after suppression. The score is neither calibrated nor interpreted as a probability of a magnetic moment. Sites with support score >=0.25 are used only for the high-support center summaries. Candidate pair construction uses a broader support threshold of 0.05; therefore high-support centers and pair-candidate centers are distinct sets.

No external site priors are used in the canonical paper extraction. The optional `site_priors` interface is an advanced extension and is outside the paper workflow.

## Candidate magnetic-pair geometry

Pairs are constructed between pair-candidate centers using minimum-image geometry. A pair is retained when its center-center distance is <=8 Å or when a shared configured ligand bridge exists, and its geometric-mean center-support weight is >=0.05. Direct-contact and compact metal-metal bins use normalized intersite distances; ligand-mediated bins identify shared ligand sites using covalent-radius cutoffs. M-X-M angular bins near 90° and near 180° encode geometry only and are not used as Goodenough-Kanamori sign predictions. Pair connectivity is reported as the largest-connected-component fraction of the candidate-center pair graph (legacy column name `magnetic_sublattice_connected_fraction`), not as a calculated magnetic sublattice.

## Canonical descriptor policy and canonical reference space

Descriptor extraction writes 55 registered structure-level descriptors. Before model fitting, six coordinates are excluded by canonical policy: `chemistry__fraction_sites_bv_successful`, which is an exact duplicate of `chemistry__bv_success` in the canonical extraction, and five raw extensive coordinates (`structure__n_sites`, `magnetic_center__n_magnetic_centers`, `magnetic_pair__n_supported_centers`, `magnetic_pair__n_weighted_pairs`, `magnetic_pair__total_pair_weight`) whose values depend directly on the crystallographic cell representation.

The remaining 49 coordinates undergo reference-cohort coverage, constant and near-constant filtering. The near-constant tolerance is 1e-8 times max(1, |reference median|). In the canonical cohort, `structure__has_disorder`, `structure__occupancy_not_1_count`, and `structure__symmetry_failed` are constant, while `chemistry__charge_balance_consistency` is near-constant. The final paper representation therefore contains 45 coordinates. The exact ordered list is stored in `paper/manifests/features.csv`.

## Reference-space fitting

Reference structures comprise MAGNDATA and Materials Project AFM, FM, FiM and NM subsets. Missing descriptor values are replaced by the reference median. Each feature is centered at the reference median and scaled by an IQR-derived robust scale, with a standard-deviation fallback when required. Transformed values are clipped to +/-8. Distances are Euclidean in this robust-scaled 45-dimensional space.

For each structure and reference branch, the branch distance is the mean distance to its 15 nearest neighbours from that reference branch. During reference validation, self-neighbours are excluded. The primary magnetic-reference contrast is

`C_mag-NM = d_NM - min(d_MAGNDATA, d_AFM, d_FM, d_FiM)`.

Positive values indicate closer proximity to at least one magnetic reference branch than to the NM branch. The nearest magnetic reference branch is an affinity label and is not interpreted as a magnetic-order prediction.

## Reference validation and ablations

The primary internal validation treats MAGNDATA/AFM/FM/FiM collectively as magnetic references and NM as the non-magnetic reference. The canonical reference model gives approximately 0.954 magnetic sensitivity, 0.915 NM specificity and 0.935 balanced accuracy. Five-branch agreement is secondary. The composition-only ablation uses 7 features; the cleaned magnetic-topology ablation uses 25 features.

## Generator benchmark

Generator-level enrichment is the fraction of scored structures with positive magnetic-reference contrast. Additional reported quantities include median contrast, nearest-magnetic-reference distance, reference-support percentile, formula diversity and nearest magnetic-reference branch composition. Formula-cluster bootstrap with 1000 replicates is used for 95% confidence intervals of generator-level metrics. CrystALLM is target-conditioned and its formula diversity is not directly compared with unconditional generators.

## External DFT validation

Historical DFT results are joined to generator outputs only by generator identity and structure identifier. DFT outcomes are not used for fitting, descriptor selection, scaling, or selection of the final reference representation. Figure 2D reports the DFT-magnetic fraction among pipeline magnetic-like candidates with Wilson 95% intervals. In the canonical external set, approximately 75% of pipeline magnetic-like candidates are DFT magnetic, compared with approximately 18% of pipeline NM-like structures. Explicit AFM-versus-FM calculations are reported separately and demonstrate that magnetic-reference branch affinity is insufficient for reliable AFM/FM ground-state assignment.

## Embeddings

PCA, UMAP and t-SNE are computed only after applying the same canonical reference-feature centering, imputation, scaling and clipping used by the quantitative model. They are used for qualitative visualization of coverage and not as evidence of branch classification.

## MAGNDATA exact-SHA deduplication sensitivity

Exact duplicate CIF files in the reference provenance manifest were identified by SHA256 hash. The canonical manifest contains 1,288 MAGNDATA entries corresponding to 1,236 unique SHA256 hashes: 52 extra rows in 43 duplicate groups. No MAGNDATA SHA256 hash overlaps an AFM, FM, FiM, or NM Materials Project reference entry. As a supplementary sensitivity analysis, MAGNDATA was therefore reweighted to one deterministic representative per exact SHA group, while all other reference branches were left unchanged. Descriptor extraction was not repeated. Feature selection, reference-median imputation, robust scaling, NM thresholds, and kNN reference distances were refit after deduplication.

The exact-SHA sensitivity retains the same 45-feature manifest. Binary reference balanced accuracy changes from 0.9346 to 0.9343, magnetic sensitivity from 0.9543 to 0.9537, while NM specificity remains 0.9150. Across 15,574 scored generator structures, magnetic-like/NM-like assignments agree for 99.91% of structures and contrast has Spearman rho = 0.99997 between the main and deduplicated fits. Generator-level magnetic-like fractions change by at most 0.0025. The external 324-structure DFT subset has identical binary pipeline assignments and therefore identical DFT confirmation fractions. MAGNDATA same-branch agreement decreases from 0.728 to 0.707, consistent with removal of zero-distance duplicate neighbours under leave-one-out validation; this branch-level effect does not affect the primary magnetic-vs-NM claim.
