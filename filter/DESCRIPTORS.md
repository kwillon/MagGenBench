# DESCRIPTORS.md — CIF Magnetic Reference Filter

This document describes the descriptor implementation in `src/cifmagfilter/core.py` of the audited public release. The framework is a **CIF-only reference-manifold filter**; descriptor names containing “magnetic” denote heuristic/reference-support constructs, not calculated magnetic moments, exchange constants, or ground-state labels.

## Canonical paper representation

- Registered extraction descriptors: **55**.
- Canonical main-metric candidates before reference filtering: **49**.
- Canonical paper metric space: **45 features**.
- Near-constant tolerance: `1e-8`.

Six registered descriptors are retained in extraction outputs but excluded from the canonical metric by policy:

- `chemistry__fraction_sites_bv_successful` — exact duplicate of `chemistry__bv_success` in the canonical extraction;
- `structure__n_sites` — raw extensive/cell-size-dependent count;
- `magnetic_center__n_magnetic_centers` — raw extensive/cell-size-dependent count;
- `magnetic_pair__n_supported_centers` — raw extensive/cell-size-dependent count;
- `magnetic_pair__n_weighted_pairs` — raw extensive/cell-size-dependent count;
- `magnetic_pair__total_pair_weight` — raw extensive/cell-size-dependent quantity.

Of the remaining 49 eligible coordinates, four are removed by canonical reference-cohort filtering:

- `structure__has_disorder` — constant;
- `structure__occupancy_not_1_count` — constant;
- `structure__symmetry_failed` — constant;
- `chemistry__charge_balance_consistency` — near-constant.

The exact ordered reference model is listed at the end of this document and in `paper/manifests/features.csv`.

## Global implementation conventions

- Space-group number/symbol and crystal system are output metadata only and are not Euclidean coordinates.
- Missing numeric values are reference-median imputed before scaling. Scaling uses median centering and `(Q75-Q25)/1.349`, with standard-deviation fallback; standardized values are clipped to `[-8,8]`.
- Reference distance is the mean Euclidean distance to the `k=15` nearest members of each reference branch. Reference self-validation uses leave-one-out removal of the query structure from its own branch.
- `element_symbol()` uses a single representative species for a disordered site. Therefore composition/center/pair features are **not occupancy-aware for mixed sites** even though density uses the full pymatgen composition.
- The canonical paper extraction must record exact `pymatgen` and `SMACT` versions. Two SMACT coordinates are otherwise silently environment-dependent.
- Optional `site_priors` can inject external site-level d/f counts, oxidation states, or old support scores. A strict CIF-only paper run should use no non-CIF external priors and should record that fact explicitly.

## Descriptor table

