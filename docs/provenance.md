# Source Provenance

## energies_updated

- URL: https://github.com/Austerlitz14/energies_updated.git
- source commit: ea834efdcec358496a9e0ce1b7f856a59a15ce2d
- original authors: TBD
- permission/license confirmation: TBD
- transferred concepts: backend abstraction, total-energy prediction contract, isolated-atom-reference proxy naming, structured error rows
- rewritten components: package-native schemas, records, fake backend, configuration contract
- scientific limitations: isolated-atom-reference values are proxies and must not be reported as true formation energy or e_above_hull

## magm_updated

- URL: https://github.com/Austerlitz14/magm_updated.git
- source commit: `1b29ec689054ef51fe739607d63fa0f57e6f6bb8`
- original authors: TBD
- permission/license confirmation: TBD
- transferred concepts: composition-feature prediction contract, Magpie
  composition feature set, model metadata requirement, `uncertainty_proxy`,
  confidence/risk categorization
- rewritten components: package-native schemas, records, fake backend, sklearn
  backend adapter, injectable model loader, injectable featurizer,
  configuration contract
- model artifact: `magmom_model_dxmag.pkl`
- artifact SHA-256:
  `a76d22393b4f7a2a32e9d57191ea88788a0e5596f262ee0048cc2a9a0facb936`
- model class: `lightgbm.sklearn.LGBMRegressor`
- verified feature contract: 132 ordered
  `ElementProperty.from_preset("magpie")` features from matminer `0.8.0`
- feature-order SHA-256:
  `8fdff659a05332499424f1f81e4817dd332cc60f2c8bd04b5b9620b66fd88344`
- verified training target: median DXMag
  `total magnetization (muB/f.u.)` grouped by formula
- output semantics: `moment_unit = "muB"` and
  `moment_normalization = "per_formula_unit"`
- scientific limitations: the prediction is composition-only and cannot
  distinguish polymorphs with the same formula; it is not a structure-dependent
  DFT magnetic moment, saturation magnetization, magnetic ordering, Curie
  temperature, or moment per atom
- deployment limitation: the binary artifact is not stored in Git and the
  sklearn backend is not enabled by default
