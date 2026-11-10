# Scientific data provenance and publication assets

## Publication figures

The selected multiobjective comparison is Figure 7,
[fig07_multiobjective.pdf](../paper/figures/fig07_multiobjective.pdf).
Its caption is in [publication figure captions](../paper/figures/figure_captions.md#figure-7).
It retains the former Figure 8 PDF bytes and the hybrid layout: five structural
and chemical metrics in A; the S1 Pareto scatter in B; S1 rank distributions in C;
and S1 Top-5 frequencies in D. Historical Figure 8 artifacts and frozen numerical
inputs retain their original identifiers.

The [figure map](../paper/figures/README.md) identifies selected assets,
reproduction entry points and source tables.
[SHA256SUMS.txt](../paper/figures/SHA256SUMS.txt) covers all current and archived PDFs.
No scientific values or plotted results were changed by renumbering.

## Magnetic-domain preparation provenance

The [adaptation data documentation](../adaptation_data/README.md) describes
1,426 source-labelled NovoMag structures, split into 1,139 training, 142 validation
and 145 test records. The source export carries seed label 1041 and has disjoint
reduced-composition groups; the original split-generator implementation remains
unavailable. The CrystalFormer-compatible variant has 1,134 training records
and unchanged validation/test sets. CrystaLLM normalized CIFs and token inputs
preserve the recovered record populations.

[Preparation evidence](../adaptation_data/preparation/README.md) connects all
1,426 records to a 5,203-row intermediate table and the supplied NOVAMAG archive.
Every retained record matches source-local identifiers, formula, CIF reference,
cell spin polarization and volume. All 1,426 archive CIFs match after newline
normalization, including 1,424 exact byte matches.

For every retained record, the saved candidate_mag_density agrees with source
cell spin polarization divided by source cell volume. The maximum absolute
discrepancy at Decimal precision 40 is 3.59736671174129614209890e-17.
Source property documentation supports ratio units mu_B/Angstrom^3. This
numerical identity does not recover the original target-calculation code.
The 3,777 nonretained intermediate records have no recovered historical
exclusion log; their actual exclusion reasons remain undocumented.

The curated NOVAMAG splits, normalized tuples, tokens and their manifests are
published under CC BY 4.0. The source deposit's official license and exact
archive checksum are recorded in the
[redistribution review](../adaptation_data/provenance/redistribution_review.json).
The mixed-source selection ledger and NEMAD materials remain private; their
rights are not established by the NOVAMAG license. The repository's MIT
software license is not the basis for redistributing these third-party data.

## DFT result summaries and Figure 4

The tracked [FM source map](../filter/paper/data/dft_fm_source_map.csv) contains
324 historical DFT result summaries and unique dataset/CIF-hash identities.
The [AFM/FM source map](../filter/paper/data/dft_afm_source_map.csv) contains
60 overlapping records, including energies, energy differences, moment
summaries and ground-state labels. These are more than identity metadata,
but they are not original VASP run files.

[recalculate_dft_mp_only.py](../filter/scripts/recalculate_dft_mp_only.py)
joins existing measured labels to current MP-only screening scores and derives
retrospective confirmation fractions and Wilson intervals.
[plot_mp_only_publication.py](../filter/scripts/plot_mp_only_publication.py)
validates the join and plots those derived statistics. Neither script launches
VASP. Original electronic-structure inputs, outputs and convergence settings
are absent from the tracked release, so those calculations cannot be rerun
from first-principles inputs using this checkout alone.

The selected Figure 4 preserves original plotted statistical vectors rather
than the numerically different MP-only recalculation.
Its original confirmation counts remain 52/55, 54/73, 24/45 and 45/58.
The historical DFT population was selected under an earlier reference setup;
it is not independent validation of current screening panels.
See [Figure 4 reproduction limitations](figures/figure4_reproduction.md).

## Third-party attribution and remaining limitations

The filter is a separately attributed package under
[BSD-3-Clause](../filter/LICENSE).
Its [package metadata](../filter/pyproject.toml) and
[citation record](../filter/CITATION.cff) identify generic authors/contributors;
individual authorship and a complete associated-paper citation need clarification.
Those notices and historical source maps are preserved.

CHGNet inference uses an external pretrained model; DXMag uses an externally
supplied composition-based model. Neither adapter is a first-principles DFT
workflow. The [donor provenance record](provenance.md) preserves source
repositories, commits, rewritten components and unresolved author/permission
details. These limitations are not represented as confirmed permission or
infringement.

Other unresolved items include historical cleaning/splitting implementations,
model-input/checkpoint links, ambiguous NEMAD record matching, malformed source
JSON entries and rights for the unreviewed mixed-source materials. Prepared-data integrity
does not by itself prove actual use in a particular training job.
