"""Classify BERTopic topics into dissertation-facing evidence-map families."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np
import pandas as pd


DEFAULT_TOPIC_DIR = Path("outputs/topics_k30")
DEFAULT_EVIDENCE_MAP = Path("outputs/evidence_maps_k30/paper_evidence_map.csv")
DEFAULT_OUTPUT_DIR = Path("outputs/topic_classification_k30")


TOPIC_FAMILY_PATTERNS = {
    "Child Agency and Joint Attention": [
        r"joint attention",
        r"\bija\b",
        r"\brja\b",
        r"gaze",
        r"autism",
        r"asd",
        r"social communication",
        r"shared attention",
        r"engagement",
        r"initiat",
        r"respond",
    ],
    "Caregiving, Scaffolding, and Parent-Child Interaction": [
        r"parenting",
        r"maternal",
        r"mother",
        r"father",
        r"caregiv",
        r"parent-child",
        r"mother-child",
        r"scaffold",
        r"responsive",
        r"sensitivity",
        r"emotional support",
        r"dyad",
    ],
    "Developmental Pathways and Heterogeneity": [
        r"trajector",
        r"pathway",
        r"profile",
        r"heterogeneity",
        r"latent class",
        r"latent profile",
        r"growth mixture",
        r"longitudinal",
        r"developmental change",
        r"cascade",
    ],
    "Neural Calibration and Directionality": [
        r"brain",
        r"neural",
        r"connectivity",
        r"cortex",
        r"fmri",
        r"fnirs",
        r"eeg",
        r"hyperscanning",
        r"interbrain",
        r"synchron",
        r"granger",
        r"directional",
        r"effective connectivity",
    ],
    "Physiological Regulation": [
        r"rsa",
        r"respiratory sinus",
        r"heart rate",
        r"vagal",
        r"physiological",
        r"autonomic",
        r"emotion regulation",
        r"reactivity",
    ],
    "Learning, Language, and Academic Development": [
        r"language",
        r"reading",
        r"literacy",
        r"learning",
        r"academic",
        r"school",
        r"vocabulary",
        r"speech",
        r"teacher",
    ],
    "Attachment and Relational Security": [
        r"attachment",
        r"security",
        r"secure base",
        r"relationship quality",
        r"relational",
    ],
    "Mental Health, Risk, and Adjustment": [
        r"depression",
        r"anxiety",
        r"externalizing",
        r"internalizing",
        r"aggression",
        r"symptoms",
        r"stress",
        r"risk",
        r"psychopathology",
        r"behavior problems",
    ],
    "Methods and Measurement": [
        r"state space",
        r"algorithm",
        r"model",
        r"measurement",
        r"psychometric",
        r"scale",
        r"latent",
        r"analysis",
        r"method",
    ],
    "Health and Public Health Context": [
        r"covid",
        r"pandemic",
        r"vaccine",
        r"pregnancy",
        r"disease",
        r"obesity",
        r"feeding",
        r"food",
        r"health",
    ],
    "Off-Domain / Search Noise": [
        r"leader",
        r"leadership",
        r"follower",
        r"workplace",
        r"organizational",
        r"\beconomic growth\b",
        r"\beconomic\b",
        r"emissions",
        r"energy",
        r"older care",
        r"older adults",
        r"patient-centered",
        r"nurse-patient",
        r"global burden",
        r"hepatitis",
        r"preeclampsia",
        r"zika",
        r"gestational diabetes",
        r"remote sensing",
        r"land cover",
        r"image segmentation",
        r"spatial-spectral",
        r"visual mamba",
    ],
}


TOPIC_ROLE_PATTERNS = {
    "Core Dissertation Construct": [
        r"joint attention",
        r"parent-child",
        r"mother-child",
        r"scaffold",
        r"responsive",
        r"caregiv",
        r"transactional",
        r"bidirectional",
        r"longitudinal",
        r"hyperscanning",
        r"interbrain",
        r"effective connectivity",
    ],
    "Supporting Developmental Evidence": [
        r"attachment",
        r"language",
        r"learning",
        r"emotion regulation",
        r"rsa",
        r"trajector",
        r"externalizing",
        r"internalizing",
        r"autism",
        r"asd",
    ],
    "Methodological or Measurement Resource": [
        r"measurement",
        r"psychometric",
        r"state space",
        r"latent",
        r"growth mixture",
        r"algorithm",
        r"model",
    ],
    "Boundary / Exclusion Candidate": [
        r"leader",
        r"leadership",
        r"\beconomic\b",
        r"emissions",
        r"covid",
        r"pandemic",
        r"vaccine",
        r"older care",
        r"patient-centered",
        r"nurse-patient",
        r"global burden",
        r"remote sensing",
        r"land cover",
        r"image segmentation",
    ],
}


def clean_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def normalize_topic_id(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    try:
        number = float(value)
        if number.is_integer():
            return str(int(number))
    except (TypeError, ValueError):
        pass
    return str(value)


def match_patterns(text: str, patterns: Iterable[str]) -> list[str]:
    matches = []
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            matches.append(pattern)
    return matches


def score_codebook(text: str, codebook: Mapping[str, list[str]]) -> tuple[str, str, str, int]:
    if "Off-Domain / Search Noise" in codebook:
        boundary_matches = match_patterns(text, codebook["Off-Domain / Search Noise"])
        if len(boundary_matches) >= 2:
            confidence = "high" if len(boundary_matches) >= 2 else "medium"
            return (
                "Off-Domain / Search Noise",
                "; ".join(boundary_matches),
                confidence,
                len(boundary_matches),
            )
    if "Boundary / Exclusion Candidate" in codebook:
        boundary_matches = match_patterns(text, codebook["Boundary / Exclusion Candidate"])
        if len(boundary_matches) >= 3:
            confidence = "high" if len(boundary_matches) >= 2 else "medium"
            return (
                "Boundary / Exclusion Candidate",
                "; ".join(boundary_matches),
                confidence,
                len(boundary_matches),
            )

    scored = []
    for label, patterns in codebook.items():
        matches = match_patterns(text, patterns)
        if matches:
            scored.append((label, len(matches), "; ".join(matches)))
    if not scored:
        return "Unclassified / Needs Review", "", "low", 0
    label, score, evidence = sorted(scored, key=lambda item: item[1], reverse=True)[0]
    confidence = "high" if score >= 3 else "medium"
    return label, evidence, confidence, score


def top_value(series: pd.Series) -> str:
    series = series.dropna().astype(str)
    series = series[series.ne("")]
    if series.empty:
        return ""
    return series.value_counts().index[0]


def top_values(series: pd.Series, n: int = 3) -> str:
    series = series.dropna().astype(str)
    series = series[series.ne("")]
    if series.empty:
        return ""
    counts = series.value_counts().head(n)
    return "; ".join(f"{label} ({count})" for label, count in counts.items())


def load_topic_inputs(topic_dir: Path, evidence_map_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    required = {
        "topic_sizes": topic_dir / "topic_sizes.csv",
        "topic_keywords": topic_dir / "topic_keywords.csv",
        "representative_papers": topic_dir / "representative_papers.csv",
        "topic_coherence": topic_dir / "topic_coherence.csv",
        "evidence_map": evidence_map_path,
    }
    missing = [str(path) for path in required.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing required input files: " + ", ".join(missing))

    topic_sizes = pd.read_csv(required["topic_sizes"])
    topic_keywords = pd.read_csv(required["topic_keywords"])
    representatives = pd.read_csv(required["representative_papers"])
    topic_coherence = pd.read_csv(required["topic_coherence"])
    evidence = pd.read_csv(required["evidence_map"])
    return topic_sizes, topic_keywords, representatives, topic_coherence, evidence


def build_topic_text(
    topic_id: str,
    topic_sizes: pd.DataFrame,
    topic_keywords: pd.DataFrame,
    representatives: pd.DataFrame,
) -> tuple[str, str, str]:
    topic_row = topic_sizes[topic_sizes["_topic_id"] == topic_id]
    name = clean_text(topic_row["Name"].iloc[0]) if not topic_row.empty else ""
    keywords = topic_keywords[topic_keywords["_topic_id"] == topic_id].sort_values("rank")
    keyword_text = "; ".join(keywords["keyword"].map(clean_text).tolist())
    reps = representatives[representatives["_topic_id"] == topic_id].head(8)
    representative_titles = " | ".join(reps["title"].map(clean_text).tolist())
    topic_text = " ".join([name, keyword_text, representative_titles]).lower()
    return topic_text, keyword_text, representative_titles


def classify_topics(
    topic_sizes: pd.DataFrame,
    topic_keywords: pd.DataFrame,
    representatives: pd.DataFrame,
    topic_coherence: pd.DataFrame,
    evidence: pd.DataFrame,
) -> pd.DataFrame:
    for frame, column in [
        (topic_sizes, "Topic"),
        (topic_keywords, "topic_id"),
        (representatives, "topic_id"),
        (topic_coherence, "topic_id"),
        (evidence, "topic_id"),
    ]:
        frame["_topic_id"] = frame[column].map(normalize_topic_id)

    rows = []
    for _, topic in topic_sizes.sort_values("Topic").iterrows():
        topic_id = normalize_topic_id(topic["Topic"])
        topic_text, keyword_text, representative_titles = build_topic_text(
            topic_id, topic_sizes, topic_keywords, representatives
        )
        family, family_evidence, family_confidence, family_score = score_codebook(
            topic_text, TOPIC_FAMILY_PATTERNS
        )
        role, role_evidence, role_confidence, role_score = score_codebook(
            topic_text, TOPIC_ROLE_PATTERNS
        )

        topic_papers = evidence[evidence["_topic_id"] == topic_id].copy()
        if not topic_papers.empty:
            relevance = pd.to_numeric(
                topic_papers.get("dissertation_relevance_score"), errors="coerce"
            ).fillna(0)
            citations = pd.to_numeric(topic_papers.get("total_times_cited"), errors="coerce").fillna(0)
            mean_relevance = float(relevance.mean())
            max_relevance = int(relevance.max())
            median_citations = float(citations.median())
            dominant_cluster = top_values(topic_papers["cluster"])
            dominant_theory = top_values(topic_papers["theory"])
            dominant_method = top_values(topic_papers["empirical_method"])
            dominant_gap = top_values(topic_papers["unresolved_gap"])
            dominant_agency = top_values(topic_papers["agency_marker"])
            dominant_caregiving = top_values(topic_papers["caregiving_scaffolding_construct"])
        else:
            mean_relevance = np.nan
            max_relevance = 0
            median_citations = np.nan
            dominant_cluster = ""
            dominant_theory = ""
            dominant_method = ""
            dominant_gap = ""
            dominant_agency = ""
            dominant_caregiving = ""

        dissertation_priority = infer_priority(
            family=family,
            role=role,
            mean_relevance=mean_relevance,
            max_relevance=max_relevance,
        )
        coherence_row = topic_coherence[topic_coherence["_topic_id"] == topic_id]
        coherence = (
            float(coherence_row["npmi_coherence"].iloc[0])
            if not coherence_row.empty and pd.notna(coherence_row["npmi_coherence"].iloc[0])
            else np.nan
        )

        rows.append(
            {
                "topic_id": topic_id,
                "topic_size": int(topic.get("Count", 0)),
                "bertopic_name": clean_text(topic.get("Name")),
                "top_keywords": keyword_text,
                "topic_family": family,
                "topic_family_evidence": family_evidence,
                "topic_family_confidence": family_confidence,
                "topic_family_rule_score": family_score,
                "topic_role": role,
                "topic_role_evidence": role_evidence,
                "topic_role_confidence": role_confidence,
                "topic_role_rule_score": role_score,
                "dissertation_priority": dissertation_priority,
                "mean_dissertation_relevance_score": mean_relevance,
                "max_dissertation_relevance_score": max_relevance,
                "npmi_coherence": coherence,
                "median_citations": median_citations,
                "dominant_cluster": dominant_cluster,
                "dominant_theory": dominant_theory,
                "dominant_method": dominant_method,
                "dominant_unresolved_gap": dominant_gap,
                "dominant_agency_marker": dominant_agency,
                "dominant_caregiving_construct": dominant_caregiving,
                "representative_titles": representative_titles,
                "human_topic_label": "",
                "human_topic_family": "",
                "human_priority": "",
                "human_notes": "",
            }
        )
    return pd.DataFrame(rows)


def infer_priority(family: str, role: str, mean_relevance: float, max_relevance: int) -> str:
    if family == "Off-Domain / Search Noise" or role == "Boundary / Exclusion Candidate":
        return "D = boundary / likely exclusion"
    if family == "Health and Public Health Context" and (pd.isna(mean_relevance) or mean_relevance < 2.5):
        return "D = boundary / likely exclusion"
    if max_relevance >= 9 or mean_relevance >= 5:
        return "A = core dissertation topic"
    if role == "Core Dissertation Construct" or max_relevance >= 7:
        return "B = important supporting topic"
    if family in {
        "Health and Public Health Context",
        "Methods and Measurement",
        "Mental Health, Risk, and Adjustment",
    }:
        return "C = background or methodological context"
    return "B = important supporting topic"


def write_outputs(classified: pd.DataFrame, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    classified.to_csv(output_dir / "topic_classification.csv", index=False)

    review_cols = [
        "topic_id",
        "topic_size",
        "bertopic_name",
        "top_keywords",
        "topic_family",
        "topic_role",
        "dissertation_priority",
        "npmi_coherence",
        "dominant_cluster",
        "dominant_theory",
        "dominant_method",
        "dominant_unresolved_gap",
        "dominant_agency_marker",
        "dominant_caregiving_construct",
        "representative_titles",
        "human_topic_label",
        "human_topic_family",
        "human_priority",
        "human_notes",
    ]
    classified[review_cols].to_csv(output_dir / "topic_label_review_template.csv", index=False)

    family_summary = (
        classified.groupby(["topic_family", "dissertation_priority"], dropna=False)
        .agg(
            n_topics=("topic_id", "count"),
            total_papers=("topic_size", "sum"),
            mean_coherence=("npmi_coherence", "mean"),
            mean_relevance=("mean_dissertation_relevance_score", "mean"),
        )
        .reset_index()
        .sort_values(["dissertation_priority", "total_papers"], ascending=[True, False])
    )
    family_summary.to_csv(output_dir / "topic_family_summary.csv", index=False)

    classified.sort_values(
        ["dissertation_priority", "mean_dissertation_relevance_score", "topic_size"],
        ascending=[True, False, False],
    ).to_csv(output_dir / "topic_priority_queue.csv", index=False)

    save_figures(classified, output_dir)


def save_figures(classified: pd.DataFrame, output_dir: Path) -> None:
    import matplotlib.pyplot as plt

    fig_dir = output_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    family_counts = (
        classified.groupby("topic_family")["topic_size"].sum().sort_values(ascending=True)
    )
    plt.figure(figsize=(11, max(5, len(family_counts) * 0.38)))
    plt.barh(family_counts.index, family_counts.values, color="#356a8a")
    plt.xlabel("Number of papers assigned to topics")
    plt.title("Topic Families by Paper Count")
    plt.tight_layout()
    plt.savefig(fig_dir / "topic_family_paper_counts.png", dpi=220)
    plt.close()

    priority_counts = (
        classified.groupby("dissertation_priority")["topic_size"].sum().sort_values(ascending=True)
    )
    plt.figure(figsize=(10, 4.8))
    plt.barh(priority_counts.index, priority_counts.values, color="#5d7f3f")
    plt.xlabel("Number of papers assigned to topics")
    plt.title("Topic Priority Tiers")
    plt.tight_layout()
    plt.savefig(fig_dir / "topic_priority_tiers.png", dpi=220)
    plt.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify BERTopic topics into TDSEM topic families.")
    parser.add_argument("--topic-dir", type=Path, default=DEFAULT_TOPIC_DIR)
    parser.add_argument("--evidence-map", type=Path, default=DEFAULT_EVIDENCE_MAP)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    topic_sizes, topic_keywords, representatives, topic_coherence, evidence = load_topic_inputs(
        args.topic_dir, args.evidence_map
    )
    classified = classify_topics(
        topic_sizes=topic_sizes,
        topic_keywords=topic_keywords,
        representatives=representatives,
        topic_coherence=topic_coherence,
        evidence=evidence,
    )
    write_outputs(classified, args.output_dir)
    print("\nTDSEM Topic Classification")
    print("--------------------------")
    print(f"Topics classified: {len(classified)}")
    print(f"Outputs saved to: {args.output_dir}")
    print()


if __name__ == "__main__":
    main()
