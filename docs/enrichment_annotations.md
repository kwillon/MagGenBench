# Enrichment Annotations

## Scope

Phase 5A-1 creates a canonical annotation table from:

`tables/03_features/master_structures_with_classes.csv`

This table is the canonical manifest for the stage. It carries `sample_uid`,
`cif_path`, validation status, rejection reason, provenance columns, and
`compound_class`. At the energy and magnetism contract boundary,
`structure_id = sample_uid`; both fields are preserved in the output.

The legacy table
`tables/02_validation/master_structures_with_validation_status.csv` has a CSV
serialization problem: the header contains 105 fields, only 40 data rows have
105 fields, and the remaining data rows contain more than 105 fields. Phase
5A-1 does not use late columns from that table as reliable status or descriptor
sources.

## Output

The intended generated output is:

`tables/04_magnetic_screening/master_structures_with_enrichment_annotations.csv`

Generated CSV output is not added to Git.

## Descriptors

Descriptors are recomputed from each row's `cif_path`. Existing legacy columns
such as `n_atoms`, `volume`, `density`, `volume_per_atom`,
`spacegroup_number`, and `spacegroup_symbol` are preserved as provenance. New
recomputed fields use explicit names:

- `n_sites`
- `composition_num_atoms`
- `volume_A3`
- `volume_per_site_A3`
- `volume_per_composition_atom_A3`
- `density_g_cm3`
- `crystal_system`
- `point_group_symbol`
- `space_group_number_recomputed`
- `space_group_symbol_recomputed`
- `descriptor_status`
- `descriptor_error_code`
- `descriptor_error_message`
- `descriptor_source`

`SpacegroupAnalyzer` is imported lazily by the default symmetry provider.
Symmetry failures preserve basic descriptors and mark
`descriptor_status = partial`.

## Magnetic Annotations

Magnetic flags are composition heuristics only. They identify configured
candidate magnetic elements and do not prove NM, FM, AFM, FiM, saturation
magnetization, magnetic ordering, or a DFT magnetic moment.

Magnetic element groups and compound-class screening rules come from
`config/magnetism.yaml` through `load_magnetism_config()`. The annotation module
does not keep a second Python copy of those lists.

The stage records configured magnetic species, magnetic site counts, 3d/4f
presence, and stable machine-readable screening reasons. Partially occupied
mixed sites are counted once when any configured magnetic element has positive
occupancy on that site.

## Compound Class

`compound_class` is not recomputed. Phase 5A-1 adds annotate-only fields:

- `compound_class_filter_status`
- `compound_class_filter_reason`

Rows are not removed, validation status is not changed, and downstream
energy/magnetism runs are not automatically blocked. Unlisted compound classes
are treated as `accepted` because this stage is annotation-only and should avoid
silently excluding new taxonomy values.

## Error And Output Policy

Every input row is preserved unless the manifest itself is invalid, such as a
duplicate or empty `sample_uid`. CIF parse errors and descriptor errors become
structured row annotations. Output is written atomically through a temporary
file next to the target and then replaced.

Phase 5A-1 intentionally does not run energy inference, DXMag/sklearn
inference, MatGL, CHGNet, LightGBM, matminer featurization, DFT orchestration,
magnetic structure enumeration, or CollinearMagneticStructureAnalyzer.
Energy and DXMag results will be attached in a separate Phase 5A-2.
