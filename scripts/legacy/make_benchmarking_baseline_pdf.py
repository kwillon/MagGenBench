from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


PROJECT_ROOT = Path("/mnt/tank/scratch/kkapranova/MagGenBench/MagGenBench")

INPUT_CSV = PROJECT_ROOT / "tables" / "benchmarking_baseline_table.csv"
OUTPUT_PDF = PROJECT_ROOT / "tables" / "benchmarking_baseline_table.pdf"


def main():
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV)

    # Optional: round numeric columns for cleaner paper-style table
    for col in df.select_dtypes(include="number").columns:
        df[col] = df[col].round(3)

    n_rows, n_cols = df.shape

    # Dynamic figure size
    fig_width = max(12, n_cols * 1.6)
    fig_height = max(3, n_rows * 0.45 + 1.5)

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.axis("off")

    table = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        cellLoc="center",
        colLoc="center",
        loc="center",
    )

    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.35)

    # Header formatting
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_text_props(weight="bold")
        cell.set_linewidth(0.4)

    plt.title("Benchmarking Baseline Table", fontsize=14, weight="bold", pad=20)
    plt.tight_layout()

    OUTPUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_PDF, format="pdf", bbox_inches="tight")
    plt.close()

    print(f"Saved PDF: {OUTPUT_PDF}")


if __name__ == "__main__":
    main()