| Feature | Family | Definition | Units/range | Source | Oxidation-state dependence | Missing / zero logic | Canonical paper | Audit note |
|---|---|---|---|---|---|---|---|---|
| `structure__n_sites` | structure/QC | Number of parsed crystallographic sites in the input cell. | count | pymatgen Structure | No | Always defined after parse. | excluded — canonical policy: raw extensive/cell-size dependent | Cell-choice dependent; supercell expansion changes it. |
| `structure__n_elements` | structure/QC | Number of distinct elements in Structure.composition. | count | pymatgen composition | No | Always defined after parse. | selected | Composition-level; robust to cell replication. |
| `structure__volume_per_atom` | structure/QC | Unit-cell volume divided by number of sites: V/N_sites. | Å³/site | pymatgen Structure.volume | No | Always defined after parse. | selected | Name is imprecise for partial/disordered occupancy: implementation is per site, not occupancy-weighted atom count. |
| `structure__density` | structure/QC | Mass density reported by pymatgen for the parsed structure. | g cm⁻³ | pymatgen Structure.density | No | NaN only on exceptional conversion failure. | selected | Occupancy-aware through pymatgen composition; package/version dependent. |
| `structure__min_interatomic_distance` | structure/QC | Minimum periodic site–site distance over all site pairs. | Å | pymatgen periodic distances | No | NaN for structures with <2 sites or if all distance calls fail. | selected | Sensitive to malformed CIFs and unresolved disorder. |
| `structure__has_disorder` | structure/QC | 1 if at least one site is not ordered; else 0. | 0/1 | pymatgen site.is_ordered | No | Always 0/1 after parse. | excluded — constant in canonical reference cohort | QC/representation flag, not a physical coordinate. |
| `structure__occupancy_not_1_count` | structure/QC | Count of sites whose total species occupancy differs from 1. | count | site.species occupancies | No | Always defined unless a site occupancy cannot be read. | excluded — constant in canonical reference cohort | Does not flag a fully occupied mixed-species site if total occupancy equals 1. |
| `structure__symmetry_failed` | structure/QC | 1 if SpacegroupAnalyzer fails at symprec=0.1 Å; else 0. | 0/1 | pymatgen SpacegroupAnalyzer | No | Always 0/1. | excluded — constant in canonical reference cohort | Algorithmic diagnostic; should not be interpreted as crystallographic disorder. |
| `chemistry__bv_success` | chemistry/local environment | 1 when BVAnalyzer returns an oxidation-state-decorated structure. | 0/1 | pymatgen BVAnalyzer | Yes | 0 on BVAnalyzer failure. | selected | Algorithmic computability/chemical-consistency signal rather than an observable. |
| `chemistry__oxi_guess_success` | chemistry/local environment | 1 when composition.oxi_state_guesses() executes without exception. | 0/1 | pymatgen composition oxidation-state guessing | Yes | 1 even if the returned guess list is empty; 0 only on exception. | selected | Current name overstates semantics; “oxi_guess_call_success” would be more exact. |
| `chemistry__oxi_guess_count` | chemistry/local environment | Number of composition-level oxidation-state guesses returned. | count | pymatgen composition oxidation-state guessing | Yes | 0 if no guesses or if call fails. | selected | Encodes formal-valence ambiguity and implementation limits. |
| `chemistry__oxidation_state_coverage` | chemistry/local environment | Fraction of sites assigned an oxidation state after BV decoration or first composition-level guess. | 0–1 | BVAnalyzer + composition oxi guesses | Yes | 0 if no site receives an oxidation state; NaN only for empty structure. | selected | Site-based, not occupancy-weighted. |
| `chemistry__charge_balance_consistency` | chemistry/local environment | If oxidation-state coverage ≥ configured threshold: 1/(1+\|Σ_i q_i\|); otherwise NaN. | 0–1 | inferred oxidation states | Yes | NaN below min_oxidation_coverage (paper default 1.0). | excluded | Not occupancy-weighted; excluded from canonical reference model. |
| `chemistry__bv_residual_mean` | chemistry/local environment | Mean absolute residual \|BVS_i − q_i\| over sites with calculable residuals. | valence units | calculate_bv_sum after BV decoration | Yes | NaN if no residuals are available. | selected | Residual is a custom post-hoc calculation, not exactly BVAnalyzer’s internal objective. |
| `chemistry__bv_residual_median` | chemistry/local environment | Median absolute residual \|BVS_i − q_i\|. | valence units | calculate_bv_sum after BV decoration | Yes | NaN if no residuals. | selected | Uses same custom residual convention as above. |
| `chemistry__bv_residual_max` | chemistry/local environment | Maximum absolute residual \|BVS_i − q_i\|. | valence units | calculate_bv_sum after BV decoration | Yes | NaN if no residuals. | selected | Outlier-sensitive. |
| `chemistry__fraction_sites_bv_consistent` | chemistry/local environment | Fraction of residual-evaluable sites with \|BVS−q\| ≤ 0.5. | 0–1 | bond-valence residuals | Yes | NaN if no residuals. | selected | 0.5 threshold is a fixed implementation choice. |
| `chemistry__fraction_magnetic_sites_bv_consistent` | chemistry/local environment | Fraction of residual-evaluable sites whose element is in the configured moment-capable registry and has residual ≤0.5. | 0–1 | bond-valence residuals + element registry | Yes | NaN if no qualifying residuals. | selected | “magnetic” here means registry membership, not a calculated local moment. |
| `chemistry__fraction_anion_sites_bv_consistent` | chemistry/local environment | Fraction of residual-evaluable configured strong-anion sites with residual ≤0.5. | 0–1 | bond-valence residuals + STRONG_ANIONS | Yes | NaN if no qualifying anion residuals. | selected | Registry-defined anion class. |
| `chemistry__fraction_sites_bv_successful` | chemistry/local environment | Number of sites with a calculated BV residual divided by N_sites. | 0–1 | bond-valence residual calculation | Yes | 0 when no residual succeeds. | excluded — canonical policy: exact duplicate in canonical extraction | Algorithmic coverage diagnostic; partly overlaps bv_success/oxidation coverage. |
| `chemistry__mean_cn_crystalnn` | chemistry/local environment | Arithmetic mean of CrystalNN coordination number across sites. | count | pymatgen CrystalNN | Indirect | NaN if BV decoration fails or CrystalNN returns no values. | selected | Current code unnecessarily gates CrystalNN on BVAnalyzer success. |
| `chemistry__mean_ligand_fraction_in_nn` | chemistry/local environment | Mean, over sites, of the unweighted fraction of CrystalNN neighbors in LIGANDS. | 0–1 | CrystalNN neighbors + ligand registry | Indirect | NaN if no site-level fractions are produced. | selected | Neighbor fractions ignore CrystalNN weights. |
| `chemistry__mean_magnetic_neighbor_fraction_in_nn` | chemistry/local environment | Mean, over sites, of the unweighted fraction of CrystalNN neighbors in the moment-capable element registry. | 0–1 | CrystalNN + element registry | Indirect | NaN if no site-level fractions. | selected | Registry membership, not local-moment evidence. |
| `chemistry__mean_opposite_sign_fraction_weighted` | chemistry/local environment | For each site, CrystalNN-weighted fraction of neighbors with inferred oxidation state of opposite sign; then arithmetic mean over sites. | 0–1 | CrystalNN weights + inferred oxidation states | Yes | NaN if no site has finite central/neighbor oxidation signs and positive total weight. | selected | Name should clarify two-stage averaging. |
| `chemistry__smact_valid` | chemistry/local environment | Binary SMACT validity with include_alloys=True. | 0/1 | SMACT formula screening | Yes/formula-level | NaN if SMACT is unavailable or call fails. | selected | Optional dependency makes the canonical feature vector environment-dependent unless version is pinned/required. |
| `chemistry__smact_valid_mixed_valence` | chemistry/local environment | Binary SMACT validity with include_alloys=True and mixed_valence=True. | 0/1 | SMACT formula screening | Yes/formula-level | NaN if installed SMACT lacks the argument or call fails. | selected | Strongly version-sensitive; must pin canonical package version. |
| `magnetic_center__n_magnetic_centers` | heuristic center support | Count of sites with center_confidence ≥ 0.25. | count | heuristic site support score | Yes for ionic/RE terms | Always integer ≥0. | excluded — canonical policy: raw extensive/cell-size dependent | 0.25 is hard-coded and differs from the pair-graph threshold 0.05. |
| `magnetic_center__fraction_magnetic_centers` | heuristic center support | n_magnetic_centers / N_sites. | 0–1 | heuristic site support score | Yes | 0 when no site passes 0.25. | selected | Heuristic center-support fraction, not local-moment fraction. |
| `magnetic_center__mean_center_confidence` | heuristic center support | Mean over all sites of soft-OR(ionic, metallic, rare-earth support) after closed-shell suppression. | 0–1 | heuristic site-score model | Yes | Non-moment sites generally contribute 0; finite mean for nonempty structures. | selected | Not calibrated confidence/probability; rename to mean_center_support_score. |
| `magnetic_center__max_center_confidence` | heuristic center support | Maximum site center support score. | 0–1 | heuristic site-score model | Yes | 0 if all sites score 0. | selected | Not a probability; rename to max_center_support_score. |
| `magnetic_center__mean_ionic_score` | heuristic center support | Mean ionic support over sites where ionic_score is finite; ionic = open_shell × mean(available BV/site-prior support, ligand fraction). | ~0–1 | formal d/f counts + BV residual + local environment | Yes | NaN site values are skipped by pandas mean, then structure summary defaults to 0 if mean is non-finite. | selected | Denominator differs from metallic/RE score means; external priors can alter it. |
| `magnetic_center__mean_metallic_score` | heuristic center support | Mean over all sites of `ELEMENTAL_PRIOR(element) × mean(metal_env, 1−composition_ligand_fraction)`, where `metal_env = mean(local metal fraction, composition metal fraction, local moment-element-neighbor fraction)`. | 0–1 | hand-set elemental prior + local environment | No direct ox dependence | Non-prior elements contribute 0. | selected | Hand-set priors are a major heuristic; disclose values and provenance. |
| `magnetic_center__mean_rare_earth_score` | heuristic center support | Mean over all sites of RE support based on open f shell, hand-set elemental prior, fixed 0.7 baseline and metal-rich environment. | 0–1 | formal f count + elemental prior + local environment | Yes | Non-RE sites contribute 0. | selected | Contains an explicit fixed 0.7 term and simplified f-shell model. |
| `magnetic_center__mean_closed_shell_suppression` | heuristic center support | Mean heuristic suppression based on d/f shell closure and explicit element/oxidation-state rules. | 0–1 | formal d/f counts + hard-coded rules | Yes | 0 for most sites; selected elements/oxidation states may be partially/fully suppressed. | selected | Mechanistic prior; should be described as heuristic exclusion support, not physics-derived probability. |
| `magnetic_center__composition_ligand_fraction` | heuristic center support | Fraction of sites whose representative element is in LIGANDS. | 0–1 | site elements + ligand registry | No | Always defined. | selected | For disordered sites element_symbol() uses the first listed species, not occupancy weighting. |
| `magnetic_center__composition_moment_element_fraction` | heuristic center support | Fraction of sites whose representative element belongs to configured 3d/4d5d/RE/actinide moment-capable families. | 0–1 | element registry | No | Always defined. | selected | Element-family prior, not DFT moment fraction. |
| `magnetic_center__fraction_centers_3d` | heuristic center support | Among sites passing center_confidence ≥0.25, fraction in configured 3d family. | 0–1 | heuristic center selection + element family | Indirect | Returns 0 if no high-support centers. | selected | Zero conflates “no centers” and “centers but none 3d”. |
| `magnetic_center__fraction_centers_4d5d_weak` | heuristic center support | Among high-support centers, fraction in configured 4d/5d family. | 0–1 | heuristic center selection + element family | Indirect | Returns 0 if no centers. | selected | “weak” is a prior convention, not a universal physical property; rename family. |
| `magnetic_center__fraction_centers_rare_earth` | heuristic center support | Among high-support centers, fraction in configured rare-earth family. | 0–1 | heuristic center selection + element family | Indirect | Returns 0 if no centers. | selected | La/Lu are excluded by registry. |
| `magnetic_center__fraction_centers_actinide` | heuristic center support | Among high-support centers, fraction in configured actinide family. | 0–1 | heuristic center selection + element family | Indirect | Returns 0 if no centers. | selected | Registry limited to U, Np, Pu, Am, Cm. |
| `magnetic_pair__n_supported_centers` | pair geometry/graph | Number of sites with center_confidence ≥ min_center_score (paper default 0.05) used to build pair graph. | count | heuristic site support | Indirect | Always integer ≥0. | excluded — canonical policy: raw extensive/cell-size dependent | Different site set from n_magnetic_centers (0.25 threshold). |
| `magnetic_pair__n_weighted_pairs` | pair geometry/graph | Number of retained supported-center pairs after distance/bridge and minimum pair-weight rules. | count | pair graph construction | Indirect | 0 if no retained pairs. | excluded — canonical policy: raw extensive/cell-size dependent | Cell-choice dependent; graph edges are not exchange interactions. |
| `magnetic_pair__total_pair_weight` | pair geometry/graph | Σ_ij sqrt(c_i c_j) over retained pairs. | arbitrary support units | center support scores | Indirect | 0 for no pairs. | excluded — canonical policy: raw extensive/cell-size dependent | Scales with cell size and number of retained pairs. |
| `magnetic_pair__mean_pair_weight` | pair geometry/graph | Mean sqrt(c_i c_j) over retained pairs. | 0–1 | center support scores | Indirect | Defaults to 0 for empty pair table. | selected | Heuristic support weight, not coupling strength. |
| `magnetic_pair__mean_mm_distance` | pair geometry/graph | Arithmetic mean minimum-image center–center distance over retained pairs. | Å | periodic geometry | No direct ox dependence | NaN if no retained pairs. | selected | Pair inclusion is support- and cutoff-dependent. |
| `magnetic_pair__mean_mm_distance_norm` | pair geometry/graph | Mean d_MM/(r_i^metal+r_j^metal) over retained pairs. | dimensionless | pymatgen Element radii with fallbacks | No direct ox dependence | NaN if no pairs. | selected | radius() silently falls back and finally uses 1.3 Å if no radius is available. |
| `magnetic_pair__weighted_fraction_direct_contact_geometry` | pair geometry/graph | Σ w_ij I[d_MM/(r_i^metal+r_j^metal)≤1.20]/Σw_ij. | 0–1 | pair geometry + support weights | Indirect | 0 for empty/no-weight graph. | selected | Pure geometric bin; no exchange-sign/mechanism claim. |
| `magnetic_pair__weighted_fraction_ligand_mediated` | pair geometry/graph | Pair-weighted fraction with ≥1 shared ligand X; M–X distance must satisfy min(1.30(r_M^cov+r_X^cov), 3.5 Å). | 0–1 | covalent-radius bridge geometry + support weights | Indirect | 0 for no pairs. | selected | Bridge definition is heuristic geometric connectivity, not a bond-order calculation. |
| `magnetic_pair__weighted_fraction_mxm_90_geometry` | pair geometry/graph | Pair-weighted fraction with ≥1 shared-ligand M–X–M angle in [72°,108°]. | 0–1 | bridge geometry + support weights | Indirect | 0 for no pairs. | selected | Geometry bin only; not a GKA/FM prediction. |
| `magnetic_pair__weighted_fraction_mxm_180_geometry` | pair geometry/graph | Pair-weighted fraction with ≥1 shared-ligand M–X–M angle ≥145°. | 0–1 | bridge geometry + support weights | Indirect | 0 for no pairs. | selected | Broad near-linear bin; “180” is shorthand, not exact geometry or AFM prediction. |
| `magnetic_pair__weighted_fraction_compact_metal_metal_geometry` | pair geometry/graph | Pair-weighted fraction classified direct-contact and, when bridged, additionally satisfying normalized metallic-radius distance ≤1.104 (=1.20×0.92). | 0–1 | pair geometry + support weights | Indirect | 0 for no pairs. | selected | Implementation-specific compact-contact bin; avoid “metallic exchange” language. |
| `magnetic_pair__weighted_fraction_re_tm` | pair geometry/graph | Pair-weighted fraction joining an RE supported center to a configured 3d/4d5d supported center. | 0–1 | element families + support weights | Indirect | 0 for no pairs. | selected | Family-composition descriptor conditioned on heuristic center support. |
| `magnetic_pair__magnetic_sublattice_connected_fraction` | pair geometry/graph | Largest connected component size / number of supported centers, using every retained pair as an edge. | 0–1 | supported-center pair graph | Indirect | 0 if no nodes; 1 if one node. | selected | Name overclaims: edges include any supported pair within 8 Å even without a ligand bridge/contact. Rename to candidate_center_pair_graph_lcc_fraction. |
| `pair_motif__bridge_chemistry_diversity` | pair motif | Normalized Shannon entropy H/log(K) over observed non-empty bridge-element-set labels. | 0–1 | bridge labels | No | 0 for empty pair table or ≤1 observed category. | selected | This is normalized evenness over observed categories, not richness-sensitive diversity. |
| `pair_motif__pair_family_diversity` | pair motif | Normalized Shannon entropy H/log(K) over observed supported-center family-pair labels. | 0–1 | center family pair labels | No | 0 for empty pair table or ≤1 category. | selected | Also an evenness measure; rename accordingly if precision is desired. |

