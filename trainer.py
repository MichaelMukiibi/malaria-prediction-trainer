"""CPU experiments. Each command writes metrics to a fresh run directory."""
import argparse
import csv
import hashlib
import json
import platform
import sys
from pathlib import Path
from time import perf_counter

import numpy as np


def read_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError(f"No records in {path}")
    return rows


def matrix(rows, columns):
    if not columns or len(set(columns)) != len(columns):
        raise ValueError("Supply distinct feature columns")
    values = np.array([[float(row[col]) for col in columns] for row in rows])
    if not np.isfinite(values).all():
        raise ValueError("Features must be finite numbers")
    return values


def image_features(path):
    from PIL import Image

    with Image.open(path) as image:
        image = image.convert("RGB").resize((16, 16), Image.Resampling.BILINEAR)
        return np.asarray(image, dtype=np.float64).reshape(-1) / 255


def partition(rows, group=None):
    if {row["split"] for row in rows} != {"train", "test"}:
        raise ValueError("Provide explicit train and test splits")
    if group:
        groups = {}
        for row in rows:
            key = row[group].strip()
            if not key or groups.setdefault(key, row["split"]) != row["split"]:
                raise ValueError(f"Blank {group} or {group} shared by train and test")
    return ([row for row in rows if row["split"] == "train"],
            [row for row in rows if row["split"] == "test"])


def labels(rows, column="label"):
    values = np.array([int(row[column]) for row in rows])
    if not set(values) <= {0, 1}:
        raise ValueError(f"{column} must contain 0 and 1 only")
    return values


def classification(y, predicted):
    tp = int(np.sum((y == 1) & predicted))
    tn = int(np.sum((y == 0) & ~predicted))
    fp = int(np.sum((y == 0) & predicted))
    fn = int(np.sum((y == 1) & ~predicted))
    return dict(accuracy=(tp + tn) / len(y), tp=tp, tn=tn, fp=fp, fn=fn,
                sensitivity=tp / (tp + fn) if tp + fn else None,
                specificity=tn / (tn + fp) if tn + fp else None)


def logits(x, weights):
    return x @ weights[:-1] + weights[-1]


def binary_cross_entropy(scores, y):
    return float(np.logaddexp(0, np.where(y == 1, -scores, scores)).mean())


def update(weights, x, y, steps, rate, history=None):
    weights = weights.copy()
    for _ in range(steps):
        scores = logits(x, weights)
        if history is not None:
            history.append(binary_cross_entropy(scores, y))
        probability = 1 / (1 + np.exp(-np.clip(scores, -40, 40)))
        error = probability - y
        weights[:-1] -= rate * (x.T @ error / len(y) + 0.01 * weights[:-1])
        weights[-1] -= rate * error.mean()
        if not np.isfinite(weights).all():
            raise ValueError("Training diverged. Check feature ranges and lower --rate.")
    if history is not None:
        history.append(binary_cross_entropy(logits(x, weights), y))
    return weights


