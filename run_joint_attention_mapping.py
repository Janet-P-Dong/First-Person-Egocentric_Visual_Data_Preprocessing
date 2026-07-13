"""Pilot Theory-Driven Systematic Evidence Mapping for joint attention records.

Run from the same folder as a Web of Science export named ``savedrecs.txt``:

    python3 run_joint_attention_mapping.py

The script uses transparent keyword dictionaries rather than opaque AI
classification. Outputs are written to ``output_joint_attention_mapping/``.
"""

from __future__ import annotations

import argparse
import csv
import html
import re
import struct
import sys
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None


RANDOM_SEED = 123
DEFAULT_INPUT = Path("savedrecs.txt")
DEFAULT_OUTPUT_DIR = Path("output_joint_attention_mapping")

np.random.seed(RANDOM_SEED)


FIELD_MAP = {
    "title": "TI",
    "authors": "AU",
    "year": "PY",
    "journal": "SO",
    "doi": "DI",
    "abstract": "AB",
    "author_keywords": "DE",
    "keywords_plus": "ID",
    "times_cited": "TC",
}

OUTPUT_COLUMNS = [
    "paper_id",
    "title",
    "authors",
    "year",
    "journal",
    "doi",
    "abstract",
    "author_keywords",
    "keywords_plus",
    "times_cited",
    "title_abstract",
    "full_text_for_coding",
    "outcome_domain",
    "outcome_domain_evidence",
    "outcome_domain_confidence",
    "developmental_role",
    "developmental_role_evidence",
    "developmental_role_confidence",
    "study_design",
    "study_design_evidence",
    "study_design_confidence",
    "developmental_assumption",
    "developmental_assumption_evidence",
    "developmental_assumption_quote",
    "developmental_assumption_confidence",
    "heterogeneity_tested",
    "heterogeneity_tested_evidence",
    "heterogeneity_tested_confidence",
]


# Keyword dictionaries are intentionally simple and inspectable. Each label maps
# to phrases or regular expressions searched in title, abstract, and keywords.
OUTCOME_DOMAIN_KEYWORDS = {
    "language": [
        r"\blanguage\b",
        r"\bvocabulary\b",
        r"\bword learning\b",
        r"\bspeech\b",
        r"\bcommunication\b",
        r"\bcommunicative\b",
        r"\bverbal\b",
        r"\blexical\b",
    ],
    "social cognition": [
        r"\bsocial cognition\b",
        r"\btheory of mind\b",
        r"\bmentaliz",
        r"\bgaze following\b",
        r"\bgaze cue",
        r"\bshared attention\b",
        r"\bsocial attention\b",
    ],
    "social competence": [
        r"\bsocial competence\b",
        r"\bsocial behavior\b",
        r"\bsocial behaviour\b",
        r"\bsocial skills\b",
        r"\bpeer\b",
        r"\bprosocial\b",
        r"\bsocial interaction\b",
    ],
    "autism / ASD": [
        r"\bautism\b",
        r"\bautistic\b",
        r"\bASD\b",
        r"\bspectrum disorder\b",
        r"\bpervasive developmental disorder\b",
    ],
    "executive function": [
        r"\bexecutive function",
        r"\bself-regulation\b",
        r"\binhibitory control\b",
        r"\battention control\b",
        r"\bcognitive control\b",
        r"\bworking memory\b",
    ],
    "learning / task performance": [
        r"\blearning\b",
        r"\btask performance\b",
        r"\bproblem solving\b",
        r"\bperformance\b",
        r"\bachievement\b",
        r"\btraining\b",
    ],
    "parent-child interaction": [
        r"\bparent-child\b",
        r"\bmother-child\b",
        r"\bfather-child\b",
        r"\bcaregiv",
        r"\bparental\b",
        r"\bmaternal\b",
        r"\bdyad",
        r"\binteraction\b",
    ],
    "neural / brain": [
        r"\bneural\b",
        r"\bbrain\b",
        r"\bEEG\b",
        r"\bfMRI\b",
        r"\bMRI\b",
        r"\bERP\b",
        r"\bconnectivity\b",
        r"\bneuroscience\b",
        r"\bcortical\b",
    ],
}