## Equations used by the heuristic center layer

For transition-metal candidates, the formal d count is approximated as `group_number - oxidation_state`. For configured rare-earth candidates, the f count is extrapolated from the trivalent f count as `f3 + (3 - oxidation_state)` and clipped to `[0,14]`.
`open_shell_score` is binary support for `0.2 < d < 9.8` and/or `0.2 < f < 13.8`, averaged when both are available.
`metallic_score = ELEMENTAL_PRIOR[element] × mean(local metal fraction, composition metal fraction, local moment-element neighbor fraction)` combined with the non-ligand composition term as implemented in `site_score()`.
`pair_weight = sqrt(center_support_i × center_support_j)`.
Weighted pair fractions use `Σ w_ij I(condition) / Σ w_ij`.
Pair-motif “diversity” is `H/log(K)` using only categories observed in the structure; mathematically this is normalized Shannon evenness.

## Terminology recommended for Methods / public README

- Prefer **center support score** or **candidate moment-center support**, not “confidence” or “probability”.
- Prefer **candidate-center pair graph**, not “magnetic sublattice”, unless the graph is explicitly redefined to represent exchange-connected sites.
- Prefer **near-90° M–X–M geometry bin** and **near-linear M–X–M geometry bin**, not FM/AFM or GKA mechanism labels.
- Describe `AFM-like`, `FM-like`, `FiM-like`, and `MAGNDATA-like` only as reference-manifold affinity.

