"""Generate aggregate exploratory charts from the two local research archives."""
import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from datetime import date
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from prepare_makerere import audit
from prepare_pangaea import MEMBER, shift_month


BLUE, ORANGE, TEAL = "#0072B2", "#D55E00", "#009E73"
CUTOFF = date(2009, 1, 1)
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})


def save(fig, output, name, title):
    fig.suptitle(title, fontsize=15, fontweight="bold")
    for extension in ("png", "svg"):
        fig.savefig(output / f"{name}.{extension}", dpi=260, facecolor="white")
    plt.close(fig)


def forecast_eda(path, output):
    observations = {}
    with ZipFile(path) as archive, archive.open(MEMBER) as member:
        for row in csv.DictReader(io.TextIOWrapper(member, encoding="utf-8-sig")):
            if row["lead"] != "LEAD1":
                continue
            key = row["district"], date.fromisoformat(row["date"])
            if key in observations:
                raise ValueError(f"Repeated observation: {key}")
            observations[key] = float(row["obs_mean"])

    districts = sorted({district for district, _ in observations})
    observed_dates = sorted({month for _, month in observations})
    months = [observed_dates[0]]
    while months[-1] < observed_dates[-1]:
        months.append(shift_month(months[-1], 1))
    panel = np.array([[observations.get((district, month), np.nan) for month in months]
                      for district in districts])
    before = np.array([month < CUTOFF for month in months])
    pre, post = panel[:, before], panel[:, ~before]
    median = np.nanmedian(panel, axis=0)
    low, high = np.nanpercentile(panel, [25, 75], axis=0)

    fig, ax = plt.subplots(figsize=(10, 3.7), layout="constrained")
    ax.fill_between(months, low, high, color=BLUE, alpha=0.2, label="District interquartile range")
    ax.plot(months, median, color=BLUE, linewidth=2, label="District median")
    ax.axvline(CUTOFF, color=ORANGE, linestyle="--", label="January 2009 cutoff")
    ax.axhline(0, color="0.5", linewidth=0.7)
    ax.set(ylabel="Published anomaly", xlabel="Observation month")
    ax.legend(frameon=False, ncols=3, loc="lower left")
    ax.grid(axis="y", alpha=0.2)
    save(fig, output, "pangaea-timeline", "Monthly malaria case anomalies across Uganda districts")

    fig, ax = plt.subplots(figsize=(11, 8), layout="constrained")
    bound = float(np.nanpercentile(np.abs(panel), 98))
    cmap = plt.get_cmap("RdBu_r").with_extremes(bad="#dadada")
    im = ax.imshow(panel, aspect="auto", cmap=cmap, vmin=-bound, vmax=bound,
                   interpolation="nearest")
    year_indices = [i for i, month in enumerate(months) if month.month == 1]
    ax.set_xticks(year_indices, [months[i].year for i in year_indices])
    ax.set_yticks(range(len(districts)), districts, fontsize=6.5)
    ax.axvline(months.index(CUTOFF) - 0.5, color="#252525", linestyle="--", linewidth=1)
    ax.set(xlabel="Observation year (January ticks)", ylabel="District")
    fig.colorbar(im, ax=ax, label="Published anomaly", extend="both", shrink=0.82)
    save(fig, output, "pangaea-heatmap", "District by month anomaly matrix")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
    bins = np.linspace(np.nanmin(panel), np.nanmax(panel), 33)
    for values, color, label in ((pre, BLUE, "Before cutoff"), (post, ORANGE, "From cutoff")):
        axes[0].hist(values[np.isfinite(values)], bins=bins, density=True,
                     histtype="step", linewidth=2, color=color, label=label)
    axes[0].set(title="Distribution by observation date", xlabel="Published anomaly", ylabel="Density")
    axes[0].legend(frameon=False)
    calendar = np.array([month.month for month in months])
    by_month = [panel[:, before & (calendar == m)].ravel() for m in range(1, 13)]
    axes[1].boxplot([v[np.isfinite(v)] for v in by_month], showfliers=False)
    axes[1].set(title="Calendar months before cutoff", xlabel="Month of year",
                ylabel="Published anomaly")
    save(fig, output, "pangaea-distributions", "Distribution and calendar-month variation")

    lags, correlations, pair_counts = range(1, 17), [], []
    for lag in lags:
        current, past = pre[:, lag:].ravel(), pre[:, :-lag].ravel()
        valid = np.isfinite(current) & np.isfinite(past)
        correlations.append(float(np.corrcoef(current[valid], past[valid])[0, 1]))
        pair_counts.append(int(valid.sum()))
    fig, ax = plt.subplots(figsize=(9, 3.6), layout="constrained")
    ax.bar(list(lags), correlations,
           color=[ORANGE if lag in (2, 5, 13, 16) else BLUE for lag in lags])
    ax.axhline(0, color="0.4", linewidth=0.8)
    ax.set(xticks=list(lags), ylim=(-1, 1), xlabel="Lag (months)", ylabel="Pearson correlation")
    ax.grid(axis="y", alpha=0.2)
    ax.set_axisbelow(True)
    save(fig, output, "pangaea-lags", "Same-district lag correlations before January 2009")
    return dict(districts=len(districts), months=len(months), first=str(months[0]),
                last=str(months[-1]), missing=int(np.isnan(panel).sum()),
                observed=int(np.isfinite(panel).sum()),
                pre_n=int(np.isfinite(pre).sum()), post_n=int(np.isfinite(post).sum()),
                pre_median=float(np.nanmedian(pre)), post_median=float(np.nanmedian(post)),
                minimum=float(np.nanmin(panel)), maximum=float(np.nanmax(panel)),
                lag_correlations=correlations, lag_pairs=pair_counts)


