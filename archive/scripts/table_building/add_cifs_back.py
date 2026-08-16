from pathlib import Path
import pandas as pd
import shutil

base = Path("/mnt/tank/scratch/kkapranova/MagGenBench/MagGenBench")

downsampled_csv = base / "tables" / "mattergen_structures.downsampled.csv"
archive_root = base / "archive" / "cifs" / "mattergen_cifs_archived_2400"
restore_root = base / "samples" / "mattergen_cifs"

df = pd.read_csv(downsampled_csv, low_memory=False)
restore_root.mkdir(parents=True, exist_ok=True)

# Индекс архивных CIF по (benchmark_group, run_name, file_name)
archive_index = {}

for p in archive_root.rglob("*.cif"):
    file_name = p.name
    run_name = p.parent.name
    benchmark_group = p.parent.parent.name if p.parent.parent != archive_root else None
    archive_index[(benchmark_group, run_name, file_name)] = p

restored = 0
missing = []

for _, row in df.iterrows():
    benchmark_group = str(row.get("benchmark_group")).strip() if pd.notna(row.get("benchmark_group")) else None
    run_name = str(row.get("run_name")).strip() if pd.notna(row.get("run_name")) else None
    file_name = str(row.get("file_name")).strip() if pd.notna(row.get("file_name")) else None

    if not benchmark_group or not run_name or not file_name:
        missing.append(f"missing metadata: benchmark_group={benchmark_group}, run_name={run_name}, file_name={file_name}")
        continue

    archived_path = archive_index.get((benchmark_group, run_name, file_name))
    if archived_path is None:
        missing.append(f"{benchmark_group}/{run_name}/{file_name}")
        continue

    restored_path = restore_root / benchmark_group / run_name / file_name
    restored_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(archived_path, restored_path)
    restored += 1

print(f"Restored: {restored}")
print(f"Missing: {len(missing)}")

if missing:
    print("First missing examples:")
    for x in missing[:20]:
        print(x)