"""Build a curated Stage 1 literature audit from local reading folders.

This script inventories PDF readings, extracts first-pass bibliographic text,
adds transparent rule-based classifications, and writes review-ready CSV files.
It does not move, rename, or overwrite source PDFs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import logging
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


DEFAULT_INPUT_DIRS = [
    Path("/Users/janet/Desktop/Study 1 Reading"),
    Path("/Users/janet/Desktop/Study2 Readings"),
]
DEFAULT_OUTPUT_DIR = Path("output_literature_audit")
DEFAULT_MAX_PAGES = 5

TEXT_EXTENSIONS = {".pdf"}
DEFAULT_EXTENSIONS = {".pdf", ".docx"}

BAD_TITLE_PATTERNS = [
    r"^©",
    r"\bcopyright\b",
    r"\ball rights reserved\b",
    r"\bpublished by\b",
    r"\bpermissions\b",
    r"^https?://",
    r"\bdoi\.org\b",
    r"^\d+$",
    r"^open access$",
    r"^empirical article$",
    r"^review/meta-analysis$",
    r"^comments and controversies$",
    r"^[A-Za-z ]+,\s*20\d{2};",
    r"^[A-Za-z &]+ \d{1,4} \(\d{4}\)",
]

OUTPUT_COLUMNS = [
    "Paper_ID",
    "Source_Folder",
    "File_Path",
    "File_Name",
    "File_Type",
    "File_Size_MB",
    "File_SHA1_12",
    "Duplicate_File_Hash",
    "Duplicate_File_Name",
    "Extraction_Status",
    "Extraction_Notes",
    "Pages",
    "APA_7_Citation",
    "In_Text_Citation",
    "DOI",
    "Title",
    "Authors",
    "Year",
    "Journal",
    "Abstract",
    "Author_Keywords",
    "Keywords_Plus",
    "Paper_Type",
    "Paper_Type_Evidence",
    "Primary_Domain",
    "Primary_Domain_Evidence",
    "Secondary_Domain",
    "Supports_Chapter_Section",
    "Chapter_Section_Evidence",
    "Role_in_Dissertation",
    "Role_Evidence",
    "Research_Question",
    "Theory_Used",
    "Methodology",
    "Population",
    "Key_Variables",
    "Main_Findings",
    "Main_Argument",
    "Authors_Limitations",
    "Unresolved_Questions",
    "Relevance_to_Dissertation",
    "BERT_Text",
    "Citation_Count",
    "Influential_Paper",
    "Priority_Level",
    "Human_Check_Notes",
]


PAPER_TYPE_KEYWORDS = {
    "Meta-Analysis": [r"\bmeta-analysis\b", r"\bmeta analytic\b"],
    "Systematic Review": [r"\bsystematic review\b", r"\bPRISMA\b"],
    "Narrative Review": [r"\breview\b", r"\boverview\b"],
    "Measurement / Instrument Development": [
        r"\bmeasure\b",
        r"\binstrument\b",
        r"\bscale\b",
        r"\bcoding system\b",
        r"\bpsychometric\b",
        r"\bvalidation\b",
    ],
    "Methodological Paper": [
        r"\bmethod\b",
        r"\btoolbox\b",
        r"\bguide\b",
        r"\bprotocol\b",
        r"\banalysis\b",
    ],
    "Hyperscanning Study": [
        r"\bhyperscanning\b",
        r"\binterbrain\b",
        r"\bbrain-to-brain\b",
        r"\bneural synchrony\b",
    ],
    "Neuroimaging Study": [
        r"\bneuroimaging\b",
        r"\bfNIRS\b",
        r"\bEEG\b",
        r"\bfMRI\b",
        r"\bMRI\b",
        r"\bbrain\b",
        r"\bneural\b",
    ],
    "Longitudinal Empirical Study": [
        r"\blongitudinal\b",
        r"\bfollow-up\b",
        r"\bover time\b",
        r"\btrajectory\b",
    ],
    "Experimental Study": [r"\bexperiment", r"\brandomi[sz]ed\b", r"\btrial\b"],
    "Intervention Study": [r"\bintervention\b", r"\btreatment\b", r"\btraining\b"],
    "Mixed-Methods Study": [r"\bmixed-method", r"\bqualitative and quantitative\b"],
    "Cross-Sectional Empirical Study": [r"\bcross-sectional\b", r"\bconcurrent\b"],
    "Theoretical Paper": [r"\btheory\b", r"\btheoretical\b"],
    "Conceptual Paper": [r"\bconceptual\b", r"\bframework\b", r"\bmodel\b"],
    "Commentary / Perspective": [r"\bcommentary\b", r"\bperspective\b"],
}

DOMAIN_KEYWORDS = {
    "Child Agency": [
        r"\bchild agency\b",
        r"\bactive child\b",
        r"\bchild-led\b",
        r"\bchild initiated\b",
        r"\bchild effects\b",
    ],
    "Joint Attention": [
        r"\bjoint attention\b",
        r"\bshared attention\b",
        r"\bgaze following\b",
        r"\binitiating joint attention\b",
        r"\bresponding to joint attention\b",
    ],
    "Caregiving": [
        r"\bcaregiving\b",
        r"\bcaregiver\b",
        r"\bparental responsiveness\b",
        r"\bmaternal responsiveness\b",
        r"\bsensitivity\b",
        r"\bresponsive parenting\b",
    ],
    "Parent-Child Interaction": [
        r"\bparent-child interaction\b",
        r"\bparent child interaction\b",
        r"\bmother-child interaction\b",
        r"\bfather-child interaction\b",
        r"\bdyad",
    ],
    "Transactional Development": [
        r"\btransactional\b",
        r"\bbidirectional\b",
        r"\breciprocal\b",
        r"\bchild effects\b",
        r"\bparent effects\b",
    ],
    "Developmental Systems": [
        r"\bdevelopmental systems\b",
        r"\brelational developmental systems\b",
        r"\bdevelopmental system\b",
    ],
    "Dynamic Systems": [
        r"\bdynamic systems\b",
        r"\bnonlinear\b",
        r"\bstate space\b",
        r"\bdynamics\b",
    ],
    "Developmental Heterogeneity": [
        r"\bheterogeneity\b",
        r"\bindividual differences\b",
        r"\bvariability\b",
        r"\bmoderator\b",
    ],
    "Developmental Profiles": [
        r"\bprofile\b",
        r"\blatent profile\b",
        r"\blatent class\b",
        r"\btrajectory class\b",
    ],
    "Neural Calibration": [
        r"\bneural\b",
        r"\bbrain\b",
        r"\bneurodevelopment\b",
        r"\bcalibration\b",
    ],
    "Interbrain Synchrony": [
        r"\binterbrain\b",
        r"\bbrain-to-brain\b",
        r"\bhyperscanning\b",
        r"\bneural synchrony\b",
    ],
    "Neural Directionality": [
        r"\bdirectionality\b",
        r"\bgranger\b",
        r"\beffective connectivity\b",
        r"\binfluence\b",
    ],
    "Longitudinal Development": [
        r"\blongitudinal\b",
        r"\bdevelopmental change\b",
        r"\bstability\b",
        r"\bcontinuity\b",
    ],
    "Developmental Cascades": [
        r"\bdevelopmental cascade\b",
        r"\bcascade\b",
        r"\bspillover\b",
    ],
    "Methodology": [
        r"\bmethod\b",
        r"\bmeasurement\b",
        r"\binstrument\b",
        r"\bcoding\b",
        r"\btoolbox\b",
    ],
}

CHAPTER_SECTION_KEYWORDS = {
    "Development as a Relational Process": [
        r"\bdevelopmental systems\b",
        r"\btransactional\b",
        r"\bdynamic systems\b",
        r"\bco-regulation\b",
        r"\bcoregulation\b",
    ],
    "Child Agency": [
        r"\bchild agency\b",
        r"\bactive child\b",
        r"\bchild-led\b",
        r"\bchild effects\b",
    ],
    "Joint Attention": [r"\bjoint attention\b", r"\bshared attention\b"],
    "Initiating Joint Attention": [
        r"\binitiating joint attention\b",
        r"\bIJA\b",
        r"\binitiat(?:e|es|ed|ing)\b",
    ],
    "Responding to Joint Attention": [
        r"\bresponding to joint attention\b",
        r"\bRJA\b",
        r"\bresponse to joint attention\b",
    ],
    "Caregiving": [
        r"\bcaregiving\b",
        r"\bparental responsiveness\b",
        r"\bsensitivity\b",
    ],
    "RIFL / Observational Caregiving": [
        r"\bRIFL\b",
        r"\bobservational\b",
        r"\bcoding system\b",
        r"\bresponsive interactions for learning\b",
    ],
    "Developmental Heterogeneity": [
        r"\bheterogeneity\b",
        r"\bindividual differences\b",
        r"\bvariability\b",
    ],
    "Developmental Landscapes": [
        r"\blandscape\b",
        r"\bstate space\b",
        r"\bnonlinear\b",
    ],
    "Neural Calibration": [
        r"\bneural\b",
        r"\bbrain\b",
        r"\bcalibration\b",
    ],
    "Parent-Child Neuroscience": [
        r"\bhyperscanning\b",
        r"\bparent-child neural\b",
        r"\binterbrain\b",
        r"\bbrain-to-brain\b",
    ],
    "Neural Directionality": [
        r"\bdirectionality\b",
        r"\bgranger\b",
        r"\beffective connectivity\b",
    ],
    "Longitudinal Development": [
        r"\blongitudinal\b",
        r"\bdevelopmental change\b",
        r"\bstability\b",
    ],
    "Developmental Recalibration": [
        r"\brecalibration\b",
        r"\bchange\b",
        r"\breorganization\b",
    ],
    "Developmental Calibration Framework": [
        r"\bcalibration\b",
        r"\bframework\b",
        r"\bdevelopmental pathway\b",
    ],
}

ROLE_KEYWORDS = {
    "Landmark Theory": [
        r"\bSameroff\b",
        r"\bThelen\b",
        r"\bSmith\b",
        r"\bLerner\b",
        r"\bGottlieb\b",
        r"\bBronfenbrenner\b",
        r"\bVygotsky\b",
    ],
    "Review / Overview": [r"\breview\b", r"\boverview\b", r"\bmeta-analysis\b"],
    "Methodological Reference": [r"\bmethod\b", r"\btoolbox\b", r"\bprotocol\b"],
    "Measurement Reference": [
        r"\bmeasure\b",
        r"\binstrument\b",
        r"\bscale\b",
        r"\bcoding system\b",
        r"\bpsychometric\b",
    ],
    "Framework Building": [r"\bframework\b", r"\bmodel\b", r"\btheory\b"],
    "Gap / Unresolved Question": [
        r"\bfuture research\b",
        r"\bunknown\b",
        r"\bunclear\b",
        r"\bremains\b",
        r"\blimited\b",
    ],
    "Foundational Empirical Study": [
        r"\blongitudinal\b",
        r"\bexperiment\b",
        r"\bempirical\b",
    ],
    "Supporting Evidence": [r"\bfindings\b", r"\bresults\b", r"\bassociated\b"],
}

THEORY_KEYWORDS = {
    "Developmental Systems Theory": [r"\bdevelopmental systems\b"],
    "Transactional Theory": [r"\btransactional\b", r"\bbidirectional\b"],
    "Dynamic Systems Theory": [r"\bdynamic systems\b", r"\bnonlinear\b"],
    "Attachment Theory": [r"\battachment\b"],
    "Sociocultural / Scaffolding Theory": [r"\bscaffold", r"\bVygotsky\b"],
    "Social Neuroscience": [r"\bsocial neuroscience\b", r"\bhyperscanning\b"],
    "Effective Connectivity": [r"\beffective connectivity\b", r"\bgranger\b"],
}


def clean_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).replace("\ufeff", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_multiline_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).replace("\ufeff", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def readable_filename_stem(path: Path) -> str:
    stem = path.stem
    stem = re.sub(r"[_]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem)
    return stem.strip()


def sha1_file(path: Path, block_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(block_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_files(input_dirs: Sequence[Path], include_all: bool = False) -> List[Path]:
    files: List[Path] = []
    for directory in input_dirs:
        if not directory.exists():
            print(f"WARNING: input folder does not exist: {directory}", file=sys.stderr)
            continue
        for path in directory.rglob("*"):
            if not path.is_file():
                continue
            if include_all or path.suffix.lower() in DEFAULT_EXTENSIONS:
                files.append(path)
    return sorted(files)


def extract_pdf_text(path: Path, max_pages: int) -> Tuple[str, int, str, str]:
    if PdfReader is None:
        return "", 0, "failed", "pypdf is not installed"

    try:
        reader = PdfReader(str(path))
        page_count = len(reader.pages)
        chunks = []
        for page in reader.pages[:max_pages]:
            chunks.append(page.extract_text() or "")
        text = clean_multiline_text("\n".join(chunks))
        if text:
            return text, page_count, "ok", ""
        return "", page_count, "no_text", "No extractable text found in sampled pages"
    except Exception as exc:
        return "", 0, "failed", f"{type(exc).__name__}: {exc}"


def extract_doi(text: str) -> str:
    text = clean_text(text)
    match = re.search(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", text, flags=re.IGNORECASE)
    if not match:
        return ""
    return match.group(0).rstrip(".,;)")


def extract_year(path: Path, text: str) -> str:
    text = clean_text(text)
    candidates = re.findall(r"\b(19[7-9]\d|20[0-3]\d)\b", f"{path.name} {text[:2000]}")
    return candidates[0] if candidates else ""


def extract_abstract(text: str) -> str:
    text = clean_text(text)
    match = re.search(
        r"\bAbstract\b[:\s]*(.*?)(?:\bKeywords?\b|\bIntroduction\b|\bBackground\b|©|Copyright)",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return clean_text(match.group(1))[:2500]
    return ""


def extract_keywords(text: str) -> str:
    text = clean_text(text)
    match = re.search(
        r"\bKeywords?\b[:\s]*(.*?)(?:\bIntroduction\b|\bAbstract\b|©|Copyright)",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return clean_text(match.group(1))[:600]
    return ""


def title_from_text_or_filename(path: Path, text: str) -> str:
    lines = [clean_text(line) for line in re.split(r"[\n\r]+", text[:2500]) if clean_text(line)]
    filtered = []
    for line in lines:
        if len(line) < 12 or len(line) > 220:
            continue
        if any(re.search(pattern, line, flags=re.IGNORECASE) for pattern in BAD_TITLE_PATTERNS):
            continue
        if re.search(r"^(abstract|keywords|introduction|copyright|doi|http)", line, re.I):
            continue
        if len(re.findall(r"[A-Za-z]", line)) < 8:
            continue
        filtered.append(line)
    if filtered:
        return filtered[0]
    return readable_filename_stem(path)


def infer_authors_from_text(text: str) -> str:
    lines = [clean_text(line) for line in re.split(r"[\n\r]+", text[:3000]) if clean_text(line)]
    for index, line in enumerate(lines[:8]):
        if re.search(r"\b(abstract|doi|journal|volume|issue)\b", line, re.I):
            continue
        if "," in line and not re.search(r"\b(202\d|201\d|199\d)\b", line):
            return line[:500]
        if index > 0 and re.search(r"\b[A-Z]\.\s*[A-Z][a-z]+|[A-Z][a-z]+\s+[A-Z][a-z]+", line):
            return line[:500]
    return ""


def find_matches(text: str, patterns: Iterable[str]) -> List[str]:
    matches = []
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            readable = pattern.replace(r"\b", "").replace("(?:", "(").strip("\\")
            matches.append(readable)
    return matches


def code_best(text: str, codebook: Dict[str, List[str]], default: str = "Unclear") -> Tuple[str, str]:
    scored = []
    for label, patterns in codebook.items():
        matches = find_matches(text, patterns)
        if matches:
            scored.append((label, len(matches), "; ".join(matches)))
    if not scored:
        return default, ""
    label, _, evidence = sorted(scored, key=lambda item: item[1], reverse=True)[0]
    return label, evidence


def code_secondary_domain(text: str, primary: str) -> str:
    scored = []
    for label, patterns in DOMAIN_KEYWORDS.items():
        if label == primary:
            continue
        matches = find_matches(text, patterns)
        if matches:
            scored.append((label, len(matches)))
    if not scored:
        return ""
    return sorted(scored, key=lambda item: item[1], reverse=True)[0][0]


def infer_priority(row: Dict[str, object]) -> str:
    combined = " ".join(
        str(row.get(column, ""))
        for column in ["File_Name", "Title", "Primary_Domain", "Role_in_Dissertation"]
    )
    if re.search(r"\b(landmark|Sameroff|Thelen|Vygotsky|Mundy|Feldman|RIFL|hyperscanning)\b", combined, re.I):
        return "A = Must Read"
    if row.get("Primary_Domain") in {
        "Transactional Development",
        "Developmental Systems",
        "Dynamic Systems",
        "Interbrain Synchrony",
        "Joint Attention",
        "Caregiving",
    }:
        return "B = Important"
    if row.get("Extraction_Status") == "ok":
        return "C = Background"
    return "D = Peripheral"


def build_apa_placeholder(row: Dict[str, object]) -> str:
    authors = clean_text(row.get("Authors", ""))
    year = clean_text(row.get("Year", ""))
    title = clean_text(row.get("Title", ""))
    journal = clean_text(row.get("Journal", ""))
    doi = clean_text(row.get("DOI", ""))
    parts = []
    parts.append(authors if authors else "[Authors need checking]")
    parts.append(f"({year})." if year else "(n.d.).")
    parts.append(f"{title}.")
    if journal:
        parts.append(f"{journal}.")
    if doi:
        parts.append(f"https://doi.org/{doi}")
    return " ".join(parts)


def build_in_text_citation(row: Dict[str, object]) -> str:
    authors = clean_text(row.get("Authors", ""))
    year = clean_text(row.get("Year", "n.d."))
    if not authors:
        return f"({clean_text(row.get('Title', 'Unknown title'))}, {year})"
    first_author = re.split(r";|,| and | & ", authors)[0].strip()
    surname = first_author.split()[-1] if first_author else "Author"
    return f"({surname}, {year})"


def build_row(path: Path, input_dirs: Sequence[Path], max_pages: int) -> Dict[str, object]:
    extension = path.suffix.lower()
    file_hash = sha1_file(path)
    source_folder = next((str(folder) for folder in input_dirs if folder in path.parents), str(path.parent))
    file_type = extension.lstrip(".") or "unknown"
    row: Dict[str, object] = {
        "Paper_ID": f"READ_{file_hash[:12]}",
        "Source_Folder": source_folder,
        "File_Path": str(path),
        "File_Name": path.name,
        "File_Type": file_type,
        "File_Size_MB": round(path.stat().st_size / (1024 * 1024), 3),
        "File_SHA1_12": file_hash[:12],
        "Duplicate_File_Hash": False,
        "Duplicate_File_Name": False,
        "Extraction_Status": "skipped",
        "Extraction_Notes": "",
        "Pages": "",
    }

    text = ""
    if extension == ".pdf":
        text, pages, status, notes = extract_pdf_text(path, max_pages)
        row.update({"Pages": pages, "Extraction_Status": status, "Extraction_Notes": notes})
    else:
        row.update({"Extraction_Status": "unsupported", "Extraction_Notes": f"Unsupported file type: {extension}"})

    abstract = extract_abstract(text)
    keywords = extract_keywords(text)
    title = title_from_text_or_filename(path, text)
    authors = infer_authors_from_text(text)
    year = extract_year(path, text)
    doi = extract_doi(text)
    coding_text = clean_text(f"{path.name} {title} {abstract} {keywords} {text[:8000]}")

    paper_type, paper_type_evidence = code_best(coding_text, PAPER_TYPE_KEYWORDS, "Unclear")
    primary_domain, primary_domain_evidence = code_best(coding_text, DOMAIN_KEYWORDS, "Unclear")
    secondary_domain = code_secondary_domain(coding_text, primary_domain)
    chapter_section, chapter_evidence = code_best(coding_text, CHAPTER_SECTION_KEYWORDS, "Unclear")
    role, role_evidence = code_best(coding_text, ROLE_KEYWORDS, "Supporting Evidence")
    theory_used, _ = code_best(coding_text, THEORY_KEYWORDS, "")

    row.update(
        {
            "DOI": doi,
            "Title": title,
            "Authors": authors,
            "Year": year,
            "Journal": "",
            "Abstract": abstract,
            "Author_Keywords": keywords,
            "Keywords_Plus": "",
            "Paper_Type": paper_type,
            "Paper_Type_Evidence": paper_type_evidence,
            "Primary_Domain": primary_domain,
            "Primary_Domain_Evidence": primary_domain_evidence,
            "Secondary_Domain": secondary_domain,
            "Supports_Chapter_Section": chapter_section,
            "Chapter_Section_Evidence": chapter_evidence,
            "Role_in_Dissertation": role,
            "Role_Evidence": role_evidence,
            "Research_Question": "",
            "Theory_Used": theory_used,
            "Methodology": "",
            "Population": "",
            "Key_Variables": "",
            "Main_Findings": "",
            "Main_Argument": "",
            "Authors_Limitations": "",
            "Unresolved_Questions": "",
            "Relevance_to_Dissertation": "",
            "BERT_Text": clean_text(f"{title} {abstract} {keywords}"),
            "Citation_Count": "",
            "Influential_Paper": "No",
            "Priority_Level": "",
            "Human_Check_Notes": "",
        }
    )
    row["APA_7_Citation"] = build_apa_placeholder(row)
    row["In_Text_Citation"] = build_in_text_citation(row)
    row["Priority_Level"] = infer_priority(row)
    return row


def flag_duplicates(rows: List[Dict[str, object]]) -> None:
    hash_counts: Dict[str, int] = {}
    name_counts: Dict[str, int] = {}
    for row in rows:
        hash_counts[str(row["File_SHA1_12"])] = hash_counts.get(str(row["File_SHA1_12"]), 0) + 1
        normalized_name = str(row["File_Name"]).lower().strip()
        name_counts[normalized_name] = name_counts.get(normalized_name, 0) + 1

    for row in rows:
        row["Duplicate_File_Hash"] = hash_counts[str(row["File_SHA1_12"])] > 1
        row["Duplicate_File_Name"] = name_counts[str(row["File_Name"]).lower().strip()] > 1


def write_outputs(rows: List[Dict[str, object]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    for column in OUTPUT_COLUMNS:
        if column not in df.columns:
            df[column] = ""
    df = df[OUTPUT_COLUMNS]

    library_path = output_dir / "developmental_calibration_library.csv"
    df.to_csv(library_path, index=False, quoting=csv.QUOTE_MINIMAL)

    extraction_report = (
        df.groupby(["File_Type", "Extraction_Status"], dropna=False)
        .size()
        .reset_index(name="n")
        .sort_values(["File_Type", "Extraction_Status"])
    )
    extraction_report.to_csv(output_dir / "extraction_report.csv", index=False)

    duplicate_report = df.loc[
        df["Duplicate_File_Hash"].astype(bool) | df["Duplicate_File_Name"].astype(bool),
        ["Paper_ID", "Source_Folder", "File_Name", "File_SHA1_12", "Duplicate_File_Hash", "Duplicate_File_Name"],
    ]
    duplicate_report.to_csv(output_dir / "duplicate_report.csv", index=False)

    manual_review = df.sort_values(["Priority_Level", "Primary_Domain", "File_Name"]).copy()
    manual_review.to_csv(output_dir / "manual_library_review.csv", index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create Stage 1 developmental calibration reading audit.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        action="append",
        dest="input_dirs",
        help="Reading folder to audit. Repeat for multiple folders.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output folder. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=DEFAULT_MAX_PAGES,
        help="Number of initial PDF pages to sample for text extraction.",
    )
    parser.add_argument(
        "--include-all-files",
        action="store_true",
        help="Inventory all file types instead of only PDFs and DOCX files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    input_dirs = args.input_dirs or DEFAULT_INPUT_DIRS
    files = discover_files(input_dirs, include_all=args.include_all_files)
    rows = [build_row(path, input_dirs, args.max_pages) for path in files]
    flag_duplicates(rows)
    write_outputs(rows, args.output_dir)

    df = pd.DataFrame(rows)
    print("\nStage 1 Literature Audit")
    print("------------------------")
    print(f"Input folders: {len(input_dirs)}")
    print(f"Files inventoried: {len(rows)}")
    print(f"PDF files: {int((df['File_Type'] == 'pdf').sum()) if not df.empty else 0}")
    print(f"PDFs with extracted text: {int((df['Extraction_Status'] == 'ok').sum()) if not df.empty else 0}")
    print(f"Duplicate file hashes: {int(df['Duplicate_File_Hash'].sum()) if not df.empty else 0}")
    print(f"Outputs saved to: {args.output_dir}")
    print()


if __name__ == "__main__":
    main()