def microscopy_eda(path, output):
    brightness = [[], []]
    counts, box_widths, box_heights = [], [], []
    dimensions, sites = Counter(), Counter()
    outside, degenerate = 0, 0
    with ZipFile(path) as archive:
        for row in audit(archive).values():
            member = row["image"]
            xml = ElementTree.fromstring(archive.read(member[:-4] + ".xml"))
            sites[xml.findtext("source/image") or "Unspecified"] += 1
            with Image.open(io.BytesIO(archive.read(member))) as image:
                width, height = image.size
                dimensions[f"{width} x {height}"] += 1
                brightness[row["label"]].append(float(np.asarray(image.convert("L")).mean()))
            boxes = xml.findall("object/bndbox")
            counts.append(len(boxes))
            for box in boxes:
                x0, y0, x1, y1 = (float(box.findtext(key)) for key in ("xmin", "ymin", "xmax", "ymax"))
                outside += int(x0 < 0 or y0 < 0 or x1 > width or y1 > height)
                degenerate += int(x1 <= x0 or y1 <= y0)
                box_widths.append(x1 - x0)
                box_heights.append(y1 - y0)

    labels = ("No labeled parasite", "Parasite annotated")
    positive = [count for count in counts if count > 0]
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4), layout="constrained")
    bars = axes[0].barh(labels, [len(v) for v in brightness], color=(BLUE, ORANGE))
    axes[0].bar_label(bars, padding=4)
    axes[0].set(xlim=(0, max(map(len, brightness)) * 1.15), xlabel="Images", title="Image labels")
    axes[1].hist(positive, bins=np.arange(0.5, max(positive) + 2.5, 2), color=TEAL)
    axes[1].set(xlabel="Annotated boxes per positive image", ylabel="Images", title="Annotation counts")
    save(fig, output, "makerere-labels", "Makerere thick smears | Labels and parasite annotations")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
    box_bins = np.histogram_bin_edges(box_widths + box_heights, bins=25)
    axes[0].hist(box_widths, bins=box_bins, histtype="step", linewidth=2, label="Width", color=BLUE)
    axes[0].hist(box_heights, bins=box_bins, histtype="step", linewidth=2, label="Height", color=ORANGE)
    axes[0].set(title="Bounding-box dimensions", xlabel="Pixels", ylabel="Boxes")
    axes[0].legend(frameon=False)
    for values, label, color in zip(brightness, labels, (BLUE, ORANGE)):
        ordered = np.sort(values)
        axes[1].step(ordered, np.arange(1, len(values) + 1) / len(values),
                     label=label, where="post", color=color, linewidth=2)
    axes[1].set(title="Image brightness by annotation label", xlabel="Mean grayscale (0–255)",
                ylabel="Cumulative fraction")
    axes[1].legend(frameon=False)
    save(fig, output, "makerere-quality", "Makerere thick smears | Image and annotation characteristics")
    return dict(labels={key: len(v) for key, v in zip(labels, brightness)}, sites=sites,
                dimensions=dimensions, boxes=sum(counts), boxes_median=float(np.median(positive)),
                boxes_max=max(positive), outside=outside, degenerate=degenerate,
                brightness_medians=[float(np.median(v)) for v in brightness],
                median_box_width=float(np.median(box_widths)),
                median_box_height=float(np.median(box_heights)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pangaea", type=Path, required=True)
    parser.add_argument("--makerere", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    summary = {}
    for name, archive, analyze in (("pangaea", args.pangaea, forecast_eda),
                                   ("makerere", args.makerere, microscopy_eda)):
        summary[name] = analyze(archive, args.out)
        with archive.open("rb") as stream:
            summary[name]["archive_sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
    (args.out / "summary.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