DEVELOPMENTAL_ROLE_KEYWORDS = {
    "predictor": [
        r"\bpredict",
        r"\bforecast",
        r"\bassociated with later\b",
        r"\blater\b",
        r"\bprospective",
    ],
    "outcome": [
        r"\boutcome\b",
        r"\bdependent variable\b",
        r"\bchange in joint attention\b",
        r"\bimprove(?:d|ment)? joint attention\b",
        r"\bjoint attention skills were measured\b",
    ],
    "mediator": [r"\bmediat", r"\bindirect effect\b", r"\bpathway\b"],
    "moderator": [r"\bmoderat", r"\binteraction effect\b", r"\bconditional\b"],
    "marker": [
        r"\bmarker\b",
        r"\bindicator\b",
        r"\bscreening\b",
        r"\bearly sign\b",
        r"\brisk marker\b",
        r"\bbiomarker\b",
    ],
    "mechanism": [
        r"\bmechanism\b",
        r"\bprocess\b",
        r"\bpathway\b",
        r"\bunderlying\b",
        r"\bexplain",
    ],
}

STUDY_DESIGN_KEYWORDS = {
    "review / meta-analysis": [
        r"\breview\b",
        r"\bmeta-analysis\b",
        r"\bsystematic review\b",
        r"\bscoping review\b",
    ],
    "longitudinal": [
        r"\blongitudinal\b",
        r"\bfollow-up\b",
        r"\bprospective\b",
        r"\bpredict(?:ed|s)? later\b",
        r"\bover time\b",
    ],
    "experimental / intervention": [
        r"\bexperiment",
        r"\bintervention\b",
        r"\brandomized\b",
        r"\brandomised\b",
        r"\btraining\b",
        r"\btreatment\b",
        r"\btrial\b",
    ],
    "neuroimaging / neuroscience": [
        r"\bneuroimaging\b",
        r"\bneuroscience\b",
        r"\bEEG\b",
        r"\bfMRI\b",
        r"\bMRI\b",
        r"\bERP\b",
        r"\bbrain\b",
        r"\bneural\b",
        r"\bconnectivity\b",
    ],
    "cross-sectional": [
        r"\bcross-sectional\b",
        r"\bconcurrent\b",
        r"\bat one time\b",
        r"\bsingle time\b",
        r"\bcorrelational\b",
    ],
}

DEVELOPMENTAL_ASSUMPTION_KEYWORDS = {
    "individual differences": [
        r"\bindividual differences\b",
        r"\bvariability\b",
        r"\bvariation\b",
        r"\bdifferences in\b",
    ],
    "social learning": [
        r"\bsocial learning\b",
        r"\bscaffold",
        r"\bmodeling\b",
        r"\bmodelling\b",
        r"\bimitation\b",
        r"\blearning from\b",
        r"\bparental input\b",
    ],
    "transactional": [
        r"\btransactional\b",
        r"\bbidirectional\b",
        r"\breciprocal\b",
        r"\bmutual\b",
        r"\bdyadic\b",
        r"\bparent-child interaction\b",
    ],
    "agency": [
        r"\bagency\b",
        r"\bchild-led\b",
        r"\binitiating joint attention\b",
        r"\binitiat(?:e|es|ed|ing)\b",
        r"\bactive role\b",
    ],
    "maturational": [
        r"\bmatur",
        r"\bage-related\b",
        r"\bdevelopmental trajectory\b",
        r"\bgrowth\b",
    ],
    "neurodevelopmental": [
        r"\bneurodevelopment",
        r"\bneural\b",
        r"\bbrain\b",
        r"\bEEG\b",
        r"\bfMRI\b",
        r"\bconnectivity\b",
        r"\bautism\b",
        r"\bASD\b",
    ],
}

HETEROGENEITY_YES_KEYWORDS = [
    r"\bheterogeneity\b",
    r"\bheterogeneous\b",
    r"\bsubgroup\b",
    r"\bmoderator\b",
    r"\bmoderation\b",
    r"\binteraction effect\b",
    r"\bindividual differences\b",
    r"\blatent class\b",
    r"\bprofile\b",
    r"\bcluster\b",
    r"\btrajectory class\b",
    r"\bvariance\b",
]

HETEROGENEITY_UNCLEAR_KEYWORDS = [
    r"\bvariability\b",
    r"\bvariation\b",
    r"\bdifferences\b",
]


