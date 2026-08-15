# Descriptor Specification v1

Status: draft

This document defines the reproducible descriptor schema used for cross-model analysis in MagGenBench.

## 1. Record identity and provenance

Identity fields are not scientific descriptors. They provide stable joins between descriptor, validation, energy, and magnetism tables.

| Column | Type | Requirement | Definition |
|---|---|---|---|
| `sample_uid` | string | required | Stable benchmark identifier of the structure; unique within a cohort. |
| `model_name` | string | required | Human-readable model or cohort name. |
| `model_short` | string | required | Stable machine-readable cohort key. |
| `run_uid` | string | required | Identifier of the generation or benchmark run from which the structure originates. |
| `source_sample_id` | string | required | Original sample identifier before downstream enrichment. |
| `cif_path` | string | required | Path used to load the CIF for descriptor extraction. |


## 2. Structural descriptors

### 2.1 Unit-cell geometry

These descriptors are calculated directly from the parsed `pymatgen.core.Structure`. They do not depend on neighbor-finding or symmetry tolerances.

| Column | Type | Unit | Definition |
|---|---|---|---|
| `n_atoms` | integer | sites/cell | Number of crystallographic sites in the parsed structure (`len(structure)`); the historical field name is retained for compatibility. |
| `lattice_a` | float | angstrom | Lattice parameter `a`. |
| `lattice_b` | float | angstrom | Lattice parameter `b`. |
| `lattice_c` | float | angstrom | Lattice parameter `c`. |
| `lattice_alpha` | float | degree | Lattice angle alpha. |
| `lattice_beta` | float | degree | Lattice angle beta. |
| `lattice_gamma` | float | degree | Lattice angle gamma. |
| `cell_volume` | float | angstrom^3 | Unit-cell volume (`structure.volume`). |
| `volume_per_atom` | float | angstrom^3/site | `cell_volume / n_atoms`, where `n_atoms` is the number of crystallographic sites; the historical field name is retained for compatibility. |
| `density` | float | g/cm^3 | Crystal density reported by `pymatgen.Structure.density`. |
| `min_lattice_length` | float | angstrom | `min(lattice_a, lattice_b, lattice_c)`. |
| `max_lattice_length` | float | angstrom | `max(lattice_a, lattice_b, lattice_c)`. |
| `lattice_length_ratio` | float | dimensionless | `max_lattice_length / min_lattice_length`. |


### 2.2 Symmetry descriptors

Symmetry descriptors are computed with `pymatgen.symmetry.analyzer.SpacegroupAnalyzer` using `symprec = 0.01` angstrom and `angle_tolerance = 5` degrees. These values match the effective settings of the current validation and enrichment pipeline. The reference implementation was verified with `pymatgen 2025.6.14`.

| Column | Type | Unit | Definition |
|---|---|---|---|
| `spacegroup_number` | nullable integer | none | International space-group number (1-230). |
| `spacegroup_symbol` | nullable string | none | Hermann-Mauguin space-group symbol. |
| `crystal_system` | nullable string | none | Crystal system reported by `SpacegroupAnalyzer`. |
| `point_group_symbol` | nullable string | none | Point-group symbol reported by `SpacegroupAnalyzer`. |
| `symmetry_status` | string | none | `ok` when symmetry analysis succeeds; `error` when it fails. |

If symmetry analysis fails, the structure remains eligible for descriptor extraction. Symmetry-derived fields are stored as missing values and `symmetry_status` is set to `error`; no fallback space group is assigned.


## 3. Composition descriptors

All composition fractions are atomic fractions calculated from the full structure composition and therefore sum over atomic occupancies rather than over unique chemical species.

### 3.1 Composition and periodic categories

