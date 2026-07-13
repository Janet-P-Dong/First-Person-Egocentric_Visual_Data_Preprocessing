"""Parse Web of Science savedrecs.txt exports into a clean CSV.

This is stage 01 of the TDSEM developmental calibration literature pipeline.
It keeps raw data unchanged, extracts the metadata needed for evidence
mapping, and creates a combined text field for later semantic clustering.
"""

from __future__ import annotations

import argparse
import csv
import html
import logging
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence


DEFAULT_INPUT = Path("data/raw/savedrecs_clusterA.txt")
DEFAULT_OUTPUT = Path("data/processed/clusterA_clean.csv")

LOGGER = logging.getLogger("parse_wos")

FIELD_MAP = {
    "title": "TI",
    "abstract": "AB",
    "author_keywords": "DE",
    "keywords_plus": "ID",
    "authors": "AU",
    "publication_year": "PY",
    "journal": "SO",
    "doi": "DI",
    "wos_categories": "WC",
    "times_cited": "TC",
}

OPTIONAL_FIELD_MAP = {
    "document_type": "DT",
    "language": "LA",
    "source_id": "UT",
}

TAGGED_LIST_FIELDS = {"AU", "AF", "DE", "ID", "WC", "DT", "EM", "C1"}

OUTPUT_COLUMNS = [
    "paper_id",
    "title",
    "abstract",
    "author_keywords",
    "keywords_plus",
    "authors",
    "publication_year",
    "journal",
    "doi",
    "wos_categories",
    "times_cited",
    "document_type",
    "language",
    "source_id",
    "has_doi",
    "has_abstract",
    "combined_text",
]