def clean_text(value: object) -> str:
    """Normalize text from Web of Science fields."""
    if value is None or pd.isna(value):
        return ""
    text = html.unescape(str(value)).replace("\ufeff", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_list_field(value: object) -> str:
    """Normalize semicolon-delimited fields such as authors and keywords."""
    text = clean_text(value)
    if not text:
        return ""
    parts = [part.strip() for part in text.split(";") if part.strip()]
    return "; ".join(parts)


def parse_integer(value: object, default: int | None = None) -> int | None:
    """Parse integer-like strings from WoS exports."""
    text = clean_text(value)
    if not text:
        return default
    try:
        return int(float(text))
    except ValueError:
        return default


def raise_csv_field_limit() -> None:
    """Allow very long Web of Science fields such as cited references."""
    limit = sys.maxsize
    while True:
        try:
            csv.field_size_limit(limit)
            return
        except OverflowError:
            limit = int(limit / 10)


def detect_wos_format(input_path: Path) -> str:
    """Detect tabular or classic tagged Web of Science export format."""
    first_line = input_path.open("r", encoding="utf-8-sig", errors="replace").readline()
    fields = first_line.rstrip("\n\r").split("\t")
    if len(fields) > 5 and {"TI", "AU", "SO"}.intersection(fields):
        return "tabular"
    return "tagged"


def read_tabular_wos(input_path: Path) -> list[dict[str, str]]:
    """Read tab-delimited Web of Science records."""
    raise_csv_field_limit()
    with input_path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not reader.fieldnames:
            raise ValueError(f"No header row found in {input_path}")
        return [dict(row) for row in reader if any(clean_text(value) for value in row.values())]


def read_tagged_wos(input_path: Path) -> list[dict[str, str]]:
    """Read classic two-letter tagged Web of Science records."""
    records: list[dict[str, str]] = []
    current: dict[str, list[str]] = {}
    active_tag: str | None = None
    list_tags = {"AU", "AF", "DE", "ID", "WC", "DT"}

    def collapse_record(record: dict[str, list[str]]) -> dict[str, str]:
        collapsed = {}
        for tag, values in record.items():
            separator = "; " if tag in list_tags else " "
            collapsed[tag] = separator.join(clean_text(value) for value in values if clean_text(value))
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
                current[active_tag].append(line.strip())

    if current:
        records.append(collapse_record(current))
    return records


def read_wos_records(input_path: Path) -> list[dict[str, str]]:
    """Read Web of Science records from supported plain-text formats."""
    if not input_path.exists():
        raise FileNotFoundError(
            f"Cannot find {input_path}. Put savedrecs.txt in this folder or pass --input PATH."
        )
    if input_path.is_dir():
        raise IsADirectoryError(f"Expected a file, got a directory: {input_path}")

    if detect_wos_format(input_path) == "tabular":
        return read_tabular_wos(input_path)
    return read_tagged_wos(input_path)


def record_to_row(record: dict[str, str], row_number: int) -> dict[str, object]:
    """Convert a raw Web of Science record into a clean row."""
    row = {}
    for output_name, wos_tag in FIELD_MAP.items():
        value = record.get(wos_tag, "")
        if output_name in {"authors", "author_keywords", "keywords_plus"}:
            row[output_name] = normalize_list_field(value)
        else:
            row[output_name] = clean_text(value)

    row["year"] = parse_integer(row["year"])
    row["times_cited"] = parse_integer(row["times_cited"], default=0)
    row["paper_id"] = clean_text(record.get("UT", "")) or f"paper_{row_number:05d}"
    row["title_abstract"] = clean_text(f"{row['title']} {row['abstract']}")
    row["full_text_for_coding"] = clean_text(
        f"{row['title']} {row['abstract']} {row['author_keywords']} {row['keywords_plus']}"
    )
    return row


def build_clean_dataframe(records: list[dict[str, str]]) -> pd.DataFrame:
    """Create one clean dataframe row per paper."""
    rows = [record_to_row(record, index) for index, record in enumerate(records, start=1)]
    return pd.DataFrame(rows)


def find_keyword_matches(text: str, patterns: list[str]) -> list[str]:
    """Return matched keyword patterns in readable form."""
    matches = []
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            readable = pattern.replace(r"\b", "").replace("(?:", "(").strip("\\")
            matches.append(readable)
    return matches


def find_abstract_quotes(abstract: str, patterns: list[str], max_quotes: int = 2) -> list[str]:
    """Return short abstract snippets around matched coding keywords."""
    abstract = clean_text(abstract)
    if not abstract:
        return []

    quotes = []
    for pattern in patterns:
        match = re.search(pattern, abstract, flags=re.IGNORECASE)
        if not match:
            continue

        start = max(0, match.start() - 90)
        end = min(len(abstract), match.end() + 90)
        snippet = abstract[start:end].strip()
        if start > 0:
            snippet = "... " + snippet
        if end < len(abstract):
            snippet = snippet + " ..."
        quotes.append(snippet)
        if len(quotes) >= max_quotes:
            break
    return quotes


def code_multicategory(
    text: str,
    keyword_dict: dict[str, list[str]],
    unclear_label: str,
) -> tuple[str, str, str]:
    """Assign the highest-scoring label from a transparent keyword dictionary."""
    scores = []
    for label, patterns in keyword_dict.items():
        matches = find_keyword_matches(text, patterns)
        if matches:
            scores.append((label, len(matches), matches))

    if not scores:
        return unclear_label, "", "low"

    # Preserve dictionary order for ties, which makes the coding deterministic.
    best_label, best_score, best_matches = sorted(scores, key=lambda item: item[1], reverse=True)[0]
    confidence = "high" if best_score >= 2 else "medium"
    evidence = "; ".join(best_matches)
    return best_label, evidence, confidence


def code_multicategory_with_quote(
    text: str,
    abstract: str,
    keyword_dict: dict[str, list[str]],
    unclear_label: str,
) -> tuple[str, str, str, str]:
    """Assign a label and add short abstract quote evidence when available."""
    label, evidence, confidence = code_multicategory(text, keyword_dict, unclear_label)
    if label == unclear_label:
        return label, evidence, "", confidence

    quote_patterns = keyword_dict[label]
    quotes = find_abstract_quotes(abstract, quote_patterns)
    return label, evidence, " | ".join(quotes), confidence


def code_heterogeneity(text: str) -> tuple[str, str, str]:
    """Code whether a paper appears to test heterogeneity."""
    yes_matches = find_keyword_matches(text, HETEROGENEITY_YES_KEYWORDS)
    if yes_matches:
        confidence = "high" if len(yes_matches) >= 2 else "medium"
        return "yes", "; ".join(yes_matches), confidence

    unclear_matches = find_keyword_matches(text, HETEROGENEITY_UNCLEAR_KEYWORDS)
    if unclear_matches:
        return "unclear", "; ".join(unclear_matches), "low"

    return "no", "", "medium"


def add_rule_based_codes(df: pd.DataFrame) -> pd.DataFrame:
    """Add all automated pilot coding variables and evidence columns."""
    coded_rows = []
    for _, row in df.iterrows():
        text = clean_text(row["full_text_for_coding"])
        coded = row.to_dict()

        label, evidence, confidence = code_multicategory(
            text, OUTCOME_DOMAIN_KEYWORDS, "other / unclear"
        )
        coded["outcome_domain"] = label
        coded["outcome_domain_evidence"] = evidence
        coded["outcome_domain_confidence"] = confidence

        label, evidence, confidence = code_multicategory(
            text, DEVELOPMENTAL_ROLE_KEYWORDS, "unclear"
        )
        coded["developmental_role"] = label
        coded["developmental_role_evidence"] = evidence
        coded["developmental_role_confidence"] = confidence

        label, evidence, confidence = code_multicategory(text, STUDY_DESIGN_KEYWORDS, "unclear")
        coded["study_design"] = label
        coded["study_design_evidence"] = evidence
        coded["study_design_confidence"] = confidence

        label, evidence, quote, confidence = code_multicategory_with_quote(
            text,
            row["abstract"],
            DEVELOPMENTAL_ASSUMPTION_KEYWORDS,
            "unclear",
        )
        coded["developmental_assumption"] = label
        coded["developmental_assumption_evidence"] = evidence
        coded["developmental_assumption_quote"] = quote
        coded["developmental_assumption_confidence"] = confidence

        label, evidence, confidence = code_heterogeneity(text)
        coded["heterogeneity_tested"] = label
        coded["heterogeneity_tested_evidence"] = evidence
        coded["heterogeneity_tested_confidence"] = confidence

        coded_rows.append(coded)

    return pd.DataFrame(coded_rows)


def make_summary_table(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Summarize a categorical code as n and percent."""
    total = len(df)
    summary = (
        df[column]
        .fillna("unclear")
        .value_counts(dropna=False)
        .rename_axis("category")
        .reset_index(name="n")
    )
    summary["percent"] = np.where(total > 0, summary["n"] / total * 100, 0).round(2)
    return summary


def save_bar_plot(summary: pd.DataFrame, title: str, output_path: Path) -> None:
    """Save a simple horizontal bar plot for one summary table."""
    if plt is None:
        save_basic_png_bar_plot(summary, output_path)
        return

    plot_df = summary.sort_values("n", ascending=True)
    fig_height = max(4, 0.45 * len(plot_df) + 1.5)
    plt.figure(figsize=(9, fig_height))
    plt.barh(plot_df["category"], plot_df["n"], color="#4c78a8")
    plt.xlabel("Number of papers")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    """Create a PNG chunk for the dependency-free fallback plotter."""
    return (
        struct.pack(">I", len(data))
        + chunk_type
        + data
        + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    )


def write_rgb_png(image: np.ndarray, output_path: Path) -> None:
    """Write an RGB numpy array as a PNG without external imaging libraries."""
    height, width, channels = image.shape
    if channels != 3:
        raise ValueError("PNG fallback expects an RGB image.")

    raw_rows = b"".join(b"\x00" + image[row].tobytes() for row in range(height))
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + png_chunk(b"IDAT", zlib.compress(raw_rows, level=9))
        + png_chunk(b"IEND", b"")
    )
    output_path.write_bytes(png_bytes)


BITMAP_FONT = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01111", "10000", "10000", "10111", "10001", "10001", "01111"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "J": ["00111", "00010", "00010", "00010", "10010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "10000", "11110", "00001", "00001", "11110"],
    "6": ["01110", "10000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00001", "01110"],
    " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
    "/": ["00001", "00010", "00010", "00100", "01000", "01000", "10000"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    ":": ["00000", "00100", "00100", "00000", "00100", "00100", "00000"],
    ".": ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
    "%": ["11001", "11010", "00010", "00100", "01000", "01011", "10011"],
    "(": ["00010", "00100", "01000", "01000", "01000", "00100", "00010"],
    ")": ["01000", "00100", "00010", "00010", "00010", "00100", "01000"],
}


def draw_text(
    image: np.ndarray,
    text: str,
    x: int,
    y: int,
    color: np.ndarray,
    scale: int = 2,
) -> None:
    """Draw simple uppercase bitmap text onto an RGB image."""
    cursor_x = x
    for char in text.upper():
        glyph = BITMAP_FONT.get(char, BITMAP_FONT[" "])
        for row_index, row in enumerate(glyph):
            for col_index, pixel in enumerate(row):
                if pixel == "1":
                    y0 = y + row_index * scale
                    x0 = cursor_x + col_index * scale
                    image[y0 : y0 + scale, x0 : x0 + scale] = color
        cursor_x += 6 * scale


def wrap_label(label: str, max_chars: int = 25) -> list[str]:
    """Wrap a short category label for the fallback PNG plot."""
    words = re.sub(r"[^A-Za-z0-9 /().:%-]", " ", str(label)).split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word[:max_chars]
    if current:
        lines.append(current)
    return lines[:2] or [""]


def save_basic_png_bar_plot(summary: pd.DataFrame, output_path: Path) -> None:
    """Save a simple PNG bar plot when matplotlib is unavailable."""
    plot_df = summary.sort_values("n", ascending=False).reset_index(drop=True)
    bar_count = max(1, len(plot_df))
    width = 1180
    height = max(360, 68 * bar_count + 115)
    image = np.full((height, width, 3), 255, dtype=np.uint8)

    left = 370
    right = 860
    top = 78
    bar_height = 28
    gap = 40
    max_n = max(int(plot_df["n"].max()), 1) if not plot_df.empty else 1
    bar_color = np.array([76, 120, 168], dtype=np.uint8)
    axis_color = np.array([70, 70, 70], dtype=np.uint8)
    text_color = np.array([25, 25, 25], dtype=np.uint8)

    title = output_path.stem.replace("plot_", "").replace("_", " ")
    draw_text(image, title, 28, 24, text_color, scale=3)

    image[top : height - 35, left - 2 : left + 1] = axis_color
    image[height - 38 : height - 35, left:right] = axis_color

    for index, row in plot_df.iterrows():
        y = top + index * (bar_height + gap)
        n = int(row["n"])
        percent = float(row["percent"]) if "percent" in row else 0.0
        bar_width = int((right - left) * n / max_n)
        image[y : y + bar_height, left : left + bar_width] = bar_color
        for line_number, line in enumerate(wrap_label(row["category"])):
            draw_text(image, line, 28, y + line_number * 18, text_color, scale=2)
        draw_text(image, f"{n} ({percent:.1f}%)", right + 18, y + 6, text_color, scale=2)

    write_rgb_png(image, output_path)


def make_manual_check_sample(df: pd.DataFrame) -> pd.DataFrame:
    """Create a reproducible 50-paper manual coding sample."""
    code_columns = [
        "outcome_domain",
        "developmental_role",
        "study_design",
        "developmental_assumption",
        "heterogeneity_tested",
    ]
    diagnostic_columns = []
    for column in code_columns:
        diagnostic_columns.extend([column, f"{column}_evidence"])
        if column == "developmental_assumption":
            diagnostic_columns.append("developmental_assumption_quote")
        diagnostic_columns.append(f"{column}_confidence")

    sample_size = min(50, len(df))
    sample = df.sample(n=sample_size, random_state=RANDOM_SEED).copy()
    sample = sample[["title", "abstract", *diagnostic_columns]]

    for column in code_columns:
        sample[f"human_{column}"] = ""
    sample["human_notes"] = ""
    return sample


def write_outputs(df: pd.DataFrame, output_dir: Path) -> dict[str, pd.DataFrame]:
    """Write clean data, summaries, plots, and manual check sample."""
    output_dir.mkdir(parents=True, exist_ok=True)

    clean_path = output_dir / "joint_attention_wos_clean.csv"
    df.loc[:, OUTPUT_COLUMNS].to_csv(clean_path, index=False)

    summary_specs = {
        "summary_outcome_domain.csv": ("outcome_domain", "Outcome domains"),
        "summary_developmental_role.csv": (
            "developmental_role",
            "Developmental role of joint attention",
        ),
        "summary_study_design.csv": ("study_design", "Study designs"),
        "summary_developmental_assumption.csv": (
            "developmental_assumption",
            "Developmental assumptions",
        ),
        "summary_heterogeneity.csv": ("heterogeneity_tested", "Heterogeneity testing"),
    }

    summaries = {}
    for filename, (column, title) in summary_specs.items():
        summary = make_summary_table(df, column)
        summaries[column] = summary
        summary.to_csv(output_dir / filename, index=False)
        plot_name = filename.replace("summary_", "plot_").replace(".csv", ".png")
        save_bar_plot(summary, title, output_dir / plot_name)

    manual_sample = make_manual_check_sample(df)
    manual_sample.to_csv(output_dir / "manual_coding_check_50.csv", index=False)
    return summaries


def print_report(df: pd.DataFrame, summaries: dict[str, pd.DataFrame], output_dir: Path) -> None:
    """Print a short console report."""
    missing_abstracts = int(df["abstract"].fillna("").astype(str).str.strip().eq("").sum())
    missing_doi = int(df["doi"].fillna("").astype(str).str.strip().eq("").sum())
    missing_keywords = int(
        (
            df["author_keywords"].fillna("").astype(str).str.strip().eq("")
            & df["keywords_plus"].fillna("").astype(str).str.strip().eq("")
        ).sum()
    )

    print("\nJoint Attention Pilot Evidence Mapping")
    print("--------------------------------------")
    print(f"Records parsed: {len(df)}")
    print(f"Missing abstracts: {missing_abstracts}")
    print(f"Missing DOI: {missing_doi}")
    print(f"Missing keywords: {missing_keywords}")
    print(f"Outputs saved to: {output_dir}")
    print("\nLargest categories:")

    for column, summary in summaries.items():
        if summary.empty:
            top_category = "none"
            top_n = 0
        else:
            top_category = summary.iloc[0]["category"]
            top_n = int(summary.iloc[0]["n"])
        print(f"- {column}: {top_category} ({top_n})")
    print()


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run a pilot rule-based evidence mapping pipeline for joint attention."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Path to Web of Science savedrecs.txt export. Default: savedrecs.txt",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Folder for all outputs. Default: output_joint_attention_mapping",
    )
    return parser.parse_args()


def main() -> None:
    """Run the full pilot mapping pipeline."""
    args = parse_args()

    try:
        records = read_wos_records(args.input)
        df = build_clean_dataframe(records)
        df = add_rule_based_codes(df)
        summaries = write_outputs(df, args.output_dir)
        print_report(df, summaries, args.output_dir)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
