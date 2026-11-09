# Table S9. Alternative chemical criteria and QC-retention ablation.

Provisional numbering. This separate table keeps Table S8 readable. Scores are dimensionless, normalized within each criterion across the same ten sets. Scores under different criterion systems are not directly comparable as performance gains. Frequencies use 20000 saved weights and seed 1984, with Dirichlet(1,...,1) dimension equal to the number of criteria.

## S9A. Original presence-based criteria (A)

Objectives: QC retention; unique-formula yield; 3d-containing yield.

Pareto-efficient sets (5): MatterGen Base, MatterGen FT, Con-CDVAE Base, Con-CDVAE FT, CrystalFormer FT.

| Generated set | Pareto | Score | Rank | First (%) | Top-3 (%) | Top-5 (%) |
|---|---|---:|---:|---:|---:|---:|
| MatterGen Base | Yes | 0.8450 | 1 | 44.820 | 98.795 | 100.000 |
| MatterGen FT | Yes | 0.6442 | 5 | 6.040 | 29.090 | 52.315 |
| Con-CDVAE Base | Yes | 0.8203 | 2 | 49.140 | 73.475 | 100.000 |
| Con-CDVAE FT | Yes | 0.6400 | 6 | 0.000 | 1.300 | 52.230 |
| CrystalFormer Base | No | 0.3620 | 8 | 0.000 | 0.000 | 0.350 |
| CrystalFormer FT | Yes | 0.6727 | 4 | 0.000 | 30.360 | 99.460 |
| CrystaLLM Base | No | 0.0000 | 10 | 0.000 | 0.000 | 0.000 |
| CrystaLLM FT | No | 0.0653 | 9 | 0.000 | 0.000 | 0.000 |
| Crys-JEPA Base | No | 0.7721 | 3 | 0.000 | 66.980 | 70.805 |
| Crys-JEPA Refined | No | 0.4378 | 7 | 0.000 | 0.000 | 24.840 |

## S9B. Four presence-based criteria (B)

Objectives: QC retention; unique-formula yield; 3d-containing yield; configured-lanthanide-containing yield.

Pareto-efficient sets (5): MatterGen Base, MatterGen FT, Con-CDVAE Base, Con-CDVAE FT, CrystalFormer FT.

| Generated set | Pareto | Score | Rank | First (%) | Top-3 (%) | Top-5 (%) |
|---|---|---:|---:|---:|---:|---:|
| MatterGen Base | Yes | 0.8648 | 2 | 42.210 | 99.955 | 100.000 |
| MatterGen FT | Yes | 0.4832 | 6 | 0.495 | 11.395 | 36.330 |
| Con-CDVAE Base | Yes | 0.8652 | 1 | 57.295 | 91.655 | 100.000 |
| Con-CDVAE FT | Yes | 0.4828 | 7 | 0.000 | 0.640 | 21.720 |
| CrystalFormer Base | No | 0.3701 | 8 | 0.000 | 0.000 | 24.095 |
| CrystalFormer FT | Yes | 0.5078 | 4 | 0.000 | 8.555 | 72.935 |
| CrystaLLM Base | No | 0.0032 | 10 | 0.000 | 0.000 | 0.000 |
| CrystaLLM FT | No | 0.0503 | 9 | 0.000 | 0.000 | 0.000 |
| Crys-JEPA Base | No | 0.7995 | 3 | 0.000 | 87.800 | 89.660 |
| Crys-JEPA Refined | No | 0.4858 | 5 | 0.000 | 0.000 | 55.260 |

## S9C. Four criteria including both atomic-content yields (C)

Objectives: QC retention; unique-formula yield; 3d atomic-content yield; configured-lanthanide atomic-content yield.

Pareto-efficient sets (7): MatterGen Base, MatterGen FT, Con-CDVAE Base, Con-CDVAE FT, CrystalFormer FT, Crys-JEPA Base, Crys-JEPA Refined.

| Generated set | Pareto | Score | Rank | First (%) | Top-3 (%) | Top-5 (%) |
|---|---|---:|---:|---:|---:|---:|
| MatterGen Base | Yes | 0.7858 | 1 | 63.845 | 97.640 | 100.000 |
| MatterGen FT | Yes | 0.4832 | 5 | 6.965 | 23.915 | 46.915 |
| Con-CDVAE Base | Yes | 0.6540 | 3 | 17.210 | 51.110 | 79.380 |
| Con-CDVAE FT | Yes | 0.4617 | 7 | 0.000 | 10.045 | 22.895 |
| CrystalFormer Base | No | 0.3738 | 8 | 0.000 | 0.000 | 28.630 |
| CrystalFormer FT | Yes | 0.4823 | 6 | 0.000 | 11.440 | 56.755 |
| CrystaLLM Base | No | 0.0018 | 10 | 0.000 | 0.000 | 0.000 |
| CrystaLLM FT | No | 0.0510 | 9 | 0.000 | 0.000 | 0.000 |
| Crys-JEPA Base | Yes | 0.6880 | 2 | 6.795 | 79.500 | 98.255 |
| Crys-JEPA Refined | Yes | 0.5799 | 4 | 5.185 | 26.350 | 67.170 |

