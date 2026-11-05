"""Prepare the published PANGAEA Uganda district case anomaly archive."""
import argparse
import csv
import hashlib
import io
import json
import math
from datetime import date
from pathlib import Path
from zipfile import BadZipFile, ZipFile

SOURCE = "https://doi.pangaea.de/10.1594/PANGAEA.897624"
MEMBER = "vectri_monthly_calibrated_timeseries_allyears_UGA_lneir_allLeads_repo.csv"


def shift_month(day, offset):
    year, month = divmod(day.year * 12 + day.month - 1 + offset, 12)
    return date(year, month + 1, 1)


def prepare(archive, output, horizon, cutoff):
    observations = {}
    with ZipFile(archive) as bundle, bundle.open(MEMBER) as member:
        for row in csv.DictReader(io.TextIOWrapper(member, encoding="utf-8-sig")):
            # The same observation is repeated across the four ensemble leads.
            if row["lead"] != "LEAD1":
                continue
            month = date.fromisoformat(row["date"])
            key = (row["district"], month)
            value = float(row["obs_mean"])
            if month.day != 1 or key in observations or not math.isfinite(value):
                raise ValueError(f"Invalid or duplicate district observation: {key}")
            observations[key] = value

    rows = []
    for (district, target_month), target in sorted(observations.items()):
        issue = shift_month(target_month, -horizon)
        prior = (district, shift_month(issue, -1))
        last_year = (district, shift_month(issue, -12))
        if prior not in observations or last_year not in observations:
            continue
        if target_month < cutoff:
            split = "train"
        elif issue >= cutoff:
            split = "test"
        else:
            continue  # Hold out rows whose outcome crosses the split boundary.
        rows.append(dict(district=district, split=split, as_of=issue.isoformat(),
                         outcome_date=target_month.isoformat(), target=target,
                         prior_anomaly=observations[prior],
                         year_ago_anomaly=observations[last_year]))

    counts = {split: sum(row["split"] == split for row in rows) for split in ("train", "test")}
    if not all(counts.values()):
        raise ValueError("Cutoff must leave both training and test rows")
    manifest = dict(source=SOURCE, archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                    archive_member=MEMBER, horizon_months=horizon, cutoff=cutoff.isoformat(),
                    districts=len({row["district"] for row in rows}), rows=counts)
    output.mkdir(parents=True)
    with (output / "forecast.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (output / "source.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(output / "forecast.csv")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--horizon", type=int, choices=(1, 4), default=1)
    parser.add_argument("--cutoff", type=date.fromisoformat, default=date(2009, 1, 1))
    args = parser.parse_args()
    if args.cutoff.day != 1:
        parser.error("Cutoff must be the first day of a month")
    try:
        prepare(args.archive, args.out, args.horizon, args.cutoff)
    except (OSError, ValueError, KeyError, BadZipFile) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
