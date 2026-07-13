"""Create bibliometric summary tables from cleaned Web of Science metadata."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd


DEFAULT_INPUT = Path("data/processed/clusterA_clean.csv")
DEFAULT_OUTPUT_DIR = Path("outputs/tables")

SUMMARY_OUTPUT = "bibliometric_summary.csv"
TOP_CITED_OUTPUT = "top50_cited.csv"
PAPERS_BY_YEAR_OUTPUT = "papers_by_year.csv"
TOP_JOURNALS_OUTPUT = "top_journals.csv"
MISSING_DATA_OUTPUT = "missing_data_report.csv"

REQUIRED_COLUMNS = {
    "paper_id",
    "title",
    "abstract",
    "author_keywords",
    "keywords_plus",
    "publication_year",
    "journal",
    "doi",
    "times_cited",
}

LOGGER = logging.getLogger("bibliometric_summary")


def configure_logging(verbose: bool = False) -> None:
    """Configure command-line logging."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )


def normalize_string_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Replace missing text values with empty strings for reliable counting."""
    text_columns = df.select_dtypes(include=["object"]).columns
    df[text_columns] = df[text_columns].fillna("")
    return df


def load_clean_metadata(input_path: Path) -> pd.DataFrame:
    """Load cleaned metadata and validate required fields."""
    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")
    if input_path.is_dir():
        raise IsADirectoryError(f"Input path is a directory, expected a CSV file: {input_path}")

    df = pd.read_csv(input_path)
    missing_columns = sorted(REQUIRED_COLUMNS.difference(df.columns))
    if missing_columns:
        raise ValueError(
            "Input CSV is missing required columns: " + ", ".join(missing_columns)
        )

    df = normalize_string_columns(df)
    df["publication_year"] = pd.to_numeric(df["publication_year"], errors="coerce").astype("Int64")
    df["times_cited"] = pd.to_numeric(df["times_cited"], errors="coerce").fillna(0).astype(int)
    return df


def is_missing(series: pd.Series) -> pd.Series:
    """Identify empty or whitespace-only values."""
    return series.fillna("").astype(str).str.strip().eq("")


def count_missing_keywords(df: pd.DataFrame) -> int:
    """Count papers missing both author keywords and Keywords Plus."""
    return int(is_missing(df["author_keywords"]).where(is_missing(df["keywords_plus"]), False).sum())


def create_summary_table(df: pd.DataFrame) -> pd.DataFrame:
    """Create one-row bibliometric summary metrics."""
    total_papers = len(df)
    missing_abstracts = int(is_missing(df["abstract"]).sum())
    missing_dois = int(is_missing(df["doi"]).sum())
    missing_keywords = count_missing_keywords(df)

    return pd.DataFrame(
        [
            {
                "total_papers": total_papers,
                "missing_abstracts": missing_abstracts,
                "missing_abstract_rate": missing_abstracts / total_papers if total_papers else 0,
                "missing_doi": missing_dois,
                "missing_doi_rate": missing_dois / total_papers if total_papers else 0,
                "missing_keywords": missing_keywords,
                "missing_keywords_rate": missing_keywords / total_papers if total_papers else 0,
            }
        ]
    )


def create_missing_data_report(df: pd.DataFrame) -> pd.DataFrame:
    """Create field-level missingness counts and rates."""
    fields = ["abstract", "doi", "author_keywords", "keywords_plus", "journal", "publication_year"]
    total_papers = len(df)
    rows = []

    for field in fields:
        if field == "publication_year":
            missing_count = int(df[field].isna().sum())
        else:
            missing_count = int(is_missing(df[field]).sum())
        rows.append(
            {
                "field": field,
                "missing_count": missing_count,
                "missing_rate": missing_count / total_papers if total_papers else 0,
            }
        )

    rows.append(
        {
            "field": "author_keywords_and_keywords_plus",
            "missing_count": count_missing_keywords(df),
            "missing_rate": count_missing_keywords(df) / total_papers if total_papers else 0,
        }
    )
    return pd.DataFrame(rows)


def create_top_cited_table(df: pd.DataFrame, top_n: int = 50) -> pd.DataFrame:
    """Return the most cited papers."""
    columns = [
        "paper_id",
        "title",
        "authors",
        "publication_year",
        "journal",
        "doi",
        "times_cited",
        "abstract",
    ]
    available_columns = [column for column in columns if column in df.columns]
    return (
        df.sort_values(["times_cited", "publication_year", "title"], ascending=[False, True, True])
        .head(top_n)
        .loc[:, available_columns]
    )


def create_papers_by_year_table(df: pd.DataFrame) -> pd.DataFrame:
    """Count papers by publication year."""
    return (
        df.dropna(subset=["publication_year"])
        .groupby("publication_year", dropna=False)
        .size()
        .reset_index(name="paper_count")
        .sort_values("publication_year")
    )


def create_top_journals_table(df: pd.DataFrame) -> pd.DataFrame:
    """Count papers by journal and include citation totals."""
    journals = df.loc[~is_missing(df["journal"])].copy()
    return (
        journals.groupby("journal", dropna=False)
        .agg(
            paper_count=("paper_id", "count"),
            total_times_cited=("times_cited", "sum"),
            mean_times_cited=("times_cited", "mean"),
        )
        .reset_index()
        .sort_values(["paper_count", "total_times_cited", "journal"], ascending=[False, False, True])
    )


def write_outputs(
    summary: pd.DataFrame,
    top_cited: pd.DataFrame,
    papers_by_year: pd.DataFrame,
    top_journals: pd.DataFrame,
    missing_report: pd.DataFrame,
    output_dir: Path,
) -> None:
    """Write all bibliometric tables to CSV."""
    output_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(output_dir / SUMMARY_OUTPUT, index=False)
    top_cited.to_csv(output_dir / TOP_CITED_OUTPUT, index=False)
    papers_by_year.to_csv(output_dir / PAPERS_BY_YEAR_OUTPUT, index=False)
    top_journals.to_csv(output_dir / TOP_JOURNALS_OUTPUT, index=False)
    missing_report.to_csv(output_dir / MISSING_DATA_OUTPUT, index=False)
    LOGGER.info("Wrote bibliometric tables to %s.", output_dir)


def print_console_report(
    summary: pd.DataFrame,
    top_cited: pd.DataFrame,
    papers_by_year: pd.DataFrame,
    top_journals: pd.DataFrame,
) -> None:
    """Print a compact report for command-line runs."""
    metrics = summary.iloc[0].to_dict()
    year_min = papers_by_year["publication_year"].min() if not papers_by_year.empty else "NA"
    year_max = papers_by_year["publication_year"].max() if not papers_by_year.empty else "NA"
    top_paper = top_cited.iloc[0] if not top_cited.empty else None
    top_journal = top_journals.iloc[0] if not top_journals.empty else None

    print("\nTDSEM Bibliometric Summary")
    print("--------------------------")
    print(f"Total papers: {int(metrics['total_papers'])}")
    print(
        "Missing abstracts: "
        f"{int(metrics['missing_abstracts'])} ({metrics['missing_abstract_rate']:.1%})"
    )
    print(f"Missing DOI: {int(metrics['missing_doi'])} ({metrics['missing_doi_rate']:.1%})")
    print(
        "Missing keywords: "
        f"{int(metrics['missing_keywords'])} ({metrics['missing_keywords_rate']:.1%})"
    )
    print(f"Publication year range: {year_min} to {year_max}")

    if top_paper is not None:
        print(
            "Most cited paper: "
            f"{top_paper['title']} ({int(top_paper['times_cited'])} citations)"
        )
    if top_journal is not None:
        print(
            "Top journal: "
            f"{top_journal['journal']} ({int(top_journal['paper_count'])} papers)"
        )
    print()


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Create bibliometric summaries for the TDSEM pipeline."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Path to cleaned metadata CSV. Default: {DEFAULT_INPUT}",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for summary CSV outputs. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print debug logging while summarizing.",
    )
    return parser.parse_args()


def main() -> None:
    """Run the bibliometric summary stage."""
    args = parse_args()
    configure_logging(args.verbose)

    try:
        df = load_clean_metadata(args.input)
        summary = create_summary_table(df)
        top_cited = create_top_cited_table(df)
        papers_by_year = create_papers_by_year_table(df)
        top_journals = create_top_journals_table(df)
        missing_report = create_missing_data_report(df)

        write_outputs(
            summary=summary,
            top_cited=top_cited,
            papers_by_year=papers_by_year,
            top_journals=top_journals,
            missing_report=missing_report,
            output_dir=args.output_dir,
        )
        print_console_report(summary, top_cited, papers_by_year, top_journals)
    except Exception as exc:
        LOGGER.error("%s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
