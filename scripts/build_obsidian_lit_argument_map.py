from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd


ROOT = Path("/Users/janet/Documents/TDSEM Developmental Calibration Research")
OBSIDIAN = ROOT / "obsidian/TDSEM_Topic_Map"
ARG_DIR = OBSIDIAN / "Literature_Review_Arguments"
PAPER_DIR = OBSIDIAN / "Literature_Paper_Notes"
OUT_DIR = ROOT / "outputs/literature_pdf_ris_audit"

CLAIM_HITS = OUT_DIR / "pdf_ris_claim_hits.csv"
DESIGN_HITS = OUT_DIR / "similar_design_hits.csv"
CLEAN_RIS = ROOT / "data/processed/tdsem_ris_corpus_clean.csv"
SEED_CSV = OUT_DIR / "argument_paper_seed_list.csv"
MISSING_CSV = OUT_DIR / "missing_full_paper_candidates.csv"


ARGUMENTS = [
    {
        "key": "caregiving_foundation",
        "title": "01 Caregiving And Scaffolding As Developmental Context",
        "question": "Why should caregiving be treated as a foundational developmental context?",
        "claim": "Responsive caregiving and scaffolding provide a powerful developmental context, but their effects are not uniform across all children.",
        "next_link": "02 Child Agency In Parent Child Systems",
    },
    {
        "key": "child_agency",
        "title": "02 Child Agency In Parent Child Systems",
        "question": "Why is the child not merely the recipient of caregiving?",
        "claim": "Children actively shape interaction through attention, initiation, responsiveness, and child-to-parent effects.",
        "next_link": "03 Joint Attention As Social Learning Mechanism",
    },
    {
        "key": "joint_attention",
        "title": "03 Joint Attention As Social Learning Mechanism",
        "question": "Why use joint attention as the observable developmental handle for child participation?",
        "claim": "Joint attention is an early, observable marker of how children participate in social learning.",
        "next_link": "04 RJA And IJA As Distinct Pathways",
    },
    {
        "key": "rja_ija_distinction",
        "title": "04 RJA And IJA As Distinct Pathways",
        "question": "Why should responding and initiating joint attention be separated?",
        "claim": "RJA and IJA reflect different forms of child participation and may calibrate caregiving in different ways.",
        "next_link": "05 Heterogeneity And Developmental Localization",
    },
    {
        "key": "heterogeneity_localization",
        "title": "05 Heterogeneity And Developmental Localization",
        "question": "Why ask where and for whom caregiving becomes effective?",
        "claim": "Developmental effects are heterogeneous and may be localized within specific regions of developmental space.",
        "next_link": "06 Dyadic Neural Organization",
    },
    {
        "key": "dyadic_neural",
        "title": "06 Dyadic Neural Organization",
        "question": "Why move from behavior to parent-child neural organization?",
        "claim": "Parent-child interaction can be studied as dyadic neural organization during naturalistic and structured interaction.",
        "next_link": "07 Neural Directionality And Leadership",
    },
    {
        "key": "neural_directionality",
        "title": "07 Neural Directionality And Leadership",
        "question": "Why is synchrony not enough?",
        "claim": "Directionality and effective connectivity are needed to ask who leads, follows, or influences whom during interaction.",
        "next_link": "08 Longitudinal Recalibration",
    },
    {
        "key": "longitudinal_recalibration",
        "title": "08 Longitudinal Recalibration",
        "question": "Why does the dissertation need a longitudinal/recalibration frame?",
        "claim": "Developmental calibration requires attention to change over time, not only concurrent associations.",
        "next_link": "09 Similar Study Designs",
    },
    {
        "key": "similar_study_design",
        "title": "09 Similar Study Designs",
        "question": "Have prior studies used a similar design?",
        "claim": "Prior work contains many partial design matches, but rarely integrates structured/free-play interaction, caregiving, joint attention, child performance, and neural directionality in one design.",
        "next_link": "",
    },
]

