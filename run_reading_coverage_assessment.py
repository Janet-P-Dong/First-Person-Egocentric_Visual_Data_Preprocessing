"""Summarize what the current curated reading library covers.

The output is a planning aid for the TDSEM dissertation literature strategy.
It uses the Stage 1 audit CSV and produces coverage tables plus a concise
Markdown report. Classifications are first-pass and should be human reviewed.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Iterable, List

import pandas as pd


DEFAULT_LIBRARY = Path("output_literature_audit/developmental_calibration_library.csv")
DEFAULT_OUTPUT_DIR = Path("output_literature_audit/coverage")


CLUSTER_RULES: Dict[str, List[str]] = {
    "A_Relational_Development_Systems": [
        "Development as a Relational Process",
        "Transactional Development",
        "Developmental Systems",
        "Dynamic Systems",
        "Developmental Calibration Framework",
        "Developmental Recalibration",
    ],
    "B_Child_Agency_Joint_Attention": [
        "Child Agency",
        "Joint Attention",
        "Initiating Joint Attention",
        "Responding to Joint Attention",
    ],
    "C_Caregiving_Parent_Child_Interaction": [
        "Caregiving",
        "Parent-Child Interaction",
        "RIFL / Observational Caregiving",
    ],
    "D_Heterogeneity_Pathways_Profiles": [
        "Developmental Heterogeneity",
        "Developmental Profiles",
        "Developmental Landscapes",
        "Developmental Cascades",
    ],
    "E_Neural_Longitudinal_Organization": [
        "Neural Calibration",
        "Interbrain Synchrony",
        "Neural Directionality",
        "Parent-Child Neuroscience",
        "Longitudinal Development",
        "Developmental Recalibration",
    ],
    "M_Methodology_Measurement": [
        "Methodology",
        "Measurement Reference",
        "Methodological Reference",
        "Measurement / Instrument Development",
        "Methodological Paper",
    ],
}

EXPECTED_CHAPTER_SECTIONS = [
    "Development as a Relational Process",
    "Child Agency",
    "Joint Attention",
    "Initiating Joint Attention",
    "Responding to Joint Attention",
    "Caregiving",
    "RIFL / Observational Caregiving",
    "Developmental Heterogeneity",
    "Developmental Landscapes",
    "Neural Calibration",
    "Parent-Child Neuroscience",
    "Neural Directionality",
    "Longitudinal Development",
    "Developmental Recalibration",
    "Developmental Calibration Framework",
]


def clean_series(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def load_library(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Library CSV does not exist: {path}")
    df = pd.read_csv(path)
    required = {
        "Paper_ID",
        "File_Name",
        "Title",
        "Primary_Domain",
        "Secondary_Domain",
        "Supports_Chapter_Section",
        "Paper_Type",
        "Role_in_Dissertation",
        "Priority_Level",
    }
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError("Library CSV is missing required columns: " + ", ".join(missing))
    return df


def summarize_category(df: pd.DataFrame, column: str) -> pd.DataFrame:
    total = len(df)
    summary = (
        clean_series(df[column])
        .replace("", "Unclear")
        .value_counts(dropna=False)
        .rename_axis("category")
        .reset_index(name="n")
    )
    summary["percent"] = (summary["n"] / total * 100).round(2) if total else 0
    return summary


def text_blob(row: pd.Series) -> str:
    fields = [
        "Primary_Domain",
        "Secondary_Domain",
        "Supports_Chapter_Section",
        "Paper_Type",
        "Role_in_Dissertation",
        "Title",
        "File_Name",
    ]
    return " | ".join(str(row.get(field, "")) for field in fields)


def row_matches_cluster(row: pd.Series, keywords: Iterable[str]) -> bool:
    blob = text_blob(row).lower()
    return any(keyword.lower() in blob for keyword in keywords)


def make_cluster_assignments(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in df.iterrows():
        assigned = [
            cluster
            for cluster, keywords in CLUSTER_RULES.items()
            if row_matches_cluster(row, keywords)
        ]
        if not assigned:
            assigned = ["Unmapped"]
        for cluster in assigned:
            rows.append(
                {
                    "Paper_ID": row["Paper_ID"],
                    "File_Name": row["File_Name"],
                    "Title": row["Title"],
                    "Priority_Level": row["Priority_Level"],
                    "Paper_Type": row["Paper_Type"],
                    "Primary_Domain": row["Primary_Domain"],
                    "Supports_Chapter_Section": row["Supports_Chapter_Section"],
                    "Coverage_Cluster": cluster,
                }
            )
    return pd.DataFrame(rows)


def summarize_clusters(cluster_df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        cluster_df.groupby("Coverage_Cluster")
        .agg(
            n_papers=("Paper_ID", "nunique"),
            n_must_read=("Priority_Level", lambda s: int(s.fillna("").str.startswith("A").sum())),
            n_important=("Priority_Level", lambda s: int(s.fillna("").str.startswith("B").sum())),
        )
        .reset_index()
        .sort_values(["n_papers", "n_must_read"], ascending=[False, False])
    )
    summary["coverage_strength"] = summary.apply(assign_strength, axis=1)
    return summary


def assign_strength(row: pd.Series) -> str:
    n = int(row["n_papers"])
    important = int(row["n_must_read"]) + int(row["n_important"])
    if n >= 50 and important >= 15:
        return "Strong"
    if n >= 20 and important >= 5:
        return "Moderate"
    if n >= 8:
        return "Thin but usable"
    return "Gap / very thin"


def make_chapter_gap_table(df: pd.DataFrame) -> pd.DataFrame:
    summaries = summarize_category(df, "Supports_Chapter_Section")
    count_map = dict(zip(summaries["category"], summaries["n"]))
    rows = []
    for section in EXPECTED_CHAPTER_SECTIONS:
        n = int(count_map.get(section, 0))
        rows.append(
            {
                "chapter_section": section,
                "n_seed_readings": n,
                "coverage_status": chapter_status(n),
            }
        )
    return pd.DataFrame(rows)


def chapter_status(n: int) -> str:
    if n >= 20:
        return "Well covered in seed library"
    if n >= 8:
        return "Moderately covered"
    if n >= 3:
        return "Thin coverage"
    return "Major gap"


def make_priority_domain_matrix(df: pd.DataFrame) -> pd.DataFrame:
    matrix = pd.crosstab(
        clean_series(df["Primary_Domain"]).replace("", "Unclear"),
        clean_series(df["Priority_Level"]).replace("", "Unprioritized"),
    )
    matrix["Total"] = matrix.sum(axis=1)
    return matrix.sort_values("Total", ascending=False).reset_index().rename(columns={"Primary_Domain": "Primary_Domain"})


def make_type_by_cluster(cluster_df: pd.DataFrame) -> pd.DataFrame:
    matrix = pd.crosstab(cluster_df["Coverage_Cluster"], cluster_df["Paper_Type"])
    matrix["Total"] = matrix.sum(axis=1)
    return matrix.sort_values("Total", ascending=False).reset_index()


def top_readings_by_cluster(cluster_df: pd.DataFrame, n: int = 8) -> pd.DataFrame:
    priority_rank = {
        "A = Must Read": 1,
        "B = Important": 2,
        "C = Background": 3,
        "D = Peripheral": 4,
    }
    top = cluster_df.copy()
    top["_rank"] = top["Priority_Level"].map(priority_rank).fillna(9)
    top = top.sort_values(["Coverage_Cluster", "_rank", "Title"])
    return top.groupby("Coverage_Cluster").head(n).drop(columns="_rank")


def write_markdown_report(
    df: pd.DataFrame,
    cluster_summary: pd.DataFrame,
    chapter_gaps: pd.DataFrame,
    output_path: Path,
) -> None:
    total = len(df)
    must_read = int(clean_series(df["Priority_Level"]).str.startswith("A").sum())
    important = int(clean_series(df["Priority_Level"]).str.startswith("B").sum())

    strongest = cluster_summary.head(3)
    weakest = chapter_gaps.sort_values(["coverage_status", "n_seed_readings"]).head(8)

    lines = [
        "# Current Reading Coverage Assessment",
        "",
        "This report summarizes the current curated reading library as a seed corpus for TDSEM planning.",
        "Counts are based on automated first-pass classifications and should be treated as review prompts.",
        "",
        "## Corpus Snapshot",
        "",
        f"- Total readings: {total}",
        f"- Must-read readings: {must_read}",
        f"- Important readings: {important}",
        "",
        "## Coverage By TDSEM Cluster",
        "",
        dataframe_to_markdown(cluster_summary),
        "",
        "## Chapter Section Coverage",
        "",
        dataframe_to_markdown(chapter_gaps),
        "",
        "## Strongest Existing Coverage",
        "",
    ]
    for _, row in strongest.iterrows():
        lines.append(
            f"- {row['Coverage_Cluster']}: {int(row['n_papers'])} readings "
            f"({row['coverage_strength']})."
        )

    lines.extend(
        [
            "",
            "## Likely Gaps To Fill Next",
            "",
        ]
    )
    for _, row in weakest.iterrows():
        if row["coverage_status"] in {"Major gap", "Thin coverage"}:
            lines.append(
                f"- {row['chapter_section']}: {int(row['n_seed_readings'])} seed readings "
                f"({row['coverage_status']})."
            )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The current library is especially rich for caregiving, parent-child interaction, neural calibration, and methodological material. It is thinner for explicit child agency, neural directionality, developmental landscapes/profiles, and the broad relational-development theory layer. This means the seed corpus is already useful for Studies 1-2 and neural calibration framing, but Cluster A and Cluster D should be expanded deliberately through Web of Science searches.",
            "",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def dataframe_to_markdown(df: pd.DataFrame) -> str:
    """Render a simple GitHub-style Markdown table without optional deps."""
    if df.empty:
        return "_No rows._"
    columns = list(df.columns)
    rows = []
    rows.append("| " + " | ".join(columns) + " |")
    rows.append("| " + " | ".join(["---"] * len(columns)) + " |")
    for _, row in df.iterrows():
        values = [str(row[column]).replace("|", "/") for column in columns]
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assess coverage of the current reading library.")
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    df = load_library(args.library)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    domain_summary = summarize_category(df, "Primary_Domain")
    chapter_summary = summarize_category(df, "Supports_Chapter_Section")
    paper_type_summary = summarize_category(df, "Paper_Type")
    role_summary = summarize_category(df, "Role_in_Dissertation")
    priority_summary = summarize_category(df, "Priority_Level")

    cluster_assignments = make_cluster_assignments(df)
    cluster_summary = summarize_clusters(cluster_assignments)
    chapter_gaps = make_chapter_gap_table(df)
    priority_domain = make_priority_domain_matrix(df)
    type_by_cluster = make_type_by_cluster(cluster_assignments)
    top_by_cluster = top_readings_by_cluster(cluster_assignments)

    outputs = {
        "coverage_by_primary_domain.csv": domain_summary,
        "coverage_by_chapter_section.csv": chapter_summary,
        "coverage_by_paper_type.csv": paper_type_summary,
        "coverage_by_dissertation_role.csv": role_summary,
        "coverage_by_priority.csv": priority_summary,
        "coverage_cluster_assignments.csv": cluster_assignments,
        "coverage_by_tdsem_cluster.csv": cluster_summary,
        "chapter_section_gap_table.csv": chapter_gaps,
        "priority_by_domain_matrix.csv": priority_domain,
        "paper_type_by_cluster_matrix.csv": type_by_cluster,
        "top_readings_by_cluster.csv": top_by_cluster,
    }
    for filename, table in outputs.items():
        table.to_csv(args.output_dir / filename, index=False)

    write_markdown_report(
        df=df,
        cluster_summary=cluster_summary,
        chapter_gaps=chapter_gaps,
        output_path=args.output_dir / "current_reading_coverage_report.md",
    )

    print("\nCurrent Reading Coverage Assessment")
    print("-----------------------------------")
    print(f"Readings analyzed: {len(df)}")
    print(f"Coverage outputs: {args.output_dir}")
    print("\nTop TDSEM clusters:")
    print(cluster_summary.head(6).to_string(index=False))
    print()


if __name__ == "__main__":
    main()
