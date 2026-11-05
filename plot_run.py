"""Render PNG and SVG figures from a trainer metrics.json file."""
import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


COLORS = ("#0072B2", "#D55E00", "#009E73")
TITLES = {
    "diagnostics": "Microscopy classification",
    "followup": "Follow-up risk classification",
    "security": "Isolation Forest evaluation",
    "forecast": "District case anomaly forecasting",
}
plt.rcParams.update({
    "font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
    "axes.titleweight": "bold", "svg.fonttype": "none",
})


def bars(ax, names, values, title, xlabel, percent=False):
    positions = list(range(len(names)))
    shown = [100 * value if percent else value for value in values]
    patches = ax.barh(positions, shown, color=[COLORS[i % len(COLORS)] for i in positions])
    ax.set_yticks(positions, names)
    ax.invert_yaxis()
    ax.set_xlim(0, 115 if percent else max(shown, default=1) * 1.22 or 1)
    ax.bar_label(patches, labels=[f"{v:.0f}%" if percent else f"{v:.3f}" for v in shown], padding=4)
    ax.set(title=title, xlabel=xlabel)
    ax.grid(axis="x", alpha=0.2)
    ax.set_axisbelow(True)


def confusion(ax, metrics, names, title):
    counts = [[metrics["tn"], metrics["fp"]], [metrics["fn"], metrics["tp"]]]
    ax.imshow(counts, cmap="Blues", vmin=0, vmax=max(1, *(max(row) for row in counts)))
    for i, row in enumerate(counts):
        for j, count in enumerate(row):
            color = "white" if count > max(map(max, counts)) / 2 else "#172533"
            ax.text(j, i, str(count), ha="center", va="center", color=color, weight="bold")
    ax.set_xticks((0, 1), names)
    ax.set_yticks((0, 1), names)
    ax.set(xlabel="Predicted", ylabel="Observed", title=title)


def training_curve(ax, loss):
    if not loss:
        ax.text(0.5, 0.5, "Loss history unavailable for this run", ha="center", va="center")
        ax.set_axis_off()
        return
    if "pooled" in loss:
        ax.plot(loss["pooled"], color=COLORS[0], label="Pooled")
        ax.plot(loss["local_weighted"], color=COLORS[1], linestyle="--",
                label="Local, weighted mean")
        ax.plot(loss["federated_steps"], loss["federated"], color=COLORS[2], marker="o",
                markersize=4, linestyle="none", label="Federated, after aggregation")
        ax.legend(frameon=False, fontsize=9)
        xlabel = "Training steps per model or client"
    else:
        ax.plot(loss["model"], color=COLORS[0], marker="o", markersize=4)
        xlabel = "Training step"
    ax.set(title="Training loss", xlabel=xlabel, ylabel="Binary cross-entropy")
    ax.grid(alpha=0.25)


def render(report, out, label=None):
    mode, metrics = report["mode"], report["metrics"]
    title = label or TITLES[mode]
    if mode == "diagnostics":
        fig, axes = plt.subplots(2, 2, figsize=(11.5, 7.5), layout="constrained")
        loss, score, latency, matrix = axes.flat
        training_curve(loss, metrics.get("training_loss"))
        desktop = metrics["desktop"]
        times = [desktop[key] for key in ("p50_ms", "p95_ms", "max_ms")]
        if all(value is not None for value in times):
            bars(latency, ("Median", "95th percentile", "Maximum"), times,
                 f"Desktop latency ({desktop['completed']}/{desktop['attempted']} completed)",
                 "Milliseconds per image")
        else:
            latency.set_axis_off()
        if "federated" in metrics:
            bars(score, ("Pooled", "Mean local", "Federated"),
                 (metrics["pooled"]["accuracy"], metrics["mean_local_accuracy"],
                  metrics["federated"]["accuracy"]), "Held-out accuracy", "Accuracy", True)
            confusion(matrix, metrics["federated"], ("Negative", "Positive"),
                      "Federated holdout")
        else:
            for ax in (score, matrix):
                ax.set_axis_off()
            score.text(0.5, 0.5, "Test input failures prevented accuracy evaluation",
                       ha="center", va="center")
    elif mode == "followup":
        fig, axes = plt.subplots(1, 3, figsize=(13, 4.2), layout="constrained")
        training_curve(axes[0], metrics.get("training_loss"))
        bars(axes[1], ("Logistic model", "Majority class"),
             (metrics["model"]["accuracy"], metrics["baseline"]["accuracy"]),
             "Held-out accuracy", "Accuracy", True)
        confusion(axes[2], metrics["model"], ("Negative", "Positive"), "Model holdout")
    elif mode == "security":
        fig, axes = plt.subplots(1, 2, figsize=(9, 4.4), layout="constrained")
        confusion(axes[0], metrics, ("Benign", "Attack"), "Held-out scenarios")
        bars(axes[1], ("Attack sensitivity", "False-positive rate"),
             (metrics["sensitivity"], metrics["false_positive_rate"]),
             "Detection rates", "Share of each observed class", True)
    else:
        fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), layout="constrained")
        models = {"ridge": "Ridge", "persistence": "Persistence", "train_mean": "Training mean"}
        available = {key: name for key, name in models.items() if key in metrics}
        for ax, error in zip(axes, ("mae", "rmse")):
            bars(ax, tuple(available.values()), [metrics[key][error] for key in available],
                 f"Held-out {error.upper()}", "Target units")
    fig.suptitle(title, fontsize=15, fontweight="bold")
    for suffix in ("png", "svg"):
        fig.savefig(out / f"charts.{suffix}", dpi=300, facecolor="white")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metrics", type=Path)
    parser.add_argument("--title", help="Figure title, including cohort or horizon if applicable")
    args = parser.parse_args()
    report = json.loads(args.metrics.read_text(encoding="utf-8"))
    render(report, args.metrics.parent, args.title)


if __name__ == "__main__":
    main()