CLAIM_KEYWORDS = {
    "caregiving_foundation": [
        "parental sensitivity", "maternal sensitivity", "responsive caregiving",
        "responsiveness", "scaffolding", "parent-child interaction",
    ],
    "child_agency": [
        "child agency", "child effects", "child-led", "bidirectional",
        "transactional", "reciprocal", "initiating",
    ],
    "joint_attention": [
        "joint attention", "shared attention", "social attention", "joint engagement",
    ],
    "rja_ija_distinction": [
        "responding to joint attention", "response to joint attention", "rja",
        "initiating joint attention", "initiation of joint attention", "ija",
    ],
    "heterogeneity_localization": [
        "heterogeneity", "individual differences", "moderator", "nonlinear",
        "threshold", "trajectory", "profile", "state space",
    ],
    "dyadic_neural": [
        "hyperscanning", "interbrain", "inter-brain", "brain-to-brain",
        "neural synchrony", "fnirs",
    ],
    "neural_directionality": [
        "granger", "effective connectivity", "directionality", "directional",
        "information flow", "leader", "follower",
    ],
    "longitudinal_recalibration": [
        "longitudinal", "prospective", "developmental change", "stability",
        "trajectory", "cascade",
    ],
}


def slugify(text: str, max_len: int = 90) -> str:
    text = re.sub(r"[^\w\s-]", "", str(text), flags=re.UNICODE)
    text = re.sub(r"\s+", "_", text.strip())
    text = re.sub(r"_+", "_", text)
    return text[:max_len].strip("_") or "Untitled"


def norm_title(row: pd.Series) -> str:
    title = str(row.get("title_or_file", "") or "").strip()
    if not title or title.lower() == "nan":
        title = Path(str(row.get("file", ""))).stem
    return re.sub(r"\s+", " ", title)


def source_priority(row: pd.Series) -> tuple:
    source_type = str(row.get("source_type", ""))
    priority = str(row.get("priority", ""))
    score = float(row.get("keyword_score", row.get("total_score", 0)) or 0)
    source_rank = 0 if source_type == "PDF" else 1
    priority_rank = {"A_Must_Read": 0, "B_Important": 1, "C_Background": 2, "D_Peripheral": 3}.get(priority, 4)
    return (source_rank, priority_rank, -score)


def paper_id(row: pd.Series) -> str:
    doi = str(row.get("doi", "") or "").strip()
    title = norm_title(row)
    if doi and doi.lower() != "nan":
        return "doi_" + slugify(doi.lower(), 60)
    return slugify(title, 80)


def wiki_link(note_name: str) -> str:
    return f"[[{note_name}]]"


def clean_snippet(text: str, limit: int = 450) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    text = text.replace("|", "\\|")
    return text[:limit]


def load_argument_rows() -> dict[str, pd.DataFrame]:
    claim_df = pd.read_csv(CLAIM_HITS)
    clean_ris = pd.read_csv(CLEAN_RIS) if CLEAN_RIS.exists() else pd.DataFrame()
    rows = {}
    for arg in ARGUMENTS:
        key = arg["key"]
        if key == "similar_study_design":
            design = pd.read_csv(DESIGN_HITS)
            design["keyword_score"] = design.get("total_score", 0)
            design["claim_key"] = key
            design["claim_label"] = arg["claim"]
            design["stance_hint"] = "design_match_or_partial_match"
            # Prefer entries covering structured/free/JA/care/task/neural, but allow partials.
            required = ["structured_task", "free_play", "joint_attention", "caregiving_observed", "task_performance", "neural"]
            for col in required:
                if col not in design.columns:
                    design[col] = 0
            design["design_core_count"] = design[required].gt(0).sum(axis=1)
            sub = design.sort_values(["design_core_count", "total_score"], ascending=[False, False])
        else:
            sub = claim_df[claim_df["claim_key"] == key].copy()
            # The raw RIS parser can occasionally concatenate many records into one very long title.
            # Keep PDF rows and only clean-looking RIS rows here; add clean RIS fallback below.
            title_len = sub["title_or_file"].fillna("").astype(str).str.len()
            sub = sub[(sub["source_type"] == "PDF") | (title_len < 500)].copy()
            sub["rank_tuple"] = sub.apply(source_priority, axis=1)
            sub = sub.sort_values("rank_tuple")
            if len(sub) < 30 and not clean_ris.empty and key in CLAIM_KEYWORDS:
                clean = clean_ris.copy()
                text = (
                    clean["title"].fillna("") + " " +
                    clean["abstract"].fillna("") + " " +
                    clean["author_keywords"].fillna("") + " " +
                    clean["keywords_plus"].fillna("")
                ).str.lower()
                kws = CLAIM_KEYWORDS[key]
                mask = text.apply(lambda x: any(kw.lower() in x for kw in kws))
                clean = clean[mask].copy()
                if not clean.empty:
                    def clean_score(row):
                        body = " ".join(str(row.get(c, "")) for c in ["title", "abstract", "author_keywords", "keywords_plus"]).lower()
                        return sum(body.count(kw.lower()) for kw in kws)

                    clean["keyword_score"] = clean.apply(clean_score, axis=1)
                    clean = clean.sort_values(["keyword_score", "times_cited_wos"], ascending=[False, False]).head(80)
                    fallback = pd.DataFrame({
                        "source_type": "RIS",
                        "priority": "",
                        "domain": clean["cluster"].fillna(""),
                        "file": clean["source_file"].fillna("").apply(lambda x: str(ROOT / "data/raw/ris" / x)),
                        "title_or_file": clean["title"].fillna(""),
                        "year": clean["publication_year"].fillna(""),
                        "authors": clean["authors"].fillna(""),
                        "journal": clean["journal"].fillna(""),
                        "doi": clean["doi"].fillna(""),
                        "claim_key": key,
                        "claim_label": arg["claim"],
                        "keyword_score": clean["keyword_score"],
                        "stance_hint": "RIS_clean_candidate_needs_full_paper_check",
                        "evidence_snippet": clean["abstract"].fillna("").astype(str).str.slice(0, 700),
                    })
                    fallback["rank_tuple"] = fallback.apply(source_priority, axis=1)
                    sub = pd.concat([sub, fallback], ignore_index=True).sort_values("rank_tuple")
        # Deduplicate by paper identity/title.
        selected = []
        seen = set()
        for _, row in sub.iterrows():
            pid = paper_id(row)
            if pid in seen:
                continue
            seen.add(pid)
            selected.append(row)
            if len(selected) >= 25:
                break
        rows[key] = pd.DataFrame(selected)
    return rows


