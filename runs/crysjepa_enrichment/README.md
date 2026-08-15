# Crys-JEPA enrichment runtime provenance

The Crys-JEPA enrichment workflow uses the DXMag runtime model artifact:

`models/magnetism/magmom_model_dxmag.pkl`

This binary artifact is not versioned in this checkpoint. Before running
`runs/crysjepa_enrichment/run.sh`, the model must be available at the exact
path above.

Frozen SHA-256:

`a76d22393b4f7a2a32e9d57191ea88788a0e5596f262ee0048cc2a9a0facb936`

The frozen hashes of the runtime model and final Crys-JEPA downstream tables
are recorded in `runs/crysjepa_enrichment/final_sha256.txt`.

The final enrichment audit requires the expected row count and `status == "ok"`
for every CHGNet and DXMag record.
