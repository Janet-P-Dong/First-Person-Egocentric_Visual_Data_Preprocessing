"""Prepare theory-driven evidence-map tables from the cleaned TDSEM corpus."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np
import pandas as pd


DEFAULT_INPUT = Path("data/processed/tdsem_ris_corpus_clean.csv")
DEFAULT_TOPIC_ASSIGNMENTS = Path("outputs/topics/paper_topic_assignments.csv")
DEFAULT_OUTPUT_DIR = Path("outputs/evidence_maps")


THEORY_PATTERNS = {
    "Developmental Systems Theory": [r"developmental systems", r"relational developmental"],
    "Dynamic Systems Theory": [r"dynamic systems", r"state space", r"nonlinear", r"self-organ"],
    "Transactional Theory": [r"transactional", r"bidirectional", r"reciprocal", r"child effects", r"parent effects"],
    "Developmental Cascades": [r"developmental cascade", r"cascade effects"],
    "Sociocultural / Scaffolding Theory": [r"sociocultural", r"scaffold", r"guided participation", r"vygotsky"],
    "Attachment Theory": [r"attachment", r"sensitivity", r"secure base"],
    "Joint Attention Theory": [r"joint attention", r"initiating joint attention", r"responding to joint attention"],
    "Social Neuroscience": [r"social neuroscience", r"hyperscanning", r"interbrain", r"brain-to-brain"],
    "Effective Connectivity": [r"effective connectivity", r"granger", r"directional connectivity", r"directed connectivity"],
}

METHOD_PATTERNS = {
    "Review / Meta-analysis": [r"review", r"meta-analysis", r"systematic review"],
    "Longitudinal": [r"longitudinal", r"follow-up", r"over time", r"trajectory"],
    "Cross-sectional": [r"cross-sectional", r"concurrent"],
    "Experimental / Intervention": [r"experiment", r"intervention", r"randomi[sz]ed", r"training", r"trial"],
    "Observational Interaction Coding": [r"observed", r"observational", r"coding", r"free play", r"structured play"],
    "Measurement / Instrument": [r"measure", r"instrument", r"scale", r"psychometric", r"validation"],
    "Neuroimaging / Neuroscience": [r"fNIRS", r"EEG", r"fMRI", r"MRI", r"neural", r"brain"],
    "Hyperscanning": [r"hyperscanning", r"interbrain", r"brain-to-brain"],
    "Dynamic / State-Space Modeling": [r"state space", r"dynamic systems", r"variability", r"nonlinear"],
    "Directional / Connectivity Modeling": [r"granger", r"effective connectivity", r"directionality", r"directed connectivity"],
}

AGENCY_PATTERNS = {
    "Initiating Joint Attention": [r"initiating joint attention", r"\bIJA\b", r"initiation of joint attention"],
    "Responding to Joint Attention": [r"responding to joint attention", r"response to joint attention", r"\bRJA\b"],
    "Joint Attention General": [r"joint attention", r"shared attention", r"gaze following"],
    "Child Agency / Child Effects": [r"child agency", r"child effects", r"child-led", r"child initiated", r"active child"],
    "Social Participation / Engagement": [r"social participation", r"social engagement", r"shared intentionality"],
}

CAREGIVING_PATTERNS = {
    "RIFL / Responsive Interactions for Learning": [r"\bRIFL\b", r"responsive interactions for learning"],
    "Developmental Scaffolding": [r"scaffold", r"guided participation", r"learning support", r"contingent support"],
    "Emotional Support": [r"emotional support", r"emotion", r"affect", r"warmth"],
    "Responsive Caregiving": [r"responsive caregiving", r"parental responsiveness", r"maternal responsiveness", r"caregiver responsiveness"],
    "Sensitivity": [r"sensitivity", r"maternal sensitivity", r"caregiver sensitivity"],
    "Parent-Child Interaction": [r"parent-child interaction", r"parent child interaction", r"mother-child", r"father-child", r"dyad"],
}

QUESTION_PATTERNS = {
    "Prediction": [r"predict", r"associated with", r"prospective"],
    "Mediation": [r"mediat", r"indirect"],
    "Moderation": [r"moderat", r"interaction effect", r"conditional"],
    "Mechanism": [r"mechanism", r"process", r"pathway", r"explain"],
    "Measurement": [r"measure", r"instrument", r"coding", r"psychometric"],
    "Heterogeneity / Profiles": [r"heterogeneity", r"profile", r"latent class", r"latent profile", r"trajectory"],
    "Directionality / Influence": [r"directionality", r"granger", r"influence", r"leader-follower"],
    "Theory / Framework": [r"theory", r"framework", r"model"],
}

GAP_PATTERNS = {
    "Theory-method gap": [r"linear", r"average effects", r"unidirectional", r"methodological"],
    "Heterogeneity unresolved": [r"heterogeneity", r"individual differences", r"variability", r"for whom"],
    "Directionality unresolved": [r"directionality", r"influence", r"causal", r"granger"],
    "Mechanism unresolved": [r"mechanism", r"process", r"pathway", r"unknown", r"unclear"],
    "Longitudinal change unresolved": [r"longitudinal", r"over time", r"developmental change", r"stability"],
    "Measurement gap": [r"measurement", r"operational", r"coding", r"assessment"],
}


def clean_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def find_matches(text: str, patterns: Iterable[str]) -> list[str]:
    matches = []
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            matches.append(pattern.replace(r"\b", "").strip("\\"))
    return matches


def code_best(text: str, codebook: Mapping[str, list[str]], default: str = "Unclear") -> tuple[str, str, str]:
    scored = []
    for label, patterns in codebook.items():
        matches = find_matches(text, patterns)
        if matches:
            scored.append((label, len(matches), "; ".join(matches)))
    if not scored:
        return default, "", "low"
    label, score, evidence = sorted(scored, key=lambda item: item[1], reverse=True)[0]
    confidence = "high" if score >= 2 else "medium"
    return label, evidence, confidence


def extract_sentence(text: str, patterns: Iterable[str]) -> str:
    text = clean_text(text)
    if not text:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    for sentence in sentences:
        for pattern in patterns:
            if re.search(pattern, sentence, flags=re.IGNORECASE):
                return sentence[:900]
    return ""


def load_inputs(input_path: Path, topic_assignments_path: Path) -> pd.DataFrame:
    if not input_path.exists():
        raise FileNotFoundError(f"Input corpus does not exist: {input_path}")
    df = pd.read_csv(input_path)
    if topic_assignments_path.exists():
        topics = pd.read_csv(topic_assignments_path)
        keep = [column for column in ["record_id", "topic_id", "topic_probability"] if column in topics]
        if "record_id" in keep:
            df = df.merge(topics[keep], on="record_id", how="left")
    else:
        df["topic_id"] = np.nan
        df["topic_probability"] = np.nan
    return df


def code_evidence_map(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in df.iterrows():
        text = clean_text(
            " ".join(
                [
                    clean_text(row.get("title")),
                    clean_text(row.get("abstract")),
                    clean_text(row.get("author_keywords")),
                    clean_text(row.get("keywords_plus")),
                ]
            )
        )
        abstract = clean_text(row.get("abstract"))
        theory, theory_evidence, theory_conf = code_best(text, THEORY_PATTERNS)
        method, method_evidence, method_conf = code_best(text, METHOD_PATTERNS)
        agency, agency_evidence, agency_conf = code_best(text, AGENCY_PATTERNS)
        caregiving, caregiving_evidence, caregiving_conf = code_best(text, CAREGIVING_PATTERNS)
        question, question_evidence, question_conf = code_best(text, QUESTION_PATTERNS)
        gap, gap_evidence, gap_conf = code_best(text, GAP_PATTERNS)
        rows.append(
            {
                **row.to_dict(),
                "theory": theory,
                "theory_evidence": theory_evidence,
                "theory_confidence": theory_conf,
                "empirical_method": method,
                "method_evidence": method_evidence,
                "method_confidence": method_conf,
                "agency_marker": agency,
                "agency_evidence": agency_evidence,
                "agency_confidence": agency_conf,
                "caregiving_scaffolding_construct": caregiving,
                "caregiving_evidence": caregiving_evidence,
                "caregiving_confidence": caregiving_conf,
                "research_question_type": question,
                "research_question_evidence": question_evidence,
                "research_question_confidence": question_conf,
                "main_finding_quote": extract_sentence(
                    abstract, [r"findings", r"results", r"showed", r"suggest", r"indicate"]
                ),
                "limitation_or_gap_quote": extract_sentence(
                    abstract, [r"unknown", r"unclear", r"future", r"limited", r"gap", r"little is known"]
                ),
                "unresolved_gap": gap,
                "unresolved_gap_evidence": gap_evidence,
                "unresolved_gap_confidence": gap_conf,
                "relevance_to_dissertation": infer_relevance(agency, caregiving, theory, method, gap),
            }
        )
    return pd.DataFrame(rows)


def infer_relevance(agency: str, caregiving: str, theory: str, method: str, gap: str) -> str:
    markers = []
    if agency != "Unclear":
        markers.append("child agency/social attention")
    if caregiving != "Unclear":
        markers.append("caregiving/scaffolding")
    if theory in {"Transactional Theory", "Dynamic Systems Theory", "Developmental Systems Theory"}:
        markers.append("dynamic relational theory")
    if method in {"Longitudinal", "Neuroimaging / Neuroscience", "Hyperscanning", "Directional / Connectivity Modeling"}:
        markers.append("behavioral/neural/longitudinal timescale")
    if gap != "Unclear":
        markers.append("unresolved gap")
    return "; ".join(markers) if markers else ""


def calculate_relevance_score(row: pd.Series) -> int:
    """Score papers by fit with the dissertation's developmental calibration focus."""
    score = 0
    if row.get("agency_marker") in {
        "Initiating Joint Attention",
        "Responding to Joint Attention",
    }:
        score += 4
    elif row.get("agency_marker") in {
        "Joint Attention General",
        "Child Agency / Child Effects",
        "Social Participation / Engagement",
    }:
        score += 2

    if row.get("caregiving_scaffolding_construct") == "RIFL / Responsive Interactions for Learning":
        score += 4
    elif row.get("caregiving_scaffolding_construct") in {
        "Developmental Scaffolding",
        "Responsive Caregiving",
        "Emotional Support",
        "Sensitivity",
        "Parent-Child Interaction",
    }:
        score += 2

    if row.get("theory") in {
        "Developmental Systems Theory",
        "Dynamic Systems Theory",
        "Transactional Theory",
        "Sociocultural / Scaffolding Theory",
        "Joint Attention Theory",
    }:
        score += 2
    elif row.get("theory") in {"Social Neuroscience", "Effective Connectivity"}:
        score += 1

    if row.get("empirical_method") in {
        "Longitudinal",
        "Observational Interaction Coding",
        "Neuroimaging / Neuroscience",
        "Hyperscanning",
        "Directional / Connectivity Modeling",
        "Dynamic / State-Space Modeling",
    }:
        score += 1

    if row.get("unresolved_gap") != "Unclear":
        score += 1
    return score


