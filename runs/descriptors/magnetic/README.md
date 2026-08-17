# Magnetic Descriptor v2

Magnetic Descriptor v2 is a separate, deterministic, CIF-derived descriptor
layer. It exists to characterize magnetic composition and the geometry of a
potential magnetic sublattice. It does not replace Descriptor v1 and does not
modify Analysis v1 or the standardized CHGNet/DXMag artifacts.

The production input is:

`tables/08_standardized_enrichment/standardized_enrichment.csv`

The run recipe writes generated output to:

`reproduced/descriptor_v2_magnetic/descriptor_v2_magnetic.csv`

No tracked production Descriptor-v2 CSV is created in this checkpoint.

## Scientific Fields

The schema contains exactly 24 scientific descriptor fields:

1. `transition_3d_fraction`
2. `selected_4d_5d_fraction`
3. `configured_lanthanide_fraction`
4. `n_transition_3d_species`
5. `n_selected_4d_5d_species`
6. `n_configured_lanthanide_species`
7. `contains_3d_and_configured_lanthanide`
8. `magnetic_site_nearest_neighbor_distance_min`
9. `magnetic_site_nearest_neighbor_distance_mean`
10. `magnetic_site_nearest_neighbor_distance_std`
11. `magnetic_site_nearest_magnetic_neighbor_distance_min`
12. `magnetic_site_nearest_magnetic_neighbor_distance_mean`
13. `magnetic_site_nearest_magnetic_neighbor_distance_std`
14. `magnetic_site_coordination_mean`
15. `magnetic_site_coordination_std`
16. `magnetic_site_magnetic_coordination_mean`
17. `magnetic_site_magnetic_coordination_std`
18. `magnetic_site_magnetic_neighbor_fraction_mean`
19. `magnetic_site_magnetic_neighbor_fraction_std`
20. `n_symmetry_unique_sites`
21. `symmetry_unique_site_fraction`
22. `n_symmetry_unique_magnetic_sites`
23. `symmetry_unique_magnetic_site_fraction`
24. `site_multiplicity_entropy`

Identity and status/provenance fields are outside this 24-field scientific
descriptor set.

## Magnetic Element Definitions

Descriptor v2 reuses the magnetic element groups from `config/magnetism.yaml`:

- `transition_3d`
- `selected_4d_5d`
- configured `lanthanides`

A crystallographic site is a configured magnetic site when any element
occupying that site belongs to the configured magnetic-element union. This
applies to partially occupied or disordered sites.

## Geometry Semantics

Nearest-neighbor distances use pymatgen periodic boundary conditions. For each
configured magnetic site, Descriptor v2 records the nearest nonzero periodic
neighbor of any elemental type and the nearest nonzero periodic configured
magnetic neighbor. Periodic images count as legitimate neighbors; only
zero-distance self matches are excluded.

Coordination uses `pymatgen.core.local_env.MinimumDistanceNN` with:

- `cutoff_angstrom: 10.0`
- `tolerance: 0.1`
- `get_all_sites: false`
- `use_weights: false`

Magnetic coordination is counted within that same `MinimumDistanceNN`
coordination shell. Magnetic-neighbor fraction is magnetic coordination divided
by total coordination.

## Nonmagnetic Structures

Structures with no configured magnetic sites are valid. Composition fractions
and species counts are zero, the 12 magnetic-geometry fields are missing, and
`magnetic_geometry_status` is `not_applicable`. Symmetry descriptors that do
not require magnetic sites are still computed. The overall status can remain
`ok`.

## Symmetry Semantics

Symmetry uses pymatgen symmetry analysis with:

- `symprec: 0.01`
- `angle_tolerance: 5`

`n_symmetry_unique_sites` is the number of equivalent-site groups.
`symmetry_unique_site_fraction` is that count divided by the number of
crystallographic sites. Magnetic symmetry counts equivalent-site groups that
contain at least one configured magnetic site. `site_multiplicity_entropy` is
the natural-log entropy of equivalent-site group multiplicities and is not
normalized.

## Status Semantics

The batch runner preserves one output row per input row. CIF parse failures
produce `descriptor_v2_status = error`. Unexpected block failures produce
`partial` when another block succeeds. Missing values are emitted as empty CSV
cells; zero is never used as an error sentinel.

## Scientific Limitations

These descriptors do not predict magnetic order, exchange constants, Curie
temperature, thermodynamic stability, energy above hull, or DFT magnetic
moments. They do not implement CHGNet local moments, bridge-angle descriptors,
Goodenough-Kanamori rules, oxidation states, SOAP, ACSF, Coulomb matrices,
TB2J, VAMPIRE, or candidate ranking.
