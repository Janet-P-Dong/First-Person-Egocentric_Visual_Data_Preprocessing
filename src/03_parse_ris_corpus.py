"""Parse stored RIS exports into a cleaned TDSEM corpus table.

The RIS files in data/raw/ris are treated as immutable Web of Science source
exports. This script reads the manifest, parses all records, attaches cluster
provenance, and writes a clean CSV for audit, screening, and later topic models.
"""

from __future__ import annotations

import argparse
import csv
import html
import logging
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Mapping, Sequence


DEFAULT_MANIFEST = Path("data/raw/ris_manifest.csv")
DEFAULT_OUTPUT = Path("data/processed/tdsem_ris_corpus_clean.csv")
DEFAULT_CLUSTER_SUMMARY = Path("outputs/tables/ris_cluster_summary.csv")
DEFAULT_DUPLICATE_REPORT = Path("outputs/tables/ris_duplicate_doi_report.csv")

LOGGER = logging.getLogger("parse_ris_corpus")

LIST_FIELDS = {"AU", "A1", "KW", "AD", "C3", "FU", "FX", "SN", "WE"}

OUTPUT_COLUMNS = [
    "record_id",
    "cluster",
    "subcluster",
    "source_file",
    "source_part",
    "ris_type",
    "title",
    "abstract",
    "author_keywords",
    "keywords_plus",
    "authors",
    "publication_year",
    "journal",
    "journal_abbrev",
    "doi",
    "wos_accession",
    "language",
    "publisher",
    "volume",
    "issue",
    "start_page",
    "end_page",
    "times_cited_wos",
    "total_times_cited",
    "cited_reference_count",
    "has_doi",
    "has_abstract",
    "duplicate_doi_count",
    "combined_text",
]


def configure_logging(verbose: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )


def raise_csv_field_limit() -> None:
    limit = sys.maxsize
    while True:
        try:
            csv.field_size_limit(limit)
            return
        except OverflowError:
            limit = int(limit / 10)