def crosstab(df: pd.DataFrame, row: str, col: str) -> pd.DataFrame:
    table = pd.crosstab(df[row].fillna("Unclear"), df[col].fillna("Unclear"))
    table["Total"] = table.sum(axis=1)
    return table.sort_values("Total", ascending=False).reset_index()


def write_outputs(df: pd.DataFrame, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    df = df.copy()
    df["dissertation_relevance_score"] = df.apply(calculate_relevance_score, axis=1)
    df.to_csv(output_dir / "paper_evidence_map.csv", index=False)

    manual_cols = [
        "record_id",
        "cluster",
        "subcluster",
        "topic_id",
        "title",
        "abstract",
        "theory",
        "empirical_method",
        "agency_marker",
        "caregiving_scaffolding_construct",
        "research_question_type",
        "main_finding_quote",
        "limitation_or_gap_quote",
        "unresolved_gap",
        "relevance_to_dissertation",
        "dissertation_relevance_score",
        "human_theory",
        "human_research_question",
        "human_method",
        "human_main_finding",
        "human_limitation",
        "human_unresolved_gap",
        "human_relevance_to_dissertation",
        "human_notes",
    ]
    manual = df.copy()
    for col in manual_cols:
        if col not in manual.columns:
            manual[col] = ""
    manual[manual_cols].to_csv(output_dir / "manual_coding_template.csv", index=False)

    tables = {
        "theory_by_method.csv": crosstab(df, "theory", "empirical_method"),
        "theory_by_agency_marker.csv": crosstab(df, "theory", "agency_marker"),
        "agency_by_caregiving_construct.csv": crosstab(
            df, "agency_marker", "caregiving_scaffolding_construct"
        ),
        "theory_by_unresolved_gap.csv": crosstab(df, "theory", "unresolved_gap"),
        "method_by_unresolved_gap.csv": crosstab(df, "empirical_method", "unresolved_gap"),
        "cluster_by_theory.csv": crosstab(df, "cluster", "theory"),
        "cluster_by_method.csv": crosstab(df, "cluster", "empirical_method"),
        "cluster_by_gap.csv": crosstab(df, "cluster", "unresolved_gap"),
    }
    if "topic_id" in df.columns and df["topic_id"].notna().any():
        tables["topic_by_theory.csv"] = crosstab(df, "topic_id", "theory")
        tables["topic_by_gap.csv"] = crosstab(df, "topic_id", "unresolved_gap")
    for filename, table in tables.items():
        table.to_csv(output_dir / filename, index=False)

    top = df.copy()
    top["_cited"] = pd.to_numeric(top.get("total_times_cited"), errors="coerce").fillna(0)
    top.sort_values("_cited", ascending=False).head(100).drop(columns="_cited").to_csv(
        output_dir / "top100_cited_evidence_map.csv", index=False
    )
    top.sort_values(
        ["dissertation_relevance_score", "_cited"], ascending=[False, False]
    ).head(100).drop(columns="_cited").to_csv(
        output_dir / "top100_relevance_weighted_cited.csv", index=False
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare TDSEM evidence-map tables.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--topic-assignments", type=Path, default=DEFAULT_TOPIC_ASSIGNMENTS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    df = load_inputs(args.input, args.topic_assignments)
    coded = code_evidence_map(df)
    write_outputs(coded, args.output_dir)
    print("\nTDSEM Evidence Map Preparation")
    print("------------------------------")
    print(f"Papers coded: {len(coded)}")
    print(f"Outputs saved to: {args.output_dir}")
    print()


if __name__ == "__main__":
    main()
