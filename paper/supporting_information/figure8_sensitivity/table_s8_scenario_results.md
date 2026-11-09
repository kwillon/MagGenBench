# Table S8. Scenario-specific Pareto efficiency, equal-weight rankings, and ranking sensitivity across generated sets.

Provisional numbering; existing manuscript references are unchanged. FT = Fine-tuned. All yields use the nominal budget Ngen = 2000 and contributions from QC-retained structures. Unique = unique reduced-formula yield, not within-QC uniqueness. Chemical = S1: 3d atomic-content yield; S2: configured-lanthanide atomic-content yield; S3: configured 3d/lanthanide union-presence yield (OR). Scores are the mean of three independently min-max-normalized criteria across all ten sets; rank 1 is best. Frequencies are exact to 0.005 percentage points from 20000 Dirichlet(1,1,1) weights, seed 1984, and are shown with three decimals. Pareto refers to all three scenario objectives.

## S1

| Generated set | QC (%) | Unique (%) | Chemical (%) | Pareto | Score | Rank | First (%) | Top-3 (%) | Top-5 (%) |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|
| MatterGen Base | 82.85 | 69.60 | 38.98 | Yes | 0.7679 | 1 | 32.515 | 85.010 | 100.000 |
| MatterGen FT | 68.80 | 20.60 | 57.18 | Yes | 0.6442 | 4 | 25.660 | 42.730 | 65.020 |
| Con-CDVAE Base | 93.20 | 92.10 | 7.50 | Yes | 0.6995 | 2 | 41.825 | 60.785 | 74.275 |
| Con-CDVAE FT | 64.95 | 28.70 | 49.85 | Yes | 0.6152 | 6 | 0.000 | 16.540 | 48.500 |
| CrystalFormer Base | 54.15 | 36.00 | 6.90 | No | 0.3417 | 8 | 0.000 | 0.000 | 0.365 |
| CrystalFormer FT | 69.00 | 34.00 | 47.99 | Yes | 0.6388 | 5 | 0.000 | 37.685 | 98.645 |
| CrystaLLM Base | 4.90 | 1.70 | 2.07 | No | 0.0000 | 10 | 0.000 | 0.000 | 0.000 |
| CrystaLLM FT | 10.85 | 4.95 | 7.42 | No | 0.0668 | 9 | 0.000 | 0.000 | 0.000 |
| Crys-JEPA Base | 88.20 | 86.50 | 10.81 | Yes | 0.6800 | 3 | 0.000 | 57.250 | 87.030 |
| Crys-JEPA Refined | 77.15 | 43.35 | 4.30 | No | 0.4398 | 7 | 0.000 | 0.000 | 26.165 |

## S2

| Generated set | QC (%) | Unique (%) | Chemical (%) | Pareto | Score | Rank | First (%) | Top-3 (%) | Top-5 (%) |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|
| MatterGen Base | 82.85 | 69.60 | 8.69 | Yes | 0.8245 | 3 | 2.510 | 100.000 | 100.000 |
| MatterGen FT | 68.80 | 20.60 | 0.0045 | No | 0.3109 | 8 | 0.000 | 0.000 | 0.000 |
| Con-CDVAE Base | 93.20 | 92.10 | 5.36 | Yes | 0.8392 | 2 | 40.825 | 65.290 | 100.000 |
| Con-CDVAE FT | 64.95 | 28.70 | 0.02 | No | 0.3267 | 7 | 0.000 | 0.000 | 0.000 |
| CrystalFormer Base | 54.15 | 36.00 | 4.87 | No | 0.4692 | 5 | 0.000 | 0.000 | 76.375 |
| CrystalFormer FT | 69.00 | 34.00 | 0.14 | No | 0.3653 | 6 | 0.000 | 0.000 | 23.625 |
| CrystaLLM Base | 4.90 | 1.70 | 0.08 | No | 0.0024 | 10 | 0.000 | 0.000 | 0.000 |
| CrystaLLM FT | 10.85 | 4.95 | 0.04 | No | 0.0356 | 9 | 0.000 | 0.000 | 0.000 |
| Crys-JEPA Base | 88.20 | 86.50 | 7.37 | Yes | 0.8645 | 1 | 31.340 | 100.000 | 100.000 |
| Crys-JEPA Refined | 77.15 | 43.35 | 10.35 | Yes | 0.7597 | 4 | 25.325 | 34.710 | 100.000 |

## S3

| Generated set | QC (%) | Unique (%) | Chemical (%) | Pareto | Score | Rank | First (%) | Top-3 (%) | Top-5 (%) |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|
| MatterGen Base | 82.85 | 69.60 | 77.90 | Yes | 0.8780 | 2 | 42.975 | 100.000 | 100.000 |
| MatterGen FT | 68.80 | 20.60 | 68.70 | No | 0.6022 | 5 | 0.000 | 14.895 | 46.610 |
| Con-CDVAE Base | 93.20 | 92.10 | 53.25 | Yes | 0.8874 | 1 | 57.025 | 92.810 | 100.000 |
| Con-CDVAE FT | 64.95 | 28.70 | 64.95 | No | 0.6004 | 6 | 0.000 | 0.445 | 30.955 |
| CrystalFormer Base | 54.15 | 36.00 | 24.10 | No | 0.4001 | 8 | 0.000 | 0.000 | 0.475 |
| CrystalFormer FT | 69.00 | 34.00 | 64.65 | No | 0.6339 | 4 | 0.000 | 6.745 | 99.060 |
| CrystaLLM Base | 4.90 | 1.70 | 4.90 | No | 0.0000 | 10 | 0.000 | 0.000 | 0.000 |
| CrystaLLM FT | 10.85 | 4.95 | 10.80 | No | 0.0614 | 9 | 0.000 | 0.000 | 0.000 |
| Crys-JEPA Base | 88.20 | 86.50 | 49.15 | No | 0.8292 | 3 | 0.000 | 85.105 | 88.325 |
| Crys-JEPA Refined | 77.15 | 43.35 | 22.25 | No | 0.5055 | 7 | 0.000 | 0.000 | 34.575 |

Figure 8B-C show S1 Pareto/rank sensitivity; Figure 8D shows S1 Top-5 only. S2/S3 frequencies are reported here. Full source-precision scores and integer counts are in `scenario_sensitivity_publication.csv`.