def configure_logging(verbose: bool = False) -> None:
    """Configure command-line logging."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )


def raise_csv_field_limit() -> None:
    """Allow very long fields such as cited-reference lists."""
    limit = sys.maxsize
    while True:
        try:
            csv.field_size_limit(limit)
            return
        except OverflowError:
            limit = int(limit / 10)


def clean_text(value: object) -> str:
    """Normalize common Web of Science text artifacts."""
    if value is None:
        return ""
    text = html.unescape(str(value)).replace("\ufeff", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_list_field(value: object) -> str:
    """Normalize semicolon-delimited WoS list fields."""
    text = clean_text(value)
    if not text:
        return ""
    parts = [part.strip() for part in text.split(";") if part.strip()]
    return "; ".join(parts)


def parse_int(value: object) -> int | None:
    """Parse integer fields and return None when values are absent."""
    text = clean_text(value)
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        LOGGER.debug("Could not parse integer from %r", text)
        return None


def detect_wos_format(input_path: Path) -> str:
    """Detect tab-delimited or tagged Web of Science export format."""
    with input_path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        first_line = handle.readline()

    tab_fields = first_line.rstrip("\n\r").split("\t")
    if len(tab_fields) > 5 and {"TI", "AU", "SO"}.intersection(tab_fields):
        return "tab"
    return "tagged"


def read_tab_delimited_wos(input_path: Path) -> List[Dict[str, str]]:
    """Read a WoS tab-delimited export."""
    raise_csv_field_limit()
    with input_path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not reader.fieldnames:
            raise ValueError(f"No header row found in {input_path}")
        rows = [dict(row) for row in reader if any((value or "").strip() for value in row.values())]

    LOGGER.info("Read %s tab-delimited Web of Science records.", len(rows))
    return rows


def read_tagged_wos(input_path: Path) -> List[Dict[str, str]]:
    """Read a classic two-letter tagged WoS export."""
    records: List[Dict[str, str]] = []
    current: Dict[str, List[str]] = {}
    active_tag: str | None = None

    def collapse_record(record: Mapping[str, List[str]]) -> Dict[str, str]:
        collapsed: Dict[str, str] = {}
        for key, values in record.items():
            separator = "; " if key in TAGGED_LIST_FIELDS else " "
            collapsed[key] = separator.join(clean_text(value) for value in values if clean_text(value))
        return collapsed

    with input_path.open("r", encoding="utf-8-sig", errors="replace") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n\r")
            if not line:
                continue
            tag = line[:2]
            payload = line[3:] if len(line) > 3 else ""

            if tag == "ER":
                if current:
                    records.append(collapse_record(current))
                current = {}
                active_tag = None
                continue
            if tag == "EF":
                break
            if tag.strip():
                active_tag = tag
                current.setdefault(active_tag, []).append(payload)
            elif active_tag:
                current[active_tag].append(clean_text(line))

    if current:
        records.append(collapse_record(current))

    LOGGER.info("Read %s tagged Web of Science records.", len(records))
    return records


def read_wos_records(input_path: Path) -> List[Dict[str, str]]:
    """Read WoS records from supported savedrecs.txt formats."""
    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")
    if input_path.is_dir():
        raise IsADirectoryError(f"Input path is a directory, expected a file: {input_path}")

    detected_format = detect_wos_format(input_path)
    LOGGER.info("Detected %s Web of Science export format.", detected_format)
    if detected_format == "tab":
        return read_tab_delimited_wos(input_path)
    return read_tagged_wos(input_path)


def get_record_value(record: Mapping[str, object], tag: str) -> str:
    """Fetch a value by WoS tag with whitespace normalization."""
    return clean_text(record.get(tag, ""))


def build_paper_id(record: Mapping[str, object], row_number: int) -> str:
    """Create a stable paper identifier from WoS ID, DOI, or row number."""
    source_id = get_record_value(record, "UT")
    if source_id:
        return source_id

    doi = get_record_value(record, "DI")
    if doi:
        safe_doi = re.sub(r"[^A-Za-z0-9]+", "_", doi).strip("_").lower()
        return f"doi_{safe_doi}"

    return f"wos_record_{row_number:05d}"


def build_combined_text(cleaned_record: Mapping[str, object]) -> str:
    """Combine text fields for sentence-transformer embeddings."""
    parts = [
        cleaned_record.get("title", ""),
        cleaned_record.get("abstract", ""),
        cleaned_record.get("author_keywords", ""),
        cleaned_record.get("keywords_plus", ""),
    ]
    return clean_text(" ".join(str(part) for part in parts if part))


def clean_wos_record(record: Mapping[str, object], row_number: int) -> Dict[str, object]:
    """Convert one raw WoS record into the project schema."""
    cleaned: Dict[str, object] = {"paper_id": build_paper_id(record, row_number)}

    for output_name, tag in FIELD_MAP.items():
        value = get_record_value(record, tag)
        if output_name in {"author_keywords", "keywords_plus", "authors", "wos_categories"}:
            value = normalize_list_field(value)
        cleaned[output_name] = value

    for output_name, tag in OPTIONAL_FIELD_MAP.items():
        value = get_record_value(record, tag)
        if output_name == "document_type":
            value = normalize_list_field(value)
        cleaned[output_name] = value

    cleaned["publication_year"] = parse_int(cleaned["publication_year"])
    cleaned["times_cited"] = parse_int(cleaned["times_cited"]) or 0
    cleaned["has_doi"] = bool(cleaned["doi"])
    cleaned["has_abstract"] = bool(cleaned["abstract"])
    cleaned["combined_text"] = build_combined_text(cleaned)

    return cleaned


def clean_wos_records(records: Sequence[Mapping[str, object]]) -> List[Dict[str, object]]:
    """Clean all WoS records and preserve input order."""
    cleaned = [clean_wos_record(record, index) for index, record in enumerate(records, start=1)]
    LOGGER.info("Cleaned %s records.", len(cleaned))
    return cleaned


def write_csv(rows: Iterable[Mapping[str, object]], output_path: Path) -> None:
    """Write cleaned records to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    LOGGER.info("Wrote %s records to %s.", len(rows), output_path)


def log_quality_summary(rows: Sequence[Mapping[str, object]]) -> None:
    """Report basic parse quality checks."""
    if not rows:
        LOGGER.warning("No records were parsed.")
        return

    missing_abstracts = sum(1 for row in rows if not row.get("has_abstract"))
    missing_dois = sum(1 for row in rows if not row.get("has_doi"))
    cited_values = [int(row.get("times_cited") or 0) for row in rows]

    LOGGER.info("Missing abstracts: %s/%s", missing_abstracts, len(rows))
    LOGGER.info("Missing DOIs: %s/%s", missing_dois, len(rows))
    LOGGER.info("Maximum Times Cited: %s", max(cited_values) if cited_values else 0)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Parse Web of Science savedrecs.txt exports for the TDSEM pipeline."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Path to a Web of Science savedrecs.txt export. Default: {DEFAULT_INPUT}",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Path for the cleaned CSV. Default: {DEFAULT_OUTPUT}",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print debug logging while parsing.",
    )
    return parser.parse_args()


def main() -> None:
    """Run the parser from the command line."""
    args = parse_args()
    configure_logging(args.verbose)

    try:
        raw_records = read_wos_records(args.input)
        cleaned_records = clean_wos_records(raw_records)
        write_csv(cleaned_records, args.output)
        log_quality_summary(cleaned_records)
    except Exception as exc:
        LOGGER.error("%s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
