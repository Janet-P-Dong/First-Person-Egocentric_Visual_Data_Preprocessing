"""Create and optionally apply a safe reading-file reorganization plan.

Default behavior is dry-run only: write a CSV manifest of proposed filenames.
Use --apply --mode copy or --apply --mode move after reviewing the manifest.
"""

from __future__ import annotations

import argparse
import re
import shutil
import unicodedata
from pathlib import Path

import pandas as pd


DEFAULT_LIBRARY = Path("output_literature_audit/developmental_calibration_library.csv")
DEFAULT_MANIFEST = Path("output_literature_audit/file_rename_manifest.csv")
DEFAULT_TARGET_ROOT = Path("/Users/janet/Desktop/TDSEM_Organized_Readings")

DOI_SOURCE_MAP = {
    "10.1111/cdev": "ChildDevelopment",
    "10.1111/desc": "DevelopmentalScience",
    "10.1111/infa": "Infancy",
    "10.1037/dev": "DevelopmentalPsychology",
    "10.1037/neu": "Neuropsychology",
    "10.1016/j.neuroimage": "NeuroImage",
    "10.1093/cercor": "CerebralCortex",
    "10.1038/": "Nature",
    "10.3389/fnhum": "FrontiersHumanNeuroscience",
    "10.3389/fpsyg": "FrontiersPsychology",
    "10.1371/journal.pone": "PLOSOne",
    "10.1016/j.chiabu": "ChildAbuseNeglect",
    "10.1016/j.infbeh": "InfantBehaviorDevelopment",
    "10.1080/": "TaylorFrancis",
    "10.1177/": "SAGE",
    "10.1007/": "Springer",
}

GENERIC_TITLE_PATTERNS = [
    r"^original article$",
    r"^child development$",
    r"^available online",
    r"^full terms",
    r"^see discussions",
    r"^review/meta-analysis$",
]

AUTHOR_NOISE_PATTERNS = [
    r"\bjournal\b",
    r"\bvolume\b",
    r"\bdoi\b",
    r"\bpublished\b",
    r"\bcopyright\b",
    r"\bavailable online\b",
    r"^\d",
]