def clean_text(value: object) -> str:
    if value is None:
        return ""
    text = html.unescape(str(value)).replace("\ufeff", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_int(value: object) -> int | None:
    text = clean_text(value)
    if not text:
        return None
    match = re.search(r"-?\d+", text)
    if not match:
        return None
    return int(match.group(0))


def normalize_list(values: Sequence[object]) -> str:
    parts = [clean_text(value) for value in values]
    return "; ".join(part for part in parts if part)


def read_manifest(manifest_path: Path) -> list[dict[str, str]]:
    if not manifest_path.exists():
        raise FileNotFoundError(f"RIS manifest does not exist: {manifest_path}")
    raise_csv_field_limit()
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = [dict(row) for row in csv.DictReader(handle)]
    if not rows:
        raise ValueError(f"RIS manifest has no rows: {manifest_path}")
    return rows


def parse_ris_file(path: Path) -> list[dict[str, list[str]]]:
    if not path.exists():
        raise FileNotFoundError(f"RIS file does not exist: {path}")

    records: list[dict[str, list[str]]] = []
    current: dict[str, list[str]] = {}
    active_tag: str | None = None

    with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n\r")
            if not line:
                continue

            if len(line) >= 6 and line[2:6] == "  - ":
                tag = line[:2]
                payload = line[6:]
                if tag == "TY":
                    if current:
                        records.append(current)
                    current = {"TY": [payload]}
                    active_tag = tag
                elif tag == "ER":
                    if current:
                        records.append(current)
                    current = {}
                    active_tag = None
                else:
                    current.setdefault(tag, []).append(payload)
                    active_tag = tag
            elif active_tag and current:
                current.setdefault(active_tag, []).append(line)

    if current:
        records.append(current)

    return records


def first(record: Mapping[str, Sequence[str]], tag: str) -> str:
    values = record.get(tag, [])
    return clean_text(values[0]) if values else ""


def values(record: Mapping[str, Sequence[str]], *tags: str) -> list[str]:
    result: list[str] = []
    for tag in tags:
        result.extend(record.get(tag, []))
    return result


def parse_citation_metrics(notes: Sequence[str]) -> dict[str, int | None]:
    text = " ".join(clean_text(note) for note in notes)
    metrics = {
        "times_cited_wos": None,
        "total_times_cited": None,
        "cited_reference_count": None,
    }
    patterns = {
        "times_cited_wos": r"Times Cited in Web of Science Core Collection:\s*(\d+)",
        "total_times_cited": r"Total Times Cited:\s*(\d+)",
        "cited_reference_count": r"Cited Reference Count:\s*(\d+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            metrics[key] = int(match.group(1))
    return metrics


def infer_source_part(filename: str) -> str:
    match = re.search(r"(Part[A-Z]|\bPart\d+|_[A-Z]\b|_RIFL\b)", filename)
    return match.group(1).strip("_") if match else ""


def build_record_id(source_file: str, index: int) -> str:
    stem = Path(source_file).stem
    safe_stem = re.sub(r"[^A-Za-z0-9]+", "_", stem).strip("_")
    return f"{safe_stem}_{index:05d}"


def build_combined_text(row: Mapping[str, object]) -> str:
    return clean_text(
        " ".join(
            str(row.get(field, ""))
            for field in ["title", "abstract", "author_keywords", "keywords_plus"]
            if row.get(field)
        )
    )


def clean_record(
    record: Mapping[str, Sequence[str]],
    manifest_row: Mapping[str, str],
    index: int,
) -> dict[str, object]:
    source_file = manifest_row["file"]
    metrics = parse_citation_metrics(record.get("N1", []))
    doi = first(record, "DO").lower()
    accession = first(record, "AN")
    row: dict[str, object] = {
        "record_id": build_record_id(source_file, index),
        "cluster": manifest_row["cluster"],
        "subcluster": manifest_row["subcluster"],
        "source_file": source_file,
        "source_part": infer_source_part(source_file),
        "ris_type": first(record, "TY"),
        "title": first(record, "TI"),
        "abstract": first(record, "AB"),
        "author_keywords": normalize_list(values(record, "KW")),
        "keywords_plus": "",
        "authors": normalize_list(values(record, "AU", "A1")),
        "publication_year": parse_int(first(record, "PY")),
        "journal": first(record, "T2"),
        "journal_abbrev": first(record, "JI") or first(record, "J9"),
        "doi": doi,
        "wos_accession": accession,
        "language": first(record, "LA"),
        "publisher": first(record, "PU"),
        "volume": first(record, "VL"),
        "issue": first(record, "IS"),
        "start_page": first(record, "SP"),
        "end_page": first(record, "EP"),
        "times_cited_wos": metrics["times_cited_wos"],
        "total_times_cited": metrics["total_times_cited"],
        "cited_reference_count": metrics["cited_reference_count"],
        "has_doi": bool(doi),
        "has_abstract": bool(first(record, "AB")),
        "duplicate_doi_count": 0,
    }
    row["combined_text"] = build_combined_text(row)
    return row


def parse_manifest_records(manifest_rows: Sequence[Mapping[str, str]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for manifest_row in manifest_rows:
        path = Path(manifest_row["stored_path"])
        records = parse_ris_file(path)
        expected = parse_int(manifest_row.get("record_count", ""))
        if expected is not None and expected != len(records):
            LOGGER.warning(
                "Manifest count mismatch for %s: expected %s, parsed %s",
                path,
                expected,
                len(records),
            )
        for index, record in enumerate(records, start=1):
            rows.append(clean_record(record, manifest_row, index))
        LOGGER.info("Parsed %s records from %s.", len(records), path)
    annotate_duplicate_dois(rows)
    return rows


def annotate_duplicate_dois(rows: list[dict[str, object]]) -> None:
    doi_counts = Counter(str(row.get("doi", "")).strip() for row in rows if row.get("doi"))
    for row in rows:
        doi = str(row.get("doi", "")).strip()
        row["duplicate_doi_count"] = doi_counts.get(doi, 0) if doi else 0


def write_csv(rows: Iterable[Mapping[str, object]], output_path: Path, columns: Sequence[str]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    row_list = list(rows)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(row_list)
    LOGGER.info("Wrote %s rows to %s.", len(row_list), output_path)


def create_cluster_summary(rows: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[Mapping[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["cluster"]), str(row["subcluster"]))].append(row)

    summary: list[dict[str, object]] = []
    for (cluster, subcluster), group in sorted(grouped.items()):
        total = len(group)
        missing_abstracts = sum(1 for row in group if not row.get("has_abstract"))
        missing_dois = sum(1 for row in group if not row.get("has_doi"))
        duplicate_doi_records = sum(
            1 for row in group if int(row.get("duplicate_doi_count") or 0) > 1
        )
        summary.append(
            {
                "cluster": cluster,
                "subcluster": subcluster,
                "records": total,
                "missing_abstracts": missing_abstracts,
                "missing_abstract_rate": missing_abstracts / total if total else 0,
                "missing_doi": missing_dois,
                "missing_doi_rate": missing_dois / total if total else 0,
                "duplicate_doi_records": duplicate_doi_records,
            }
        )
    return summary


def create_duplicate_report(rows: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for row in rows:
        doi = str(row.get("doi", "")).strip()
        if doi:
            grouped[doi].append(row)

    report: list[dict[str, object]] = []
    for doi, group in sorted(grouped.items()):
        if len(group) <= 1:
            continue
        clusters = sorted({str(row["cluster"]) for row in group})
        titles = sorted({str(row["title"]) for row in group if row.get("title")})
        files = sorted({str(row["source_file"]) for row in group})
        report.append(
            {
                "doi": doi,
                "record_count": len(group),
                "clusters": "; ".join(clusters),
                "titles": " || ".join(titles[:5]),
                "source_files": "; ".join(files),
            }
        )
    return report


def print_report(rows: Sequence[Mapping[str, object]], cluster_summary: Sequence[Mapping[str, object]]) -> None:
    total = len(rows)
    missing_abstracts = sum(1 for row in rows if not row.get("has_abstract"))
    missing_dois = sum(1 for row in rows if not row.get("has_doi"))
    duplicate_doi_records = sum(
        1 for row in rows if int(row.get("duplicate_doi_count") or 0) > 1
    )
    print("\nRIS Corpus Parse Summary")
    print("------------------------")
    print(f"Total records: {total}")
    print(f"Missing abstracts: {missing_abstracts} ({missing_abstracts / total:.1%})")
    print(f"Missing DOI: {missing_dois} ({missing_dois / total:.1%})")
    print(f"Records sharing a DOI with another record: {duplicate_doi_records}")
    print("\nRecords by cluster/subcluster:")
    for row in cluster_summary:
        print(f"- {row['cluster']} / {row['subcluster']}: {row['records']}")
    print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse TDSEM RIS exports into a clean corpus CSV.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cluster-summary", type=Path, default=DEFAULT_CLUSTER_SUMMARY)
    parser.add_argument("--duplicate-report", type=Path, default=DEFAULT_DUPLICATE_REPORT)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_logging(args.verbose)
    try:
        manifest_rows = read_manifest(args.manifest)
        rows = parse_manifest_records(manifest_rows)
        cluster_summary = create_cluster_summary(rows)
        duplicate_report = create_duplicate_report(rows)
        write_csv(rows, args.output, OUTPUT_COLUMNS)
        write_csv(
            cluster_summary,
            args.cluster_summary,
            [
                "cluster",
                "subcluster",
                "records",
                "missing_abstracts",
                "missing_abstract_rate",
                "missing_doi",
                "missing_doi_rate",
                "duplicate_doi_records",
            ],
        )
        write_csv(
            duplicate_report,
            args.duplicate_report,
            ["doi", "record_count", "clusters", "titles", "source_files"],
        )
        print_report(rows, cluster_summary)
    except Exception as exc:
        LOGGER.error("%s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