def diagnostics(args, rows):
    train, test = partition(rows, "group")
    base = args.input.parent.resolve()
    paths = [(base / row["image"]).resolve() for row in rows]
    if any(not path.is_relative_to(base) for path in paths):
        raise ValueError("Images must be inside the manifest directory")
    if len(set(paths)) != len(paths):
        raise ValueError("Image paths must be unique")
    by_row = {id(row): path for row, path in zip(rows, paths)}
    x = np.array([image_features(by_row[id(row)]) for row in train]) - 0.5
    y, truth = labels(train), labels(test)
    if len(set(y)) < 2 or len(set(truth)) < 2:
        raise ValueError("Both splits must contain both classes")
    clients = np.array([row["client"].strip() for row in train])
    if "" in clients or len(set(clients)) < 2:
        raise ValueError("Use at least two named training clients")
    masks = [clients == client for client in sorted(set(clients))]
    initial = np.zeros(x.shape[1] + 1)
    pooled_loss, local_loss = [], [[] for _ in masks]
    central = update(initial, x, y, args.steps * args.rounds, args.rate, pooled_loss)
    local = [update(initial, x[mask], y[mask], args.steps * args.rounds, args.rate, history)
             for mask, history in zip(masks, local_loss)]
    federated = initial
    federated_loss = [binary_cross_entropy(logits(x, federated), y)]
    counts = [int(mask.sum()) for mask in masks]
    for _ in range(args.rounds):
        federated = np.average(
            [update(federated, x[mask], y[mask], args.steps, args.rate)
             for mask in masks], axis=0, weights=counts)
        federated_loss.append(binary_cross_entropy(logits(x, federated), y))

    elapsed, predictions, failures = [], [], 0
    for row in test:
        start = perf_counter()
        try:
            features = image_features(by_row[id(row)]) - 0.5
            prediction = logits(features, federated) >= 0
        except OSError:
            failures += 1
        else:
            elapsed.append((perf_counter() - start) * 1000)
            predictions.append((features, prediction))

    metrics = {
        "train_images": len(train), "test_images": len(test), "client_sizes": counts,
        "training_loss": {
            "metric": "binary_cross_entropy",
            "pooled": pooled_loss,
            "local_weighted": np.average(local_loss, axis=0, weights=counts).tolist(),
            "federated": federated_loss,
            "federated_steps": [round_id * args.steps for round_id in range(args.rounds + 1)],
        },
        "desktop": {
            "attempted": len(test), "completed": len(predictions), "failed": failures,
            "completion_fraction": len(predictions) / len(test),
            "p50_ms": float(np.percentile(elapsed, 50)) if elapsed else None,
            "p95_ms": float(np.percentile(elapsed, 95)) if elapsed else None,
            "max_ms": max(elapsed, default=None),
        },
    }
    if failures:
        return metrics, federated
    held_out = np.array([item[0] for item in predictions])
    pooled = classification(truth, logits(held_out, central) >= 0)
    fed = classification(truth, np.array([item[1] for item in predictions]))
    local_scores = [classification(truth, logits(held_out, model) >= 0) for model in local]
    mean_local = float(np.mean([item["accuracy"] for item in local_scores]))
    metrics.update(
        pooled=pooled, federated=fed, local_models=local_scores,
        mean_local_accuracy=mean_local,
        federated_gain_vs_mean_local_pp=100 * (fed["accuracy"] - mean_local),
        federated_gain_vs_mean_local_relative_pct=(
            100 * (fed["accuracy"] - mean_local) / mean_local if mean_local else None),
        federated_gain_vs_pooled_pp=100 * (fed["accuracy"] - pooled["accuracy"]),
    )
    return metrics, federated


def security(args, rows):
    from sklearn.ensemble import IsolationForest

    train, test = partition(rows, "scenario")
    if set(labels(train)) != {0} or set(labels(test)) != {0, 1}:
        raise ValueError("Train on benign logs and test on both benign and attack logs")
    columns = args.features
    if {"scenario", "label", "split"} & set(columns):
        raise ValueError("Scenario, label and split are metadata")
    model = IsolationForest(n_estimators=100, contamination=args.contamination,
                            n_jobs=1, random_state=args.seed)
    model.fit(matrix(train, columns))
    truth = labels(test)
    flagged = model.predict(matrix(test, columns)) == -1
    metrics = classification(truth, flagged)
    metrics["false_positive_rate"] = 1 - metrics["specificity"]
    metrics.update(train_events=len(train), test_events=len(test))
    return metrics, None