def ascii_slug(value: object, max_len: int = 90) -> str:
    """Return a filesystem-friendly ASCII component."""
    text = "" if pd.isna(value) else str(value)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.replace("&", "and")
    text = re.sub(r"[^A-Za-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:max_len].strip("_") or "Unknown"


def clean_folder_name(value: object) -> str:
    return ascii_slug(value, max_len=70)


def title_is_generic(title: str) -> bool:
    title = title.strip()
    if not title:
        return True
    return any(re.search(pattern, title, flags=re.IGNORECASE) for pattern in GENERIC_TITLE_PATTERNS)


def title_from_filename(file_name: str) -> str:
    stem = Path(file_name).stem
    stem = re.sub(r"^1-s2\.0-[A-Z0-9-]+-main$", "", stem, flags=re.IGNORECASE)
    stem = re.sub(r"^\d{4}[_ -]+", "", stem)
    stem = re.sub(r"[_]+", " ", stem)
    stem = re.sub(r"\b(copy|main|full|pdf)\b", " ", stem, flags=re.IGNORECASE)
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem


def parse_filename_parts(file_name: str) -> dict[str, str]:
    """Infer citation components from common saved-PDF filename patterns."""
    stem = Path(file_name).stem.strip()
    normalized = re.sub(r"[_]+", " ", stem)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    parts: dict[str, str] = {}

    # Pattern: Journal - 2022 - Last - Title
    match = re.match(
        r"^(?P<source>.+?)\s+-\s+(?P<year>19[7-9]\d|20[0-3]\d)\s+-\s+(?P<last>[A-Za-z][A-Za-z]+)\s+-\s+(?P<title>.+)$",
        normalized,
    )
    if match:
        return {key: value.strip() for key, value in match.groupdict().items()}

    # Pattern: Last_2024_Source_Title or Last-2024-Title
    match = re.match(
        r"^(?P<last>[A-Za-z][A-Za-z]+)[\s_-]+(?P<year>19[7-9]\d|20[0-3]\d)[\s_-]+(?P<rest>.+)$",
        normalized,
    )
    if match:
        parts.update(match.groupdict())
        rest = parts.pop("rest")
        source = ""
        title = rest
        source_match = re.match(
            r"^(?P<source>Child Development|Developmental Science|Developmental Psychology|CerebralCortex|Cerebral Cortex|Infancy|NeuroImage|Frontiers|PLOS|SAGE|Springer|Nature|JCPP|PNAS|Child Developemnt Perspectives|Child Development Perspectives)\s+(?P<title>.+)$",
            rest,
            flags=re.IGNORECASE,
        )
        if source_match:
            source = source_match.group("source")
            title = source_match.group("title")
        parts["source"] = source
        parts["title"] = title
        return {key: value.strip() for key, value in parts.items()}

    # Pattern: Last etal 2018 Title, Last_etal_2018_Title, or Last 2018 Title
    match = re.match(
        r"^(?P<last>[A-Za-z][A-Za-z]+)(?:\s+etal|\s+et\s+al\.?)?[\s_-]+(?P<year>19[7-9]\d|20[0-3]\d)[\s_-]+(?P<title>.+)$",
        normalized,
        flags=re.IGNORECASE,
    )
    if match:
        return {key: value.strip() for key, value in match.groupdict().items()}

    # Pattern: ALLCAPSLAST_Source - 2025 - Author_ - Title
    match = re.match(
        r"^(?P<last>[A-Z]{3,})\s+(?P<source>.+?)\s+-\s+(?P<year>19[7-9]\d|20[0-3]\d)\s+-\s+.+?\s+-\s+(?P<title>.+)$",
        normalized,
    )
    if match:
        return {key: value.title().strip() for key, value in match.groupdict().items()}

    return parts


def choose_title(row: pd.Series) -> tuple[str, str]:
    filename_parts = parse_filename_parts(str(row.get("File_Name", "")))
    if filename_parts.get("title"):
        return filename_parts["title"], "filename_pattern"

    title = "" if pd.isna(row.get("Title")) else str(row.get("Title"))
    if title_is_generic(title) or len(title) < 12:
        fallback = title_from_filename(str(row.get("File_Name", "")))
        return fallback, "filename_fallback"
    return title, "audit_title"


def infer_last_name_from_authors(authors: object) -> tuple[str, str]:
    if pd.isna(authors):
        return "", "missing"
    text = str(authors).strip()
    if not text or any(re.search(pattern, text, re.IGNORECASE) for pattern in AUTHOR_NOISE_PATTERNS):
        return "", "noisy"

    first_author = re.split(r";| and | & |\|", text)[0].strip()
    first_author = re.sub(r"\d|✉|[^\w\s,.-]", " ", first_author)
    first_author = re.sub(r"\b[A-Z]\.?\b", " ", first_author)
    parts = [part for part in re.split(r"\s+|,", first_author) if part and len(part) > 1]
    if not parts:
        return "", "missing"
    if "," in first_author:
        return parts[0], "authors"
    return parts[-1], "authors"


def infer_last_name_from_filename(file_name: str) -> tuple[str, str]:
    stem = Path(file_name).stem
    stem = re.sub(r"^\s*\d{4}[_ -]+", "", stem)
    first_token = re.split(r"[_\s-]+", stem.strip())[0]
    first_token = re.sub(r"[^A-Za-z]", "", first_token)
    if len(first_token) >= 3 and not re.match(r"^(the|and|pdf|nihms|s\d|fnhum|pone)$", first_token, re.I):
        return first_token, "filename"
    return "UnknownAuthor", "fallback"


def choose_last_name(row: pd.Series) -> tuple[str, str]:
    filename_parts = parse_filename_parts(str(row.get("File_Name", "")))
    if filename_parts.get("last"):
        return filename_parts["last"], "filename_pattern"

    last_name, source = infer_last_name_from_authors(row.get("Authors"))
    if last_name:
        return last_name, source
    return infer_last_name_from_filename(str(row.get("File_Name", "")))


def choose_year(row: pd.Series) -> tuple[str, str]:
    filename_parts = parse_filename_parts(str(row.get("File_Name", "")))
    if filename_parts.get("year"):
        return filename_parts["year"], "filename_pattern"

    year = row.get("Year", "")
    if not pd.isna(year):
        try:
            return str(int(float(year))), "audit_year"
        except ValueError:
            pass
    match = re.search(r"\b(19[7-9]\d|20[0-3]\d)\b", str(row.get("File_Name", "")))
    if match:
        return match.group(1), "filename_year"
    return "n.d.", "missing"


def choose_source(row: pd.Series) -> tuple[str, str]:
    filename_parts = parse_filename_parts(str(row.get("File_Name", "")))
    if filename_parts.get("source"):
        return filename_parts["source"], "filename_pattern"

    journal = row.get("Journal", "")
    if not pd.isna(journal) and str(journal).strip():
        return str(journal), "journal"

    doi = "" if pd.isna(row.get("DOI")) else str(row.get("DOI")).lower()
    for prefix, source in DOI_SOURCE_MAP.items():
        if doi.startswith(prefix):
            return source, "doi_prefix"

    file_name = str(row.get("File_Name", ""))
    known_sources = [
        "Child Development",
        "Developmental Science",
        "Developmental Psychology",
        "CerebralCortex",
        "NeuroImage",
        "Infancy",
        "Frontiers",
        "PLOS",
        "SAGE",
        "Springer",
    ]
    for source in known_sources:
        if re.search(re.escape(source).replace("\\ ", r"[_\s-]+"), file_name, re.IGNORECASE):
            return source.replace(" ", ""), "filename_source"
    return "UnknownSource", "fallback"


def priority_folder(priority: object) -> str:
    text = "" if pd.isna(priority) else str(priority)
    if text.startswith("A"):
        return "A_Must_Read"
    if text.startswith("B"):
        return "B_Important"
    if text.startswith("C"):
        return "C_Background"
    if text.startswith("D"):
        return "D_Peripheral"
    return "Unprioritized"


def make_unique_paths(paths: list[Path]) -> list[Path]:
    seen: dict[str, int] = {}
    unique = []
    for path in paths:
        key = str(path)
        count = seen.get(key, 0)
        if count == 0:
            unique.append(path)
        else:
            unique.append(path.with_name(f"{path.stem}_{count + 1}{path.suffix}"))
        seen[key] = count + 1
    return unique


def build_manifest(df: pd.DataFrame, target_root: Path) -> pd.DataFrame:
    proposed_paths = []
    rows = []
    for _, row in df.iterrows():
        source_path = Path(str(row["File_Path"]))
        last_name, last_name_source = choose_last_name(row)
        year, year_source = choose_year(row)
        source, source_source = choose_source(row)
        title, title_source = choose_title(row)

        new_name = "_".join(
            [
                ascii_slug(last_name, 35),
                ascii_slug(year, 12),
                ascii_slug(source, 45),
                ascii_slug(title, 95),
            ]
        )
        new_name = re.sub(r"_+", "_", new_name).strip("_") + source_path.suffix.lower()

        target_dir = (
            target_root
            / priority_folder(row.get("Priority_Level"))
            / clean_folder_name(row.get("Primary_Domain", "Unclear"))
        )
        proposed_paths.append(target_dir / new_name)
        rows.append(
            {
                "Paper_ID": row.get("Paper_ID", ""),
                "Current_Path": str(source_path),
                "Current_File_Name": source_path.name,
                "Proposed_File_Name": new_name,
                "Proposed_Directory": str(target_dir),
                "LastName": last_name,
                "Year": year,
                "Source": source,
                "Title_For_File": title,
                "LastName_Source": last_name_source,
                "Year_Source": year_source,
                "Source_Source": source_source,
                "Title_Source": title_source,
                "Primary_Domain": row.get("Primary_Domain", ""),
                "Priority_Level": row.get("Priority_Level", ""),
                "Duplicate_File_Hash": row.get("Duplicate_File_Hash", False),
                "Duplicate_File_Name": row.get("Duplicate_File_Name", False),
                "Needs_Human_Check": any(
                    source in {"authors", "fallback", "missing", "noisy", "filename_fallback"}
                    for source in [last_name_source, year_source, source_source, title_source]
                ),
                "Action_Status": "planned",
            }
        )

    unique_paths = make_unique_paths(proposed_paths)
    for manifest_row, unique_path in zip(rows, unique_paths):
        manifest_row["Proposed_Path"] = str(unique_path)
        if unique_path.name != manifest_row["Proposed_File_Name"]:
            manifest_row["Proposed_File_Name"] = unique_path.name
            manifest_row["Action_Status"] = "planned_collision_renamed"
    return pd.DataFrame(rows)


def apply_manifest(manifest: pd.DataFrame, mode: str) -> pd.DataFrame:
    updated = manifest.copy()
    for index, row in updated.iterrows():
        src = Path(row["Current_Path"])
        dst = Path(row["Proposed_Path"])
        try:
            if not src.exists():
                updated.at[index, "Action_Status"] = "missing_source"
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists() and src.stat().st_size == dst.stat().st_size:
                updated.at[index, "Action_Status"] = "already_exists"
                continue
            if mode == "copy":
                shutil.copy2(src, dst)
            elif mode == "move":
                shutil.move(str(src), str(dst))
            else:
                raise ValueError(f"Unsupported mode: {mode}")
            updated.at[index, "Action_Status"] = f"{mode}d"
        except Exception as exc:
            updated.at[index, "Action_Status"] = f"error: {type(exc).__name__}: {exc}"
    return updated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan or apply reading-file organization.")
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--target-root", type=Path, default=DEFAULT_TARGET_ROOT)
    parser.add_argument("--apply", action="store_true", help="Actually copy or move files.")
    parser.add_argument("--mode", choices=["copy", "move"], default="copy")
    parser.add_argument(
        "--only-safe",
        action="store_true",
        help="Apply only rows where Needs_Human_Check is false.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    df = pd.read_csv(args.library)
    manifest = build_manifest(df, args.target_root)
    if args.apply:
        if args.only_safe:
            safe_mask = ~manifest["Needs_Human_Check"].astype(bool)
            applied = apply_manifest(manifest.loc[safe_mask].copy(), args.mode)
            manifest.loc[safe_mask, :] = applied
            manifest.loc[~safe_mask, "Action_Status"] = "skipped_needs_human_check"
        else:
            manifest = apply_manifest(manifest, args.mode)

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(args.manifest, index=False)

    print("\nReading File Organizer")
    print("----------------------")
    print(f"Records planned: {len(manifest)}")
    print(f"Needs human check: {int(manifest['Needs_Human_Check'].sum())}")
    print(f"Target root: {args.target_root}")
    print(f"Manifest: {args.manifest}")
    if args.apply:
        print(f"Applied mode: {args.mode}")
        if args.only_safe:
            print("Applied subset: only rows where Needs_Human_Check is false")
    else:
        print("Dry run only. Review the manifest before using --apply.")
    print()


if __name__ == "__main__":
    main()
