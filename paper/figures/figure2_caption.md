# Figure 2 caption

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
