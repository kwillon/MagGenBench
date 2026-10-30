# Figure 3 caption

**Figure 3. Magnetic-domain composition and local environments across ten
structurally retained benchmark sets (12281 structures).** Each set starts
from 2000 harmonized benchmark structures; its post-QC population, not
the raw generation count or the number of successful energy/magnetism
predictions, defines the descriptor audit population.
(A) Prevalence of nonzero configured
3d transition-metal content (top) and the distribution of 3d atomic
fractions among nonzero structures (bottom). (B) The corresponding
prevalence and conditional distribution for configured lanthanides.
Atomic fractions use all atoms in each structure as the denominator,
including fractional occupancies. The configured 3d set is Sc, Ti, V, Cr,
Mn, Fe, Co, Ni and Cu; the configured lanthanide set is Ce, Pr, Nd, Sm,
Eu, Gd, Tb, Dy, Ho, Er, Tm and Yb. Prevalence is the number of structures
with a finite positive fraction divided by the number with an available
finite fraction in the same QC-retained set; missing values are excluded
and are not replaced by zeros. The nonzero population size is indicated
by n+. (C) Distribution of the mean magnetic-neighbor fraction over
configured magnetic sites in each applicable structure, including valid
zero values. At each central magnetic site, this fraction is the
unweighted number of configured magnetic neighbors divided by its total
MinimumDistanceNN coordination, then averaged equally over central
magnetic sites. The configured magnetic set additionally includes Mo,
Ru, Rh, Pd, Re, Os and Ir. Neighborhoods use periodic structures, a 10 A
cutoff and a relative nearest-neighbor tolerance of 0.1, with
get_all_sites=false and use_weights=false. Panel C includes only records
with magnetic_geometry_status=ok and a finite fraction; n denotes this
population. Structures without configured magnetic sites are
not-applicable, and missing or failed geometry records are excluded
separately. These elemental and geometric heuristics do not establish
magnetic order or require successful CHGNet or DXMag predictions.
Model-family colors are shared across Base and adapted variants;
Base uses solid fill, and fine-tuned (FT) and Refined variants use the same
family hue with diagonal hatching in both bars and boxes. Separate Generator
and Version legends define these encodings. A dashed separator marks the Crys-JEPA Base
and Refined (Ref.) comparators. Boxes span the interquartile range with
median lines; whiskers extend to the most extreme values within 1.5
interquartile ranges, and outliers are not drawn.