| Column | Type | Unit | Definition |
|---|---|---|---|
| `n_elements` | integer | elements | Number of distinct chemical elements in the structure composition. |
| `min_element_fraction` | float | fraction | Minimum atomic fraction among the elements present. |
| `max_element_fraction` | float | fraction | Maximum atomic fraction among the elements present. |
| `composition_entropy` | float | dimensionless | Shannon entropy `-sum(x_i * ln(x_i))` over elemental atomic fractions `x_i`, using the natural logarithm. |
| `transition_metal_fraction` | float | fraction | Sum of atomic fractions for elements with `pymatgen.Element.is_transition_metal == True`. |
| `d_block_fraction` | float | fraction | Sum of atomic fractions for elements with `pymatgen.Element.block == "d"`. |
| `f_block_fraction` | float | fraction | Sum of atomic fractions for elements with `pymatgen.Element.block == "f"`. |
| `lanthanide_fraction` | float | fraction | Sum of atomic fractions for elements with `pymatgen.Element.is_lanthanoid == True`. |
| `actinide_fraction` | float | fraction | Sum of atomic fractions for elements with `pymatgen.Element.is_actinoid == True`. |
| `magnetic_screening_element_fraction` | float | fraction | Sum of atomic fractions belonging to the magnetic-element heuristic defined by `config/magnetism.yaml` (`transition_3d`, `selected_4d_5d`, and `lanthanides`). |

Periodic-category descriptors intentionally preserve the definitions used by `pymatgen 2025.6.14`. Categories are not forced to be mutually exclusive. For example, an element may contribute to both `transition_metal_fraction` and `lanthanide_fraction` if the corresponding `pymatgen` properties are both true.

`magnetic_screening_element_fraction` is a MagGenBench screening heuristic and must not be interpreted as evidence that a specific element carries a magnetic moment in the evaluated crystal. The historical `magnetic_elements` list in `config/thresholds.yaml` is not used for this descriptor.


### 3.2 Element-property statistics

Element-property statistics are calculated from elemental atomic fractions `x_i`. For a property `p_i`, the mean is composition-weighted: `sum(x_i * p_i)`. The standard deviation is the corresponding composition-weighted population standard deviation. Minimum, maximum, and range are calculated over the distinct elements present in the composition.

The following elemental properties are included:

| Prefix | Pymatgen source | Unit |
|---|---|---|
| `atomic_number` | `Element.Z` | dimensionless |
| `atomic_mass` | `Element.atomic_mass` | atomic mass unit |
| `atomic_radius` | `Element.atomic_radius` | angstrom |
| `electronegativity` | `Element.X` | Pauling scale |
| `periodic_row` | `Element.row` | dimensionless |
| `periodic_group` | `Element.group` | dimensionless |

For every prefix, Descriptor v1 produces `<prefix>_mean`, `<prefix>_min`, `<prefix>_max`, `<prefix>_range`, `<prefix>_std`, and `<prefix>_coverage`.

`<prefix>_coverage` is the sum of atomic fractions for which the elemental property is finite and available. If coverage is less than `1.0`, all five statistical descriptors for that property are stored as missing values rather than being calculated from a renormalized partial composition. This prevents silent changes in descriptor meaning for elements with unavailable properties, such as the missing Pauling electronegativity and atomic radius observed for He in `pymatgen 2025.6.14`.


## 4. Local-geometry descriptors

Local geometry is evaluated with periodic boundary conditions. Descriptor v1 uses a maximum neighbor-search radius of `10` angstrom.

### 4.1 Nearest-neighbor distances

For each crystallographic site, the minimum non-zero periodic neighbor distance `d_min` is determined within the `10` angstrom search radius. Statistics are then calculated over the site-wise `d_min` values.

| Column | Type | Unit | Definition |
|---|---|---|---|
| `nearest_neighbor_min` | nullable float | angstrom | Minimum site-wise nearest-neighbor distance in the structure. |
| `nearest_neighbor_mean` | nullable float | angstrom | Mean of site-wise nearest-neighbor distances. |
| `nearest_neighbor_std` | nullable float | angstrom | Population standard deviation of site-wise nearest-neighbor distances. |

### 4.2 Coordination numbers

