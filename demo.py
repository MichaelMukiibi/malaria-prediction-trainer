"""Generate small, synthetic fixtures for checking the training commands."""
import csv
from datetime import date, timedelta
from pathlib import Path

import numpy as np
from PIL import Image


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    root = Path("data/demo")
    root.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(42)
    images, events, series = [], [], []
    for i in range(80):
        label = i % 2
        split = "train" if i < 60 else "test"
        client = f"client-{(i // 2) % 3}"
        pixels = np.clip(rng.normal(95 + label * 60, 30, (32, 32, 3)), 0, 255)
        name = f"sample-{i}.png"
        Image.fromarray(pixels.astype("uint8")).save(root / name)
        images.append(dict(image=name, label=label, split=split, group=f"slide-{i}", client=client))
        attack = int(split == "test" and label)
        events.append(dict(scenario=f"scenario-{i}", split=split, label=attack,
                           rate=float(rng.normal(10 + attack * 30)),
                           errors=float(rng.normal(2 + attack * 10))))
        start = date(2020, 1, 1) + timedelta(days=7 * i)
        series.append(dict(split=split, group=f"person-{i}", as_of=start.isoformat(),
                           outcome_date=(start + timedelta(days=3)).isoformat(),
                           history=float(rng.normal(label * 3)), target=label))
    write_csv(root / "images.csv", images)
    write_csv(root / "events.csv", events)
    write_csv(root / "series.csv", series)


if __name__ == "__main__":
    main()

