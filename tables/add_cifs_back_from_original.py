from pathlib import Path
import pandas as pd
import shutil

base = Path("/mnt/tank/scratch/kkapranova/MagGenBench/MagGenBench")

downsampled_csv = base / "tables" / "mattergen_structures.downsampled.csv"
restore_root = base / "samples" / "mattergen_cifs"

df = pd.read_csv(downsampled_csv, low_memory=False)
restore_root.mkdir(parents=True, exist_ok=True)

restored = 0
missing = []

for _, row in df.iterrows():
    cif_path = row.get("cif_path")
    benchmark_group = row.get("benchmark_group")
    run_name = row.get("run_name")
    file_name = row.get("file_name")

    if pd.isna(cif_path) or pd.isna(benchmark_group) or pd.isna(run_name) or pd.isna(file_name):
        missing.append(f"missing metadata: cif_path={cif_path}, benchmark_group={benchmark_group}, run_name={run_name}, file_name={file_name}")
        continue

    src = Path(str(cif_path))
    benchmark_group = str(benchmark_group).strip()
    run_name = str(run_name).strip()
    file_name = str(file_name).strip()

    if not src.exists():
        missing.append(str(src))
        continue

    dst = restore_root / benchmark_group / run_name / file_name
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    restored += 1

print(f"Restored: {restored}")
print(f"Missing: {len(missing)}")

if missing:
    print("First missing examples:")
    for x in missing[:20]:
        print(x)