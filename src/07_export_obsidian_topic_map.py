"""Export the TDSEM topic classification map as Obsidian-ready Markdown notes."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

import pandas as pd


DEFAULT_CLASSIFICATION = Path("outputs/topic_classification_k30/topic_classification.csv")
DEFAULT_FAMILY_SUMMARY = Path("outputs/topic_classification_k30/topic_family_summary.csv")
DEFAULT_REPRESENTATIVES = Path("outputs/topics_k30/representative_papers.csv")
DEFAULT_OUTPUT_DIR = Path("obsidian/TDSEM_Topic_Map")
DEFAULT_ASSET_SOURCES = [
    Path("outputs/topic_classification_k30/figures/topic_family_paper_counts.png"),
    Path("outputs/topic_classification_k30/figures/topic_priority_tiers.png"),
]


def slugify(value: object, max_length: int = 72) -> str:
    text = "" if value is None or pd.isna(value) else str(value)
    text = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
    text = re.sub(r"_+", "_", text)
    return text[:max_length].strip("_") or "untitled"


def clean(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def md_escape(value: object) -> str:
    return clean(value).replace("|", "\\|")


def wikilink(filename: str, label: str | None = None) -> str:
    if label:
        return f"[[{filename}|{label}]]"
    return f"[[{filename}]]"


def topic_filename(row: pd.Series) -> str:
    topic_id = int(float(row["topic_id"]))
    name = slugify(row["bertopic_name"])
    return f"Topic_{topic_id:02d}_{name}"


def family_filename(family: str) -> str:
    return f"Family_{slugify(family)}"


def priority_tag(priority: str) -> str:
    if priority.startswith("A"):
        return "priority/a_core"
    if priority.startswith("B"):
        return "priority/b_supporting"
    if priority.startswith("C"):
        return "priority/c_background"
    if priority.startswith("D"):
        return "priority/d_boundary"
    return "priority/unclassified"


def load_inputs(classification_path: Path, family_summary_path: Path, representatives_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    missing = [
        str(path)
        for path in [classification_path, family_summary_path, representatives_path]
        if not path.exists()
    ]
    if missing:
        raise FileNotFoundError("Missing input files: " + ", ".join(missing))
    topics = pd.read_csv(classification_path)
    families = pd.read_csv(family_summary_path)
    representatives = pd.read_csv(representatives_path)
    return topics, families, representatives


def write_note(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def yaml_list(items: list[str]) -> str:
    return "\n".join(f"  - {item}" for item in items)


def write_index(topics: pd.DataFrame, families: pd.DataFrame, output_dir: Path) -> None:
    topic_rows = []
    for _, row in topics.sort_values(["dissertation_priority", "topic_id"]).iterrows():
        topic_rows.append(
            "| "
            + " | ".join(
                [
                    wikilink(f"Topics/{topic_filename(row)}", f"Topic {int(float(row['topic_id']))}"),
                    md_escape(row["bertopic_name"]),
                    md_escape(row["topic_family"]),
                    md_escape(row["topic_role"]),
                    md_escape(row["dissertation_priority"]),
                    str(int(row["topic_size"])),
                    f"{float(row['npmi_coherence']):.3f}" if pd.notna(row["npmi_coherence"]) else "",
                ]
            )
            + " |"
        )

    family_rows = []
    for _, row in families.sort_values(["topic_family", "dissertation_priority"]).iterrows():
        family_rows.append(
            "| "
            + " | ".join(
                [
                    wikilink(
                        f"Families/{family_filename(row['topic_family'])}",
                        md_escape(row["topic_family"]),
                    ),
                    md_escape(row["dissertation_priority"]),
                    str(int(row["n_topics"])),
                    str(int(row["total_papers"])),
                    f"{float(row['mean_coherence']):.3f}" if pd.notna(row["mean_coherence"]) else "",
                    f"{float(row['mean_relevance']):.2f}" if pd.notna(row["mean_relevance"]) else "",
                ]
            )
            + " |"
        )

    priority_counts = topics.groupby("dissertation_priority")["topic_size"].sum().sort_index()
    priority_lines = "\n".join(f"- {priority}: {int(count):,} papers" for priority, count in priority_counts.items())

    content = f"""---
title: TDSEM Topic Map Index
project: TDSEM Developmental Calibration Research
type: evidence-map-index
tags:
  - tdsem
  - evidence-map
  - bertopic
  - dissertation
---

