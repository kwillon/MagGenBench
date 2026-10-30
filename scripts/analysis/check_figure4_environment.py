"""Paired environment-sensitivity check on the exact original smoke identities."""
import argparse
import json
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
from cifmagfilter.cli import extract
from cifmagfilter.model import CIFMagFilter

ROOT = Path(__file__).resolve().parents[2]


def compare_scored_records(first, scored):
    keys = ["dataset", "structure_id"]
    field = "magnetic_reference_vs_NM_contrast"
    paired = first[keys + [field]].merge(scored[keys + [field]], on=keys,
                                         suffixes=("_first", "_diagnostic"), validate="one_to_one")
    if len(paired) != len(scored) or len(paired) == 0:
        raise ValueError("Diagnostic scores must match all selected scored identities")
    return paired


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=ROOT / "reproduced/fig04_mp_only")
    parser.add_argument("--label", default="core_2026_10_16")
    parser.add_argument("--selection", choices=("smoke", "boundary", "quantiles"), default="smoke")
    args = parser.parse_args()
    base = args.base.resolve()
    output = base / "environment_sensitivity" / args.label
    if args.selection == "smoke":
        smoke = pd.read_csv(base / "results/mp_only_smoke/features/structure_features.csv")
    else:
        # A fixed boundary-sensitive diagnostic, applied identically to each
        # environment, never used to select or remove publication records.
        scores = pd.read_csv(base / "results/mp_only/generator_scores.csv")
        if args.selection == "boundary":
            selected = scores.assign(distance=scores.magnetic_reference_vs_NM_contrast.abs()).sort_values(
                ["dataset", "distance", "structure_id"]).groupby("dataset", sort=True).head(10)
        else:
            parts = []
            for ds in ("crystalformer", "crystalformer_finetuned"):
                group = scores.loc[scores.dataset.eq(ds)]
                for field, quantiles in (("magnetic_reference_vs_NM_contrast", (.05, .25, .5, .75, .95)),
                                         ("nearest_magnetic_reference_distance", (.5,))):
                    ordered = group.sort_values([field, "structure_id"])
                    for q in quantiles:
                        rank = int(np.floor(q*(len(ordered)-1)))
                        parts.append(ordered.iloc[max(0, rank-2):rank+4])
            selected = pd.concat(parts).drop_duplicates(["dataset", "structure_id"])
        full = pd.read_csv(base / "results/mp_only/features/structure_features.csv", low_memory=False)
        smoke = selected[["dataset", "structure_id"]].merge(full, on=["dataset", "structure_id"], validate="one_to_one")
    config = {"output_dir": str(output), "extraction": {"reject_disordered": True},
              "datasets": [{"name": row.dataset, "role": "query", "path": row.source_path}
                           for row in smoke.itertuples()]}
    output.mkdir(parents=True, exist_ok=True)
    (output / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    current = extract(config)
    keys = ["dataset", "structure_id"]
    old = smoke.set_index(keys).sort_index()
    new = current.set_index(keys).sort_index()
    pd.testing.assert_index_equal(old.index, new.index)
    pd.testing.assert_series_equal(old.parse_success, new.parse_success)
    model = CIFMagFilter.from_pretrained(ROOT / "filter/src/cifmagfilter/data/model")
    differences = []
    for feature in model.feature_names:
        a, b = old[feature].to_numpy(float), new[feature].to_numpy(float)
        changed = ~np.isclose(a, b, rtol=0, atol=1e-10, equal_nan=True)
        for index in np.flatnonzero(changed):
            differences.append({"dataset": old.index[index][0], "structure_id": old.index[index][1],
                                "feature": feature, "first_environment": a[index], "diagnostic": b[index]})
    pd.DataFrame(differences).to_csv(output / "feature_differences.csv", index=False)
    scored = model.score_features(current.loc[current.parse_success.eq(1)])
    scored.to_csv(output / "generator_scores.csv", index=False)
    first = pd.read_csv(base / ("results/mp_only_smoke/generator_scores.csv"
                               if args.selection == "smoke" else "results/mp_only/generator_scores.csv"))
    paired = compare_scored_records(first, scored)
    paired.to_csv(output / "contrast_comparison.csv", index=False)
    distance_fields = [c for c in ("nearest_magnetic_reference_distance", "distance_to_AFM", "distance_to_FM",
                                  "distance_to_FiM", "distance_to_NM") if c in first and c in scored]
    distances = first[keys + distance_fields].merge(scored[keys + distance_fields], on=keys,
                                                   suffixes=("_first", "_diagnostic"), validate="one_to_one")
    if len(distances) != len(scored):
        raise ValueError("Distance comparison lost selected identities")
    distances.to_csv(output / "distance_comparison.csv", index=False)
    result = {"pymatgen_core": version("pymatgen-core"), "rows": len(current),
              "selection": args.selection,
              "scored_pairs_compared": len(paired),
              "changed_feature_values": len(differences),
              "changed_scored_contrasts": int((~np.isclose(paired.iloc[:, 2], paired.iloc[:, 3], rtol=0, atol=1e-10)).sum())}
    result["distance_max_abs_differences"] = {
        field: float((distances[field+"_first"]-distances[field+"_diagnostic"]).abs().max())
        for field in distance_fields}
    (output / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
