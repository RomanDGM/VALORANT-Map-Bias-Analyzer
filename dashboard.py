# dashboard.py — Results visualization with matplotlib

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
import numpy as np
import os


COLORS = {
    "ATTACKER": "#FF4655",   # VALORANT red
    "DEFENDER": "#4FC3F7",   # Defender blue
    "BALANCED": "#B0BEC5",   # Neutral grey
    "attacker": "#FF4655",
    "defender": "#4FC3F7",
}

plt.rcParams.update({
    "figure.facecolor": "#0F1923",
    "axes.facecolor":   "#0F1923",
    "axes.edgecolor":   "#3A4A5C",
    "axes.labelcolor":  "#FFFFFF",
    "xtick.color":      "#FFFFFF",
    "ytick.color":      "#FFFFFF",
    "text.color":       "#FFFFFF",
    "grid.color":       "#1E2D3D",
    "grid.linestyle":   "--",
    "grid.alpha":       0.5,
    "font.family":      "sans-serif",
})


def plot_win_rates(win_rates: pd.DataFrame, save_path="data/win_rates.png"):
    """Grouped bar chart: attacker vs defender win rate per map."""
    maps  = win_rates["map_name"].unique()
    x     = np.arange(len(maps))
    width = 0.35

    fig, ax = plt.subplots(figsize=(14, 6))
    fig.suptitle(
        "Win Rate by Map and Side — VALORANT Ranked",
        fontsize=14, fontweight="bold", color="#FF4655"
    )

    for i, side in enumerate(["attacker", "defender"]):
        vals = []
        for m in maps:
            row = win_rates[(win_rates["map_name"] == m) & (win_rates["starting_side"] == side)]
            vals.append(row["win_rate"].values[0] if len(row) > 0 else 0)

        bars = ax.bar(
            x + (i - 0.5) * width, vals, width,
            color=COLORS[side], label=side.capitalize(), alpha=0.85
        )
        for bar, val in zip(bars, vals):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.01,
                f"{val:.0%}", ha="center", va="bottom", fontsize=8
            )

    ax.axhline(0.5, color="#FFD700", linestyle="--", linewidth=1, label="50% (balanced)")
    ax.set_xticks(x)
    ax.set_xticklabels(maps, rotation=30, ha="right")
    ax.set_ylabel("Win Rate")
    ax.set_ylim(0, 0.75)
    ax.legend()
    ax.grid(axis="y")

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[Dashboard] Chart saved: {save_path}")


def plot_map_classification(classification: pd.DataFrame, save_path="data/classification.png"):
    """Horizontal bar chart showing attacker-defender win-rate differential per map."""
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.suptitle(
        "Map Classification: Attacker vs Defender",
        fontsize=13, fontweight="bold", color="#FF4655"
    )

    classification = classification.sort_values("difference")
    colors = [COLORS[c] for c in classification["classification"]]

    bars = ax.barh(classification["map_name"], classification["difference"], color=colors, alpha=0.85)

    for bar, val in zip(bars, classification["difference"]):
        label = f"{val:+.3f}"
        xpos  = val + 0.002 if val >= 0 else val - 0.002
        ha    = "left" if val >= 0 else "right"
        ax.text(xpos, bar.get_y() + bar.get_height() / 2, label, va="center", ha=ha, fontsize=9)

    ax.axvline(0,     color="#FFD700", linewidth=1.5)
    ax.axvline(0.05,  color="#FF4655", linewidth=0.8, linestyle=":")
    ax.axvline(-0.05, color="#4FC3F7", linewidth=0.8, linestyle=":")
    ax.set_xlabel("Win Rate Difference (Attacker − Defender)")
    ax.grid(axis="x")

    patches = [
        mpatches.Patch(color=COLORS["ATTACKER"], label="Favors Attacker"),
        mpatches.Patch(color=COLORS["DEFENDER"], label="Favors Defender"),
        mpatches.Patch(color=COLORS["BALANCED"], label="Balanced"),
    ]
    ax.legend(handles=patches, loc="lower right")

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[Dashboard] Chart saved: {save_path}")


def plot_confusion_matrix(cm, save_path="data/confusion_matrix.png"):
    """Visualize the logistic regression confusion matrix."""
    fig, ax = plt.subplots(figsize=(5, 4))
    fig.suptitle("Confusion Matrix — Logistic Regression", fontsize=12, fontweight="bold")

    im = ax.imshow(cm, cmap="Blues")
    plt.colorbar(im, ax=ax)

    labels = ["Loss", "Win"]
    ax.set_xticks([0, 1]); ax.set_yticks([0, 1])
    ax.set_xticklabels(labels); ax.set_yticklabels(labels)
    ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")

    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                    color="white" if cm[i, j] > cm.max() / 2 else "black", fontsize=14)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[Dashboard] Chart saved: {save_path}")


def generate_all(results: dict):
    """Generate all charts from analysis results."""
    os.makedirs("data", exist_ok=True)

    plot_win_rates(results["win_rates"])
    plot_map_classification(results["classification"])

    if results["model"] is not None:
        from sklearn.metrics import confusion_matrix
        df = results["dataframe"].copy()
        le_map, le_side = results["encoders"]
        df["map_encoded"]  = le_map.transform(df["map_name"])
        df["side_encoded"] = le_side.transform(df["starting_side"])
        X      = df[["map_encoded", "side_encoded"]]
        y      = df["won"]
        y_pred = results["model"].predict(X)
        cm     = confusion_matrix(y, y_pred)
        plot_confusion_matrix(cm)

    print("[Dashboard] All charts saved to /data/")