# TDSEM Topic Map Index

This Obsidian map summarizes the `k=30` BERTopic solution and its higher-order dissertation-facing topic classification.

## Construct Anchor

The dissertation examines how child agency and caregiving jointly organize developmental functioning across behavioral, neural, and longitudinal timescales. In this map, initiating joint attention and responding to joint attention are treated as child agency/responsiveness markers, while parenting scaffolding and emotional support are interpreted through RIFL and related parent-child interaction constructs.

## Priority Tiers

{priority_lines}

## Visual Summary

![[Assets/topic_family_paper_counts.png]]

![[Assets/topic_priority_tiers.png]]

## Family Summary

| Topic family | Priority | Topics | Papers | Mean coherence | Mean relevance |
|---|---:|---:|---:|---:|---:|
{chr(10).join(family_rows)}

## Topic Register

| Topic | BERTopic name | Family | Role | Priority | Papers | Coherence |
|---|---|---|---|---|---:|---:|
{chr(10).join(topic_rows)}

## Source Tables

- [topic_classification.csv](../../outputs/topic_classification_k30/topic_classification.csv)
- [topic_label_review_template.csv](../../outputs/topic_classification_k30/topic_label_review_template.csv)
- [topic_family_summary.csv](../../outputs/topic_classification_k30/topic_family_summary.csv)
- [topic_priority_queue.csv](../../outputs/topic_classification_k30/topic_priority_queue.csv)
- [paper_evidence_map.csv](../../outputs/evidence_maps_k30/paper_evidence_map.csv)
- [topic_coherence.csv](../../outputs/topics_k30/topic_coherence.csv)
- [topic_similarity_matrix.csv](../../outputs/topics_k30/topic_similarity_matrix.csv)
"""
    write_note(output_dir / "00_TDSEM_Topic_Map_Index.md", content)


def write_family_notes(topics: pd.DataFrame, families: pd.DataFrame, output_dir: Path) -> None:
    for family, family_topics in topics.groupby("topic_family"):
        summary = families[families["topic_family"] == family].copy()
        topic_lines = []
        for _, row in family_topics.sort_values(["dissertation_priority", "topic_id"]).iterrows():
            topic_lines.append(
                f"- {wikilink(f'Topics/{topic_filename(row)}', f'Topic {int(float(row["topic_id"]))}')} "
                f"- {clean(row['bertopic_name'])}; {clean(row['dissertation_priority'])}; "
                f"{int(row['topic_size'])} papers"
            )

        summary_rows = []
        for _, row in summary.sort_values("dissertation_priority").iterrows():
            summary_rows.append(
                "| "
                + " | ".join(
                    [
                        md_escape(row["dissertation_priority"]),
                        str(int(row["n_topics"])),
                        str(int(row["total_papers"])),
                        f"{float(row['mean_coherence']):.3f}" if pd.notna(row["mean_coherence"]) else "",
                        f"{float(row['mean_relevance']):.2f}" if pd.notna(row["mean_relevance"]) else "",
                    ]
                )
                + " |"
            )

        tags = ["tdsem", "topic-family", slugify(family).lower()]
        content = f"""---
title: {family}
type: topic-family
topic_family: "{family}"
tags:
{yaml_list(tags)}
---

# {family}

## Summary

| Priority | Topics | Papers | Mean coherence | Mean relevance |
|---|---:|---:|---:|---:|
{chr(10).join(summary_rows)}

## Topics

{chr(10).join(topic_lines)}

## Notes

- Human interpretation:
- Relevance to dissertation:
- Potential exclusions or boundary cases:
"""
        write_note(output_dir / "Families" / f"{family_filename(family)}.md", content)


def write_topic_notes(topics: pd.DataFrame, representatives: pd.DataFrame, output_dir: Path) -> None:
    for _, row in topics.sort_values("topic_id").iterrows():
        topic_id = int(float(row["topic_id"]))
        reps = representatives[representatives["topic_id"].astype(int) == topic_id].copy()
        reps = reps.sort_values("total_times_cited", ascending=False).head(8)
        rep_lines = []
        for _, paper in reps.iterrows():
            year = clean(paper.get("publication_year"))
            journal = clean(paper.get("journal"))
            citations = clean(paper.get("total_times_cited"))
            doi = clean(paper.get("doi"))
            doi_text = f" DOI: {doi}." if doi else ""
            rep_lines.append(
                f"- {clean(paper.get('title'))} ({year}). {journal}. Citations: {citations}.{doi_text}"
            )

        tags = [
            "tdsem",
            "bertopic",
            f"topic/{topic_id:02d}",
            slugify(row["topic_family"]).lower(),
            priority_tag(clean(row["dissertation_priority"])),
        ]
        coherence_text = (
            f"{float(row['npmi_coherence']):.3f}" if pd.notna(row["npmi_coherence"]) else ""
        )
        median_citations_text = (
            f"{float(row['median_citations']):.1f}" if pd.notna(row["median_citations"]) else ""
        )
        content = f"""---