## S9D. S1 without the separate QC-retention objective

Objectives: unique-formula yield; 3d atomic-content yield.

Pareto-efficient sets (6): MatterGen Base, MatterGen FT, Con-CDVAE Base, Con-CDVAE FT, CrystalFormer FT, Crys-JEPA Base.

| Generated set | Pareto | Score | Rank | First (%) | Top-3 (%) | Top-5 (%) |
|---|---|---:|---:|---:|---:|---:|
| MatterGen Base | Yes | 0.7105 | 1 | 31.800 | 70.760 | 100.000 |
| MatterGen FT | Yes | 0.6045 | 2 | 37.875 | 53.310 | 59.740 |
| Con-CDVAE Base | Yes | 0.5493 | 5 | 30.325 | 46.690 | 50.540 |
| Con-CDVAE FT | Yes | 0.5828 | 4 | 0.000 | 36.510 | 76.735 |
| CrystalFormer Base | No | 0.2336 | 8 | 0.000 | 0.000 | 2.765 |
| CrystalFormer FT | Yes | 0.5953 | 3 | 0.000 | 46.475 | 97.235 |
| CrystaLLM Base | No | 0.0000 | 10 | 0.000 | 0.000 | 0.000 |
| CrystaLLM FT | No | 0.0666 | 9 | 0.000 | 0.000 | 0.000 |
| Crys-JEPA Base | Yes | 0.5483 | 6 | 0.000 | 46.255 | 96.745 |
| Crys-JEPA Refined | No | 0.2507 | 7 | 0.000 | 0.000 | 16.240 |

## S9E. S2 without the separate QC-retention objective

Objectives: unique-formula yield; configured-lanthanide atomic-content yield.

Pareto-efficient sets (4): MatterGen Base, Con-CDVAE Base, Crys-JEPA Base, Crys-JEPA Refined.

| Generated set | Pareto | Score | Rank | First (%) | Top-3 (%) | Top-5 (%) |
|---|---|---:|---:|---:|---:|---:|
| MatterGen Base | Yes | 0.7953 | 2 | 5.175 | 100.000 | 100.000 |
| MatterGen FT | No | 0.1045 | 8 | 0.000 | 0.000 | 0.000 |
| Con-CDVAE Base | Yes | 0.7587 | 3 | 24.120 | 52.545 | 100.000 |
| Con-CDVAE FT | No | 0.1500 | 7 | 0.000 | 0.000 | 0.000 |
| CrystalFormer Base | No | 0.4249 | 5 | 0.000 | 0.000 | 100.000 |
| CrystalFormer FT | No | 0.1850 | 6 | 0.000 | 0.000 | 0.000 |
| CrystaLLM Base | No | 0.0036 | 10 | 0.000 | 0.000 | 0.000 |
| CrystaLLM FT | No | 0.0196 | 9 | 0.000 | 0.000 | 0.000 |
| Crys-JEPA Base | Yes | 0.8250 | 1 | 35.085 | 100.000 | 100.000 |
| Crys-JEPA Refined | Yes | 0.7304 | 4 | 35.620 | 47.455 | 100.000 |

## S9F. S3 without the separate QC-retention objective

Objectives: unique-formula yield; configured 3d/lanthanide union-presence yield (OR).

Pareto-efficient sets (2): MatterGen Base, Con-CDVAE Base.

| Generated set | Pareto | Score | Rank | First (%) | Top-3 (%) | Top-5 (%) |
|---|---|---:|---:|---:|---:|---:|
| MatterGen Base | Yes | 0.8756 | 1 | 57.390 | 100.000 | 100.000 |
| MatterGen FT | No | 0.5415 | 6 | 0.000 | 26.720 | 36.480 |
| Con-CDVAE Base | Yes | 0.8312 | 2 | 42.610 | 80.530 | 100.000 |
| Con-CDVAE FT | No | 0.5606 | 5 | 0.000 | 6.585 | 67.140 |
| CrystalFormer Base | No | 0.3212 | 8 | 0.000 | 0.000 | 3.780 |
| CrystalFormer FT | No | 0.5879 | 4 | 0.000 | 12.885 | 96.220 |
| CrystaLLM Base | No | 0.0000 | 10 | 0.000 | 0.000 | 0.000 |
| CrystaLLM FT | No | 0.0584 | 9 | 0.000 | 0.000 | 0.000 |
| Crys-JEPA Base | No | 0.7721 | 3 | 0.000 | 73.280 | 74.830 |
| Crys-JEPA Refined | No | 0.3492 | 7 | 0.000 | 0.000 | 21.550 |

For 2D ablation, only the separate QC objective is dropped: unique-formula yield and the scenario chemical yield retain Ngen=2000 and identical values/min-max normalization. QC filtering is not removed. All three scenario Pareto memberships are unchanged. A is the original presence-based three-objective analysis, not the updated atomic-content S1. B adds lanthanide presence to A; C replaces the chemical objectives with both atomic-content yields.
