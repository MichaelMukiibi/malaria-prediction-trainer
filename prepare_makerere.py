"""Audit the Makerere phone-camera archive or prepare it with verified split groups."""
import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

IMAGE = re.compile(r"plasmodium-phonecamera/plasmodium-phone-\d{4}\.jpg")
SOURCE = "https://air.ug/downloads/plasmodium-phonecamera.zip"


def audit(bundle):
    names = bundle.namelist()
    images = sorted(name for name in names if IMAGE.fullmatch(name))
    if not images or len(set(names)) != len(names):
        raise ValueError("Unexpected archive layout or duplicate member paths")
    rows, digests = {}, set()
    for image in images:
        annotation = ElementTree.fromstring(bundle.read(image[:-4] + ".xml"))
        labels = {obj.findtext("label") for obj in annotation.findall("object")}
        if annotation.tag != "annotation" or labels - {"plasmodium"}:
            raise ValueError(f"Unexpected annotation for {image}")
        digest = hashlib.sha256(bundle.read(image)).hexdigest()
        if digest in digests:
            raise ValueError(f"Identical image bytes found for {image}")
        digests.add(digest)
        rows[Path(image).name] = dict(image=image, label=int("plasmodium" in labels))
    return rows


def prepare(bundle, rows, groups_path, output):
    with groups_path.open(encoding="utf-8-sig", newline="") as stream:
        groups = {}
        assignments = {}
        for row in csv.DictReader(stream):
            name = row["image"]
            group, split, client = (row[key].strip() for key in ("group", "split", "client"))
            if name in groups or not group or not client or split not in {"train", "test"}:
                raise ValueError(f"Invalid group assignment for {name}")
            if assignments.setdefault(group, (split, client)) != (split, client):
                raise ValueError(f"Group {group} appears in different splits or clients")
            groups[name] = dict(group=group, split=split, client=client)
    if groups.keys() != rows.keys():
        raise ValueError("Group file must contain exactly one row per archive image basename")
    manifest = [row | groups[name] for name, row in rows.items()]
    output.mkdir(parents=True)
    for row in manifest:
        bundle.extract(row["image"], output)
    with (output / "images.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(manifest[0]))
        writer.writeheader()
        writer.writerows(manifest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--groups", type=Path, help="Verified image,group,split,client CSV")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if bool(args.groups) != bool(args.out):
        parser.error("--groups and --out must be supplied together")
    try:
        with args.archive.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        with ZipFile(args.archive) as bundle:
            rows = audit(bundle)
            positive = sum(row["label"] for row in rows.values())
            report = dict(source=SOURCE, archive_sha256=digest, images=len(rows),
                          positive=positive, negative=len(rows) - positive)
            if args.groups:
                prepare(bundle, rows, args.groups, args.out)
                with args.groups.open("rb") as stream:
                    report["groups_sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
                (args.out / "source.json").write_text(json.dumps(report, indent=2) + "\n",
                                                     encoding="utf-8")
        print(json.dumps(report, indent=2))
    except (OSError, ValueError, KeyError, BadZipFile, ElementTree.ParseError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