Coordination numbers are calculated with `pymatgen.analysis.local_env.MinimumDistanceNN(tol=0.1, cutoff=10, get_all_sites=False)`. For each site, neighbors include the nearest neighbor(s) at distance `d_min` and all neighbors within `(1 + tol) * d_min`. Coordination numbers are unweighted (`use_weights=False`). The reference implementation uses `pymatgen 2025.6.14`.

| Column | Type | Unit | Definition |
|---|---|---|---|
| `coordination_mean` | nullable float | neighbors/site | Mean unweighted site coordination number. |
| `coordination_min` | nullable float | neighbors/site | Minimum site coordination number. |
| `coordination_max` | nullable float | neighbors/site | Maximum site coordination number. |
| `coordination_std` | nullable float | neighbors/site | Population standard deviation of site coordination numbers. |
| `local_geometry_status` | string | none | `ok` when local-geometry extraction succeeds; `error` otherwise. |

If local-geometry extraction fails or no periodic neighbor is found within the configured search radius, the affected local-geometry descriptors are stored as missing values and `local_geometry_status` is set to `error`. Such a failure does not change the structural-validation status of the structure.


## 5. Output and missing-value policy

Descriptor extraction is row-preserving with respect to the explicit input manifest. No structure is silently removed because of validation status or a descriptor-level failure, and the output row order follows the input manifest order. Any filtering of cohorts must occur before descriptor extraction and must be explicit in the input manifest provenance.

| Column | Type | Definition |
|---|---|---|
| `descriptor_schema_version` | string | Constant schema identifier; `v1` for this specification. |
| `descriptor_status` | string | Overall extraction status: `ok`, `partial`, or `error`. |
| `descriptor_error_code` | nullable string | Machine-readable error code for a fatal descriptor-extraction failure. |
| `descriptor_error_message` | nullable string | Human-readable diagnostic message for a fatal descriptor-extraction failure. |

`descriptor_status = "ok"` means that all Descriptor v1 groups were calculated successfully. `partial` means that the structure was parsed and core descriptors were calculated, but at least one optional descriptor group or elemental-property group is unavailable. `error` means that the structure could not be parsed or the core descriptor extraction failed.

Missing scientific descriptor values are represented as `None` in memory and as empty fields in CSV output. Descriptor extraction performs no zero-filling, mean-filling, or other imputation. Imputation, if required for later statistical or machine-learning analysis, must be a separate downstream operation.

A symmetry or local-geometry failure does not erase successfully calculated structural or composition descriptors. Likewise, elemental-property coverage below `1.0` only invalidates the statistics for that specific property. Such cases set the overall `descriptor_status` to `partial` rather than `error`.

Floating-point descriptor values are stored without intentional pre-rounding. `sample_uid` must be unique within every output table.


## 6. Scope and deferred descriptors

Descriptor v1 is intentionally limited to reproducible descriptors that can be calculated directly from a parsed crystal structure and its composition with the dependencies already used by MagGenBench.

The following are explicitly outside Descriptor v1:

- oxidation-state inference and oxidation-state statistics;
- packing efficiency and packing-fraction descriptors;
- structural-complexity metrics;
- chemical-ordering metrics;
- advanced local-environment fingerprints and Voronoi-based descriptors;
- the 132 Magpie composition features used by the frozen DXMag model contract;
- predicted magnetic moments from DXMag;
- Curie-temperature predictions or CurieML features;
- site-resolved magnetic moments and magnetic-order labels;
- CHGNet energy predictions and relaxation-derived quantities;
- Heisenberg exchange parameters, TB2J calculations, and VAMPIRE-derived quantities.

These quantities may be joined to Descriptor v1 outputs as separate downstream result families, but they are not part of the Descriptor v1 scientific feature contract.

The frozen DXMag Magpie feature vector remains model-specific and must not be redefined or regenerated as part of the general descriptor schema. Likewise, CHGNet and DXMag outputs remain downstream model predictions rather than structural descriptors.

Candidate Descriptor v2 additions include packing efficiency, dimensionality, structural complexity, chemical ordering, additional local-property differences, and robust oxidation-state-derived statistics. Each addition requires an explicit definition and reproducibility test before entering the common benchmark schema.
