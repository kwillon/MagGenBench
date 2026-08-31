# Scientific Conventions

This document records interpretation constraints used throughout MagGenBench.

## Energy

CHGNet outputs used in this repository are ML-predicted total energies. They must not be described as DFT formation energies, energy above hull, or proof of thermodynamic stability.

## Magnetism

DXMag outputs are composition-based predicted magnetic moments. They do not establish FM, AFM, or FIM ordering, saturation magnetization, Curie temperature, or structure-dependent DFT magnetic moments.

## Magnetically informed descriptors

Descriptor v2 contains composition, magnetic-site geometry, and symmetry-derived proxies. Missing magnetic geometry for structures without configured magnetic sites is scientifically `not_applicable` and must not be silently replaced by zero.

## PCA and set-level shifts

PCA is descriptive. Centroid or median arrows summarize generated-set shifts and must not be interpreted as paired trajectories of individual structures or causal effects.

## Crys-JEPA Refined

Crys-JEPA Refined is a generatively refined comparator set. It is not a geometry relaxation of individual Crys-JEPA Base structures.