title: Topic {topic_id}: {clean(row["bertopic_name"])}
type: bertopic-topic
topic_id: {topic_id}
topic_family: "{clean(row["topic_family"])}"
topic_role: "{clean(row["topic_role"])}"
dissertation_priority: "{clean(row["dissertation_priority"])}"
topic_size: {int(row["topic_size"])}
npmi_coherence: {float(row["npmi_coherence"]) if pd.notna(row["npmi_coherence"]) else ""}
tags:
{yaml_list(tags)}
---

# Topic {topic_id}: {clean(row["bertopic_name"])}

Family: {wikilink(f"Families/{family_filename(row['topic_family'])}", clean(row["topic_family"]))}

Priority: {clean(row["dissertation_priority"])}

Role: {clean(row["topic_role"])}

## Topic Keywords

{clean(row["top_keywords"])}

## Evidence-Map Profile

| Field | Dominant values |
|---|---|
| Cluster | {md_escape(row["dominant_cluster"])} |
| Theory | {md_escape(row["dominant_theory"])} |
| Method | {md_escape(row["dominant_method"])} |
| Unresolved gap | {md_escape(row["dominant_unresolved_gap"])} |
| Agency marker | {md_escape(row["dominant_agency_marker"])} |
| Caregiving construct | {md_escape(row["dominant_caregiving_construct"])} |

## Metrics

- Topic size: {int(row["topic_size"])}
- Mean dissertation relevance score: {float(row["mean_dissertation_relevance_score"]):.2f}
- Max dissertation relevance score: {int(row["max_dissertation_relevance_score"])}
- NPMI coherence: {coherence_text}
- Median citations: {median_citations_text}

## Representative Papers

{chr(10).join(rep_lines) if rep_lines else "- No representative papers found."}

## Human Coding Notes

- Better topic label:
- Dissertation relevance:
- Keep / background / exclude:
- Notes:
"""
        write_note(output_dir / "Topics" / f"{topic_filename(row)}.md", content)


def write_readme(output_dir: Path) -> None:
    content = """# Obsidian TDSEM Topic Map

Open `00_TDSEM_Topic_Map_Index.md` as the entry point.

This folder is generated from:

- `outputs/topic_classification_k30/topic_classification.csv`
- `outputs/topic_classification_k30/topic_family_summary.csv`
- `outputs/topics_k30/representative_papers.csv`

The notes are intentionally reviewable. Human labels, exclusions, and dissertation relevance judgments should be added in the topic notes or in `topic_label_review_template.csv`.
"""
    write_note(output_dir / "README.md", content)


def copy_assets(output_dir: Path) -> None:
    asset_dir = output_dir / "Assets"
    asset_dir.mkdir(parents=True, exist_ok=True)
    for source in DEFAULT_ASSET_SOURCES:
        if source.exists():
            shutil.copy2(source, asset_dir / source.name)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export TDSEM topic map to Obsidian Markdown.")
    parser.add_argument("--classification", type=Path, default=DEFAULT_CLASSIFICATION)
    parser.add_argument("--family-summary", type=Path, default=DEFAULT_FAMILY_SUMMARY)
    parser.add_argument("--representatives", type=Path, default=DEFAULT_REPRESENTATIVES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    topics, families, representatives = load_inputs(
        args.classification, args.family_summary, args.representatives
    )
    write_index(topics, families, args.output_dir)
    write_family_notes(topics, families, args.output_dir)
    write_topic_notes(topics, representatives, args.output_dir)
    copy_assets(args.output_dir)
    write_readme(args.output_dir)
    print("\nObsidian Topic Map Export")
    print("-------------------------")
    print(f"Topics exported: {len(topics)}")
    print(f"Families exported: {topics['topic_family'].nunique()}")
    print(f"Output folder: {args.output_dir}")
    print()


if __name__ == "__main__":
    main()
