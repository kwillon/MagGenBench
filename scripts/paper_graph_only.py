import matplotlib
matplotlib.use("Agg")  # важно для сервера

import matplotlib.pyplot as plt
from pathlib import Path

# ---- ДАННЫЕ ----
models = ["Con-CDVAE", "CrystalFormer", "CrystaLLM", "MatterGen"]

comp_valid = [
    0.932,
    0.5415,
    0.049,
    0.8285
]

# ---- ПАПКА ДЛЯ СОХРАНЕНИЯ ----
outdir = Path("figures_stats_paper")
outdir.mkdir(exist_ok=True)

# ---- ГРАФИК ----
plt.figure(figsize=(8, 5), dpi=200)

bars = plt.bar(
    models,
    comp_valid,
    color="#4C72B0",
    edgecolor="black",
    linewidth=0.4
)

# ---- ПОДПИСИ НАД СТОЛБЦАМИ ----
for bar in bars:
    h = bar.get_height()
    plt.text(
        bar.get_x() + bar.get_width()/2,
        h + 0.005,
        f"{h*100:.1f}%",
        ha='center',
        va='bottom',
        fontsize=10
    )

# ---- ОФОРМЛЕНИЕ ----
plt.ylim(0.85, 1.02)  # аккуратнее под твои данные
plt.ylabel("Composition validity", fontsize=12)
plt.title("Chemical Validity Comparison", fontsize=14)

plt.grid(axis="y", linestyle="--", alpha=0.3)

plt.tight_layout()

# ---- СОХРАНЕНИЕ ----
outfile = outdir / "composition_validity.png"
plt.savefig(outfile, bbox_inches="tight")
print(f"Saved to: {outfile.resolve()}")

plt.close()