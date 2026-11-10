# Publication figure captions

## Figure 2

**Figure 2. Structural quality control across ten generated benchmark sets.**
(A) Retention for the MatterGen, Con-CDVAE, CrystalFormer and CrystaLLM Base
sets. (B) Retention for the four corresponding fine-tuned (FT) sets, in the
same model order and on the same scale as panel A. (C) Retention for Crys-JEPA
Base and Refined (Ref.). Bars are annotated with the number of structures
retained after structural quality control (QC) and the retention percentage.
Retention is calculated as the number with QC status `validated` divided by
the full harmonized benchmark population of the corresponding set (2000
structures), including retained and rejected structures. Raw generation
counts, which may be 2016 before benchmark harmonization, are not used as
these denominators. Family colors are preserved across Base and adapted
variants. (D) Registered primary rejection reasons for the five Base sets,
including Crys-JEPA Base: duplicates, charge-balance failure, crystallographic
information file (CIF) parse errors, implausible interatomic
distances and unrealistic density. Each cell gives the percentage of all
rejected structures in that set assigned the indicated registered primary
reason; the rejected population size is shown beside each row. These are
registered primary reasons, not an exhaustive inventory of every defect in
each structure. Counts in A-C describe structural QC retention and do not
require successful CHGNet energy predictions, DXMag magnetic predictions or
descriptor records.

## Figure 3

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

## Figure 4

**MP-only magnetic-reference screening and retrospective DFT validation.**
(A) Fraction of scored candidates closer to a magnetic than to the NM reference,
with reduced-formula cluster-bootstrap 95% confidence intervals.
(B) Magnetic-reference contrast, d(NM) - d(magnetic): thin intervals indicate
the 5th-95th percentiles, thick bands the interquartile range, and dark ticks
(Base) or diamonds (Fine-tuned/Refined) the medians.
(C) AFM, FM and FiM reference-branch fractions among magnetic-like candidates
(contrast > 0). Class colors have a separate legend; hatching denotes adapted
variants throughout. Reference affinity is not a ground-state prediction.
(D) DFT magnetic confirmation among the selected MP-only magnetic-like
candidates for four Base generators, with Wilson 95% confidence intervals:
MatterGen 52/55, Con-CDVAE 54/73, CrystalFormer 24/45 and CrystaLLM 45/58.
The historical DFT cohort was selected with the previous reference model;
this retrospective comparison is not an unbiased independent test of A-C.

## Figure 5

**Figure 5. Predicted energy-magnetism landscape across ten structurally
retained benchmark cohorts.** (A) Multicolor scatter of paired CHGNet
total-energy and DXMag moment predictions, with one color per generator.
There are 12,277 finite pairs from 12,281 QC-retained structures; four rows
without finite pairs are excluded. The full-width A panel is followed by
MatterGen, Con-CDVAE and CrystalFormer in B-D and CrystaLLM and Crys-JEPA
in E-F. Circles show Base predictions and triangles show fine-tuned predictions
(Refined for Crys-JEPA). Open diamonds mark Base population medians and filled
diamonds mark adapted population medians. Arrows point from Base to adapted
group medians, not along matched-sample trajectories. All finite pairs are
passed to the scatter artists, without subsampling. The historical common
display window is restored: each axis spans its pooled 0.5th to 99.5th
percentiles, padded by 6% of that energy span and 8% of that moment span.
Extreme points outside the window are not visible; medians use the full
finite populations. Energies are CHGNet-predicted total energies in
eV/atom, not formation energies or convex-hull stability. DXMag moments in
mu_B/f.u. are composition-based predictions and do not identify magnetic ground
states.

## Figure 7

**Figure 7. Structural and chemical trade-offs and ranking sensitivity across ten generated sets.**
(A) QC retention, unique reduced-formula yield, 3d atomic-content yield,
configured-lanthanide atomic-content yield, and configured 3d/lanthanide
union-presence yield. Numbers are original percentages; colors are independently
min-max normalized within each metric across all ten sets. All yields use a
nominal harmonized generation budget of 2000 structures per set. Atomic-content
yields sum per-structure atomic fractions over QC-retained structures and divide
by this budget; union-presence yield counts accepted structures containing at
least one element from either configured group, counting each structure once.
(B) QC retention versus unique-formula yield for S1. Marker area increases with
3d atomic-content yield; colors identify generator families, and circles, squares
and diamonds distinguish Base, Fine-tuned and Refined variants. Dark outlines
identify the three-objective S1 Pareto frontier.
(C) S1 rank distributions across 20000 Dirichlet(1,1,1) objective-weight
combinations (seed 1984), applied to min-max-normalized QC retention,
unique-formula yield and 3d atomic-content yield. Color gives the percentage
of weight combinations at each rank (1 = best).
(D) Percentage of the same S1 weight combinations placing each generated set
among the top five, sorted in descending order. Labels retain the 0.005
percentage-point resolution of the sampled weights. Panel D is not a
first-place-frequency plot. Panels B-D concern S1 only; S2/S3 and criterion
ablation are documented in the Supporting Information. Ranking frequencies
describe sensitivity to the selected objectives and weights, not probabilities
of intrinsic superiority. These chemical proxies do not establish magnetic
order, moments or functional performance.