def build_seed_table(arg_rows: dict[str, pd.DataFrame]) -> pd.DataFrame:
    records = []
    for arg in ARGUMENTS:
        key = arg["key"]
        df = arg_rows[key]
        for i, (_, row) in enumerate(df.iterrows(), start=1):
            pid = paper_id(row)
            title = norm_title(row)
            note_name = slugify(title)
            source_type = str(row.get("source_type", ""))
            has_pdf = "yes" if source_type == "PDF" else "not_confirmed"
            records.append({
                "argument_key": key,
                "argument_title": arg["title"],
                "rank": i,
                "paper_id": pid,
                "paper_note": note_name,
                "title": title,
                "source_type": source_type,
                "priority": row.get("priority", ""),
                "domain": row.get("domain", ""),
                "year": row.get("year", ""),
                "journal": row.get("journal", ""),
                "doi": row.get("doi", ""),
                "has_local_full_paper": has_pdf,
                "local_file": row.get("file", ""),
                "score": row.get("keyword_score", row.get("total_score", "")),
                "stance_hint": row.get("stance_hint", ""),
                "snippet": clean_snippet(row.get("evidence_snippet", row.get("snippet", "")), 700),
            })
    return pd.DataFrame(records)


def write_paper_notes(seed: pd.DataFrame) -> None:
    PAPER_DIR.mkdir(parents=True, exist_ok=True)
    grouped = seed.groupby("paper_note", sort=False)
    for note_name, group in grouped:
        first = group.iloc[0]
        safe_title = str(first["title"]).replace('"', "'")
        safe_doi = str(first.get("doi", "")).replace('"', "'")
        args = [wiki_link(t) for t in group["argument_title"].drop_duplicates()]
        source_type = first.get("source_type", "")
        has_pdf = first.get("has_local_full_paper", "")
        local_file = str(first.get("local_file", ""))
        lines = [
            "---",
            f"title: \"{safe_title}\"",
            f"source_type: {source_type}",
            f"has_local_full_paper: {has_pdf}",
            f"doi: \"{safe_doi}\"",
            "---",
            f"# {first['title']}",
            "",
            f"Arguments: {', '.join(args)}",
            "",
            f"Source type: `{source_type}`",
            f"Priority/domain: `{first.get('priority','')}` / `{first.get('domain','')}`",
            f"Year/journal: `{first.get('year','')}` / `{first.get('journal','')}`",
            f"DOI: `{first.get('doi','')}`",
            f"Local full paper: `{has_pdf}`",
            "",
            "## Local File",
            "",
            f"`{local_file}`",
            "",
            "## Why It Is In The Map",
            "",
        ]
        for _, row in group.iterrows():
            lines.extend([
                f"- {wiki_link(row['argument_title'])}: {row.get('stance_hint','')}; score `{row.get('score','')}`.",
            ])
        lines.extend(["", "## Evidence Snippets", ""])
        for _, row in group.head(5).iterrows():
            snip = str(row.get("snippet", "") or "").strip()
            if snip:
                lines.append(f"- **{row['argument_title']}**: {snip}")
        (PAPER_DIR / f"{note_name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_argument_notes(seed: pd.DataFrame) -> None:
    ARG_DIR.mkdir(parents=True, exist_ok=True)
    for idx, arg in enumerate(ARGUMENTS):
        df = seed[seed["argument_key"] == arg["key"]].copy()
        prev_link = ARGUMENTS[idx - 1]["title"] if idx > 0 else ""
        next_link = arg["next_link"]
        lines = [
            f"# {arg['title']}",
            "",
            f"Question: **{arg['question']}**",
            "",
            f"Working claim: {arg['claim']}",
            "",
            "## Position In Dissertation Story",
            "",
            f"Previous: {wiki_link(prev_link) if prev_link else 'Start of literature review chain'}",
            f"Next: {wiki_link(next_link) if next_link else 'End of literature review chain'}",
            "",
            "## Seed Papers",
            "",
            "| Rank | Paper | Source | Full paper | Stance / use |",
            "|---:|---|---|---|---|",
        ]
        for _, row in df.iterrows():
            lines.append(
                f"| {int(row['rank'])} | {wiki_link(row['paper_note'])} | "
                f"{row.get('source_type','')} / {row.get('priority','')} / {row.get('domain','')} | "
                f"{row.get('has_local_full_paper','')} | {row.get('stance_hint','')} |"
            )
        lines.extend([
            "",
            "## How This Section Should Argue",
            "",
            "- Use the PDF-backed papers as the first citation layer.",
            "- Use RIS-only papers as candidates to verify or download before final citation.",
            "- Keep tension visible: this section should explain both what is known and what remains unresolved.",
            "",
            "## RIS-Only / Needs Full Paper Check",
            "",
        ])
        missing = df[df["has_local_full_paper"] != "yes"]
        if missing.empty:
            lines.append("All seed items in this argument currently have local PDF-backed evidence.")
        else:
            for _, row in missing.iterrows():
                doi = row.get("doi", "")
                lines.append(f"- {row['title']} | DOI: `{doi}` | source: `{row.get('local_file','')}`")
        (ARG_DIR / f"{arg['title']}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_index(seed: pd.DataFrame) -> None:
    lines = [
        "# Literature Review Argument Index",
        "",
        "This map links the dissertation literature review arguments to seed papers from the organized PDFs and RIS records.",
        "",
        "## Argument Chain",
        "",
    ]
    for arg in ARGUMENTS:
        n = len(seed[seed["argument_key"] == arg["key"]])
        n_pdf = (seed[(seed["argument_key"] == arg["key"]) & (seed["has_local_full_paper"] == "yes")]).shape[0]
        lines.append(f"- {wiki_link(arg['title'])} ({n} seed papers; {n_pdf} local PDFs confirmed)")
    lines.extend([
        "",
        "## Working Dissertation Spine",
        "",
        "Caregiving matters, but it is not uniformly effective. Its developmental value depends on the child's social-attentional state, the structure of interaction, and dyadic temporal/neural organization.",
        "",
        "## CSV Companions",
        "",
        f"- `{SEED_CSV}`",
        f"- `{MISSING_CSV}`",
    ])
    (ARG_DIR / "00 Literature Review Argument Index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    arg_rows = load_argument_rows()
    seed = build_seed_table(arg_rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    seed.to_csv(SEED_CSV, index=False)
    missing = seed[seed["has_local_full_paper"] != "yes"].copy()
    missing.to_csv(MISSING_CSV, index=False)
    write_paper_notes(seed)
    write_argument_notes(seed)
    write_index(seed)
    print(f"Wrote {SEED_CSV}")
    print(f"Wrote {MISSING_CSV}")
    print(f"Wrote argument notes to {ARG_DIR}")
    print(f"Wrote paper notes to {PAPER_DIR}")
    print("Counts by argument:")
    print(seed.groupby("argument_title").agg(seed_papers=("paper_id", "count"), local_pdfs=("has_local_full_paper", lambda s: (s == "yes").sum())).to_string())


if __name__ == "__main__":
    main()