## Canonical canonical reference model

The exact feature order used by the final paper model is:

1. `structure__n_elements`
2. `structure__volume_per_atom`
3. `structure__density`
4. `structure__min_interatomic_distance`
5. `chemistry__bv_success`
6. `chemistry__oxi_guess_success`
7. `chemistry__oxi_guess_count`
8. `chemistry__oxidation_state_coverage`
9. `chemistry__bv_residual_mean`
10. `chemistry__bv_residual_median`
11. `chemistry__bv_residual_max`
12. `chemistry__fraction_sites_bv_consistent`
13. `chemistry__fraction_magnetic_sites_bv_consistent`
14. `chemistry__fraction_anion_sites_bv_consistent`
15. `chemistry__mean_cn_crystalnn`
16. `chemistry__mean_ligand_fraction_in_nn`
17. `chemistry__mean_magnetic_neighbor_fraction_in_nn`
18. `chemistry__mean_opposite_sign_fraction_weighted`
19. `chemistry__smact_valid`
20. `chemistry__smact_valid_mixed_valence`
21. `magnetic_center__fraction_magnetic_centers`
22. `magnetic_center__mean_center_confidence`
23. `magnetic_center__max_center_confidence`
24. `magnetic_center__mean_ionic_score`
25. `magnetic_center__mean_metallic_score`
26. `magnetic_center__mean_rare_earth_score`
27. `magnetic_center__mean_closed_shell_suppression`
28. `magnetic_center__composition_ligand_fraction`
29. `magnetic_center__composition_moment_element_fraction`
30. `magnetic_center__fraction_centers_3d`
31. `magnetic_center__fraction_centers_4d5d_weak`
32. `magnetic_center__fraction_centers_rare_earth`
33. `magnetic_center__fraction_centers_actinide`
34. `magnetic_pair__mean_pair_weight`
35. `magnetic_pair__mean_mm_distance`
36. `magnetic_pair__mean_mm_distance_norm`
37. `magnetic_pair__weighted_fraction_direct_contact_geometry`
38. `magnetic_pair__weighted_fraction_ligand_mediated`
39. `magnetic_pair__weighted_fraction_mxm_90_geometry`
40. `magnetic_pair__weighted_fraction_mxm_180_geometry`
41. `magnetic_pair__weighted_fraction_compact_metal_metal_geometry`
42. `magnetic_pair__weighted_fraction_re_tm`
43. `magnetic_pair__magnetic_sublattice_connected_fraction`
44. `pair_motif__bridge_chemistry_diversity`
45. `pair_motif__pair_family_diversity`

This order is also stored machine-readably in `paper/manifests/features.csv`.