def tabular(args, rows):
    from datetime import date

    train, test = partition(rows, "group" if args.mode == "followup" else None)
    if max(date.fromisoformat(row["outcome_date"]) for row in train) >= min(
        date.fromisoformat(row["as_of"]) for row in test
    ):
        raise ValueError("Training outcomes must precede the first test prediction")
    if any(date.fromisoformat(row["as_of"]) >= date.fromisoformat(row["outcome_date"])
           for row in rows):
        raise ValueError("Each outcome must follow its prediction date")
    if {"split", "group", "as_of", "outcome_date", "target"} & set(args.features):
        raise ValueError("Target and split metadata cannot be features")
    x, held_out = matrix(train, args.features), matrix(test, args.features)
    persistence = (held_out[:, args.features.index(args.persistence_feature)]
                   if args.persistence_feature else None)
    center = x.mean(axis=0)
    spread = x.std(axis=0)
    spread[spread == 0] = 1
    x, held_out = (x - center) / spread, (held_out - center) / spread
    if not np.isfinite(x).all() or not np.isfinite(held_out).all():
        raise ValueError("Feature standardization overflowed. Check feature ranges.")
    metrics = dict(train_rows=len(train), test_rows=len(test))
    if args.mode == "followup":
        y, truth = labels(train, "target"), labels(test, "target")
        if len(set(y)) < 2 or len(set(truth)) < 2:
            raise ValueError("Both splits must contain both follow-up outcomes")
        history = []
        weights = update(np.zeros(x.shape[1] + 1), x, y, args.steps, args.rate, history)
        metrics.update(model=classification(truth, logits(held_out, weights) >= 0),
                       baseline=classification(truth, np.full(len(truth), y.mean() >= 0.5)),
                       training_loss={"metric": "binary_cross_entropy", "model": history})
    else:
        y, truth = matrix(train, ["target"]).ravel(), matrix(test, ["target"]).ravel()
        weights = np.r_[np.linalg.solve(x.T @ x + np.eye(x.shape[1]), x.T @ (y - y.mean())),
                        y.mean()]
        forecasts = {"ridge": logits(held_out, weights),
                     "train_mean": np.full(len(truth), y.mean())}
        if persistence is not None:
            forecasts["persistence"] = persistence
        for name, predicted in forecasts.items():
            error = truth - predicted
            metrics[name] = dict(mae=float(np.abs(error).mean()),
                                 rmse=float(np.sqrt(np.mean(error ** 2))))
    return metrics, np.vstack([weights, np.r_[center, 0], np.r_[spread, 1]])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["diagnostics", "security", "forecast", "followup"])
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--features", nargs="+", default=[])
    parser.add_argument("--persistence-feature", help="Forecast feature in target units to use as-is")
    parser.add_argument("--rounds", type=int, default=10)
    parser.add_argument("--steps", type=int, default=10)
    parser.add_argument("--rate", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--plot", action="store_true", help="Save PNG and SVG charts with metrics")
    parser.add_argument("--contamination", type=float, default=0.01)
    args = parser.parse_args()
    if args.persistence_feature and (args.mode != "forecast" or
                                     args.persistence_feature not in args.features):
        parser.error("--persistence-feature must name a selected forecast feature")
    if args.steps < 1 or args.rounds < 1 or not np.isfinite(args.rate) or args.rate <= 0:
        parser.error("Steps, rounds and learning rate must be positive")
    if not 0 < args.contamination <= 0.5:
        parser.error("Contamination must be in (0, 0.5]")
    if args.out.exists():
        parser.error("Choose a new run directory")
    if args.plot:
        try:
            from plot_run import render
        except ImportError as exc:
            parser.error(f"Install requirements-plots.txt to use --plot ({exc})")
    try:
        rows = read_rows(args.input)
        run = {"diagnostics": diagnostics, "security": security}.get(args.mode, tabular)
        metrics, weights = run(args, rows)
    except (ValueError, OSError, KeyError, ImportError) as exc:
        parser.error(str(exc))
    args.out.mkdir(parents=True)
    report = dict(mode=args.mode, input_sha256=hashlib.sha256(args.input.read_bytes()).hexdigest(),
                  python=platform.python_version(), numpy=np.__version__, host=platform.platform(),
                  options={k: v for k, v in vars(args).items() if k not in {"input", "out", "mode"}},
                  metrics=metrics)
    if args.mode == "diagnostics":
        from PIL import __version__ as pillow_version
        report["pillow"] = pillow_version
    if args.mode == "security":
        from sklearn import __version__ as sklearn_version
        report["scikit_learn"] = sklearn_version
    if weights is not None:
        np.save(args.out / "weights.npy", weights)
    (args.out / "metrics.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n",
                                           encoding="utf-8")
    print(args.out / "metrics.json")
    if args.plot:
        render(report, args.out)
    return int(metrics.get("desktop", {}).get("failed", 0) > 0)


if __name__ == "__main__":
    sys.exit(main())

