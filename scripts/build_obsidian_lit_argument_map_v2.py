from __future__ import annotations

import math
import re
from pathlib import Path

import pandas as pd


ROOT = Path("/Users/janet/Documents/TDSEM Developmental Calibration Research")
PDF_ROOT = Path("/Users/janet/Desktop/TDSEM_Organized_Readings")
OBSIDIAN = ROOT / "obsidian/TDSEM_Topic_Map"
ARG_DIR = OBSIDIAN / "Literature_Review_Arguments"
PAPER_DIR = OBSIDIAN / "Literature_Paper_Notes"
OUT_DIR = ROOT / "outputs/literature_pdf_ris_audit"

CLAIM_HITS = OUT_DIR / "pdf_ris_claim_hits.csv"
DESIGN_HITS = OUT_DIR / "similar_design_hits.csv"
CLEAN_RIS = ROOT / "data/processed/tdsem_ris_corpus_clean.csv"
SEED_CSV = OUT_DIR / "argument_paper_seed_list_v2.csv"
MISSING_CSV = OUT_DIR / "missing_full_paper_candidates_v2.csv"


ARGUMENTS = [
    {
        "key": "caregiving_foundation",
        "title": "01 Caregiving And Scaffolding As Developmental Context",
        "question": "Why should caregiving be treated as a foundational developmental context?",
        "claim": "Responsive caregiving and scaffolding provide a powerful developmental context, but their effects are not uniform across all children.",
        "must": ["parent", "child"],
        "phrases": {
            "parental sensitivity": 12,
            "maternal sensitivity": 12,
            "responsive caregiving": 12,
            "parental responsivity": 10,
            "caregiving quality": 10,
            "scaffolding": 10,
            "tutoring": 8,
            "parent-child interaction": 6,
            "sensitive responsiveness": 10,
        },
        "clusters": {"C": 8, "A": 3},
        "domains": {"Caregiving": 10, "Parent_Child_Interaction": 7, "Transactional_Development": 3},
        "penalty": ["hyperscanning", "fnirs", "granger", "neural directionality"],
        "next_link": "02 Child Agency In Parent Child Systems",
    },
    {
        "key": "child_agency",
        "title": "02 Child Agency In Parent Child Systems",
        "question": "Why is the child not merely the recipient of caregiving?",
        "claim": "Children actively shape interaction through attention, initiation, responsiveness, and child-to-parent effects.",
        "must": ["child"],
        "phrases": {
            "child effects": 14,
            "bidirectional": 12,
            "transactional": 12,
            "reciprocal": 8,
            "child-driven": 10,
            "child led": 10,
            "child-led": 10,
            "mutual influence": 9,
            "coregulation": 8,
            "parent-child coregulation": 12,
            "initiating": 5,
        },
        "clusters": {"A": 10, "B": 9, "C": 3},
        "domains": {"Transactional_Development": 10, "Parent_Child_Interaction": 7, "Joint_Attention": 4},
        "penalty": ["method", "protocol", "toolbox"],
        "next_link": "03 Joint Attention As Social Learning Mechanism",
    },
    {
        "key": "joint_attention",
        "title": "03 Joint Attention As Social Learning Mechanism",
        "question": "Why use joint attention as the observable developmental handle for child participation?",
        "claim": "Joint attention is an early, observable marker of how children participate in social learning.",
        "must": ["joint attention"],
        "phrases": {
            "joint attention": 15,
            "joint engagement": 10,
            "shared attention": 8,
            "social attention": 8,
            "social learning": 6,
            "language development": 4,
            "social communication": 5,
        },
        "clusters": {"B": 10, "A": 2},
        "domains": {"Joint_Attention": 12, "Parent_Child_Interaction": 4},
        "penalty": ["hyperscanning", "granger"],
        "next_link": "04 RJA And IJA As Distinct Pathways",
    },
    {
        "key": "rja_ija_distinction",
        "title": "04 RJA And IJA As Distinct Pathways",
        "question": "Why should responding and initiating joint attention be separated?",
        "claim": "RJA and IJA reflect different forms of child participation and may calibrate caregiving in different ways.",
        "must": ["joint attention"],
        "phrases": {
            "responding to joint attention": 18,
            "response to joint attention": 18,
            "initiating joint attention": 18,
            "initiation of joint attention": 18,
            "rja": 12,
            "ija": 12,
            "reactive joint attention": 10,
            "joint attention bids": 8,
        },
        "clusters": {"B": 10},
        "domains": {"Joint_Attention": 12},
        "penalty": ["parenting style", "attachment"],
        "next_link": "05 Heterogeneity And Developmental Localization",
    },
    {
        "key": "heterogeneity_localization",
        "title": "05 Heterogeneity And Developmental Localization",
        "question": "Why ask where and for whom caregiving becomes effective?",
        "claim": "Developmental effects are heterogeneous and may be localized within specific regions of developmental space.",
        "must": [],
        "phrases": {
            "heterogeneity": 12,
            "individual differences": 10,
            "differential susceptibility": 12,
            "moderator": 10,
            "moderation": 10,
            "person-centered": 9,
            "latent profile": 9,
            "nonlinear": 8,
            "trajectory": 6,
            "developmental cascade": 6,
        },
        "clusters": {"D": 10, "C": 4, "A": 3},
        "domains": {"Developmental_Heterogeneity": 12, "Developmental_Profiles": 10, "Caregiving": 3},
        "penalty": ["fnirs method", "toolbox"],
        "next_link": "06 Dyadic Neural Organization",
    },
    {
        "key": "dyadic_neural",
        "title": "06 Dyadic Neural Organization",
        "question": "Why move from behavior to parent-child neural organization?",
        "claim": "Parent-child interaction can be studied as dyadic neural organization during naturalistic and structured interaction.",
        "must": [],
        "phrases": {
            "parent-child brain-to-brain": 16,
            "parent-child interbrain": 16,
            "interbrain synchrony": 12,
            "brain-to-brain synchrony": 12,
            "hyperscanning": 10,
            "fnirs": 8,
            "neural synchrony": 8,
            "mother-child": 5,
        },
        "clusters": {"E": 10, "C": 3},
        "domains": {"Interbrain_Synchrony": 12, "Neural_Calibration": 10, "Parent_Child_Interaction": 5},
        "penalty": ["granger causality"],
        "next_link": "07 Neural Directionality And Leadership",
    },
    {
        "key": "neural_directionality",
        "title": "07 Neural Directionality And Leadership",
        "question": "Why is synchrony not enough?",
        "claim": "Directionality and effective connectivity are needed to ask who leads, follows, or influences whom during interaction.",
        "must": [],
        "phrases": {
            "granger causality": 16,
            "effective connectivity": 14,
            "directionality": 12,
            "directional": 8,
            "information flow": 10,
            "leader": 8,
            "follower": 8,
            "leads": 6,
            "follows": 6,
        },
        "clusters": {"E": 10},
        "domains": {"Neural_Directionality": 12, "Neural_Calibration": 6, "Joint_Attention": 4},
        "penalty": ["parenting style"],
        "next_link": "08 Longitudinal Recalibration",
    },
    {
        "key": "longitudinal_recalibration",
        "title": "08 Longitudinal Recalibration",
        "question": "Why does the dissertation need a longitudinal/recalibration frame?",
        "claim": "Developmental calibration requires attention to change over time, not only concurrent associations.",
        "must": [],
        "phrases": {
            "longitudinal": 14,
            "prospective": 10,
            "developmental change": 10,
            "stability": 6,
            "trajectory": 8,
            "cascade": 8,
            "transactional": 8,
            "developmental cascade": 12,
        },
        "clusters": {"E2": 10, "A": 4, "C": 3},
        "domains": {"Longitudinal_Development": 12, "Transactional_Development": 7, "Developmental_Heterogeneity": 4},
        "penalty": ["cross-sectional"],
        "next_link": "09 Similar Study Designs",
    },
    {
        "key": "similar_study_design",
        "title": "09 Similar Study Designs",
        "question": "Have prior studies used a similar design?",
        "claim": "Prior work contains many partial design matches, but rarely integrates structured/free-play interaction, caregiving, joint attention, child performance, and neural directionality in one design.",
        "must": [],
        "phrases": {
            "parent-child": 8,
            "mother-child": 6,
            "joint attention": 8,
            "free play": 8,
            "structured": 6,
            "task performance": 7,
            "hyperscanning": 8,
            "fnirs": 6,
            "granger": 8,
            "leader": 5,
            "follower": 5,
        },
        "clusters": {"E": 8, "B": 5, "C": 5},
        "domains": {"Joint_Attention": 8, "Neural_Calibration": 8, "Parent_Child_Interaction": 8, "Interbrain_Synchrony": 7},
        "penalty": [],
        "next_link": "",
    },
]


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").lower()).strip()


def slugify(text: str, max_len: int = 90) -> str:
    text = re.sub(r"[^\w\s-]", "", str(text), flags=re.UNICODE)
    text = re.sub(r"\s+", "_", text.strip())
    text = re.sub(r"_+", "_", text)
    return text[:max_len].strip("_") or "Untitled"


def wiki_link(note_name: str) -> str:
    return f"[[{note_name}]]"


def clean_snippet(text: str, limit: int = 700) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text.replace("|", "\\|")[:limit]


def phrase_score(text: str, title: str, phrases: dict[str, int]) -> tuple[float, list[str]]:
    score = 0.0
    hits = []
    for phrase, weight in phrases.items():
        phrase_l = phrase.lower()
        n_body = text.count(phrase_l)
        n_title = title.count(phrase_l)
        if n_body or n_title:
            hits.append(phrase)
            score += min(n_body, 4) * weight
            score += n_title * weight * 1.8
    return score, hits


def title_key(title: str) -> str:
    title = norm(title)
    title = re.sub(r"[^a-z0-9 ]", " ", title)
    return re.sub(r"\s+", " ", title).strip()


def paper_key(row: pd.Series) -> str:
    doi = norm(row.get("doi", ""))
    if doi and doi != "nan":
        return "doi:" + doi
    return "title:" + title_key(row.get("title", ""))


def citation_score(value) -> float:
    try:
        v = float(value)
    except Exception:
        return 0.0
    if math.isnan(v) or v <= 0:
        return 0.0
    return min(math.log1p(v), 6.5)


def load_pdf_candidates() -> pd.DataFrame:
    claim = pd.read_csv(CLAIM_HITS)
    pdf = claim[claim["source_type"] == "PDF"].copy()
    pdf["title"] = pdf["title_or_file"].fillna("").astype(str)
    pdf["abstract"] = pdf["evidence_snippet"].fillna("").astype(str)
    pdf["combined_text"] = pdf["title"] + " " + pdf["abstract"]
    pdf["source_kind"] = "PDF"
    pdf["source_file"] = pdf["file"]
    pdf["local_file"] = pdf["file"]
    pdf["publication_year"] = pdf.get("year", "")
    pdf["times_cited_wos"] = 0
    return pdf


def load_ris_candidates() -> pd.DataFrame:
    ris = pd.read_csv(CLEAN_RIS)
    ris["title"] = ris["title"].fillna("").astype(str)
    ris["abstract"] = ris["abstract"].fillna("").astype(str)
    ris["combined_text"] = (
        ris["title"] + " " + ris["abstract"] + " " +
        ris["author_keywords"].fillna("").astype(str) + " " +
        ris["keywords_plus"].fillna("").astype(str)
    )
    ris["source_kind"] = "RIS"
    ris["source_file"] = ris["source_file"].fillna("").apply(lambda x: str(ROOT / "data/raw/ris" / x))
    ris["local_file"] = ""
    ris["priority"] = ""
    ris["domain"] = ris["subcluster"].fillna(ris["cluster"].fillna(""))
    return ris


def build_pdf_lookup(pdf: pd.DataFrame) -> dict[str, str]:
    lookup = {}
    for _, row in pdf.iterrows():
        title = str(row.get("title", ""))
        path = str(row.get("local_file", ""))
        key = title_key(title)
        if key and path:
            lookup[key] = path
    return lookup


def passes_argument_gate(arg_key: str, text: str) -> bool:
    if arg_key == "neural_directionality":
        neural_terms = ["granger", "effective connectivity", "directionality", "directional", "information flow"]
        neural_context = ["neural", "brain", "fnirs", "hyperscanning", "interbrain", "eeg", "fmri"]
        if any(term in text for term in neural_terms):
            return True
        return ("leader" in text or "follower" in text) and any(term in text for term in neural_context)
    if arg_key == "similar_study_design":
        dyad_terms = ["parent-child", "parent child", "mother-child", "mother child", "caregiver-child", "caregiver child"]
        design_terms = ["joint attention", "free play", "structured", "task", "performance", "fnirs", "hyperscanning", "interbrain"]
        return any(term in text for term in dyad_terms) and any(term in text for term in design_terms)
    if arg_key == "heterogeneity_localization":
        developmental_terms = ["child", "infant", "toddler", "development", "parent", "mother", "caregiving"]
        return any(term in text for term in developmental_terms)
    return True


def score_for_argument(df: pd.DataFrame, arg: dict, pdf_lookup: dict[str, str]) -> pd.DataFrame:
    rows = []
    for _, row in df.iterrows():
        title = norm(row.get("title", ""))
        text = norm(row.get("combined_text", ""))
        if any(must not in text for must in arg.get("must", [])):
            continue
        if not passes_argument_gate(arg["key"], text):
            continue
        score, hits = phrase_score(text, title, arg["phrases"])
        if score <= 0:
            continue
        cluster = str(row.get("cluster", ""))
        domain = str(row.get("domain", ""))
        source_kind = str(row.get("source_kind", ""))
        local_file = str(row.get("local_file", "") or "")
        if source_kind == "RIS" and not local_file:
            local_file = pdf_lookup.get(title_key(str(row.get("title", ""))), "")
        for cluster_prefix, weight in arg.get("clusters", {}).items():
            if cluster.startswith(cluster_prefix):
                score += weight
        for domain_name, weight in arg.get("domains", {}).items():
            if domain_name.lower() in domain.lower():
                score += weight
        if source_kind == "PDF":
            score += 10
        if local_file:
            score += 8
        priority = str(row.get("priority", ""))
        score += {"A_Must_Read": 8, "B_Important": 4, "C_Background": 1}.get(priority, 0)
        score += citation_score(row.get("times_cited_wos", 0)) * 1.5
        for bad in arg.get("penalty", []):
            if bad in text:
                score -= 8
        candidate_tier = "strong_ris_download_candidate"
        if source_kind == "PDF" or local_file:
            candidate_tier = "anchor_local_pdf" if score >= 30 else "local_support"
        elif score < 24:
            candidate_tier = "weak_ris_filler"
        out = row.to_dict()
        out.update({
            "argument_key": arg["key"],
            "argument_title": arg["title"],
            "argument_question": arg["question"],
            "argument_claim": arg["claim"],
            "score_v2": round(score, 3),
            "matched_terms": "; ".join(hits),
            "candidate_tier": candidate_tier,
            "local_file": local_file,
            "has_local_full_paper": "yes" if local_file else "not_confirmed",
            "snippet": clean_snippet(row.get("abstract", row.get("evidence_snippet", ""))),
        })
        rows.append(out)
    scored = pd.DataFrame(rows)
    if scored.empty:
        return scored
    scored["dedupe_key"] = scored.apply(paper_key, axis=1)
    scored = scored.sort_values(
        ["candidate_tier", "score_v2"],
        key=lambda s: s.map({"anchor_local_pdf": 0, "local_support": 1, "strong_ris_download_candidate": 2, "weak_ris_filler": 3}) if s.name == "candidate_tier" else s,
        ascending=[True, False],
    )
    deduped = []
    seen = set()
    for _, row in scored.iterrows():
        key = row["dedupe_key"]
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
        if len(deduped) >= 30:
            break
    return pd.DataFrame(deduped)


def build_seed_table() -> pd.DataFrame:
    pdf = load_pdf_candidates()
    ris = load_ris_candidates()
    all_candidates = pd.concat([pdf, ris], ignore_index=True, sort=False)
    pdf_lookup = build_pdf_lookup(pdf)
    records = []
    for arg in ARGUMENTS:
        scored = score_for_argument(all_candidates, arg, pdf_lookup)
        if scored.empty:
            continue
        # Keep 25 seeds, but label weak fillers so we can replace them manually.
        for rank, (_, row) in enumerate(scored.head(25).iterrows(), start=1):
            title = str(row.get("title", "") or row.get("title_or_file", ""))
            note_name = slugify(title)
            records.append({
                "argument_key": row["argument_key"],
                "argument_title": row["argument_title"],
                "rank": rank,
                "paper_note": note_name,
                "title": title,
                "source_type": row.get("source_kind", ""),
                "candidate_tier": row.get("candidate_tier", ""),
                "has_local_full_paper": row.get("has_local_full_paper", ""),
                "local_file": row.get("local_file", ""),
                "source_file": row.get("source_file", ""),
                "priority": row.get("priority", ""),
                "domain": row.get("domain", ""),
                "cluster": row.get("cluster", ""),
                "year": row.get("publication_year", row.get("year", "")),
                "journal": row.get("journal", ""),
                "doi": row.get("doi", ""),
                "times_cited_wos": row.get("times_cited_wos", ""),
                "score_v2": row.get("score_v2", ""),
                "matched_terms": row.get("matched_terms", ""),
                "selection_reason": f"{row.get('candidate_tier', '')}; matched: {row.get('matched_terms', '')}",
                "snippet": row.get("snippet", ""),
            })
    return pd.DataFrame(records)


def write_argument_notes(seed: pd.DataFrame) -> None:
    ARG_DIR.mkdir(parents=True, exist_ok=True)
    for idx, arg in enumerate(ARGUMENTS):
        df = seed[seed["argument_key"] == arg["key"]].copy()
        prev_link = ARGUMENTS[idx - 1]["title"] if idx > 0 else ""
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
            f"Next: {wiki_link(arg['next_link']) if arg['next_link'] else 'End of literature review chain'}",
            "",
            "## Seed Papers V2",
            "",
            "| Rank | Paper | Tier | Source | Full paper | Why selected |",
            "|---:|---|---|---|---|---|",
        ]
        for _, row in df.iterrows():
            lines.append(
                f"| {int(row['rank'])} | {wiki_link(row['paper_note'])} | "
                f"{row.get('candidate_tier','')} | {row.get('source_type','')} / {row.get('domain','')} | "
                f"{row.get('has_local_full_paper','')} | {row.get('matched_terms','')} |"
            )
        lines.extend([
            "",
            "## How This Section Should Argue",
            "",
            "- Start with `anchor_local_pdf` papers when drafting because they are immediately readable.",
            "- Treat `strong_ris_download_candidate` papers as likely better citations that need full-paper retrieval.",
            "- Replace `weak_ris_filler` items before final writing unless they become necessary after full-text checking.",
            "",
            "## RIS-Only / Needs Full Paper Check",
            "",
        ])
        missing = df[df["has_local_full_paper"] != "yes"]
        if missing.empty:
            lines.append("All V2 seed items in this argument currently have local PDF-backed evidence.")
        else:
            for _, row in missing.iterrows():
                lines.append(f"- {row['title']} | DOI: `{row.get('doi','')}` | source: `{row.get('source_file','')}`")
        (ARG_DIR / f"{arg['title']}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_paper_notes(seed: pd.DataFrame) -> None:
    PAPER_DIR.mkdir(parents=True, exist_ok=True)
    for note_name, group in seed.groupby("paper_note", sort=False):
        first = group.iloc[0]
        args = [wiki_link(t) for t in group["argument_title"].drop_duplicates()]
        safe_title = str(first["title"]).replace('"', "'")
        safe_doi = str(first.get("doi", "")).replace('"', "'")
        lines = [
            "---",
            f"title: \"{safe_title}\"",
            f"source_type: {first.get('source_type','')}",
            f"candidate_tier: {first.get('candidate_tier','')}",
            f"has_local_full_paper: {first.get('has_local_full_paper','')}",
            f"doi: \"{safe_doi}\"",
            "---",
            f"# {first['title']}",
            "",
            f"Arguments: {', '.join(args)}",
            "",
            f"Source: `{first.get('source_type','')}`",
            f"Tier: `{first.get('candidate_tier','')}`",
            f"Year/journal: `{first.get('year','')}` / `{first.get('journal','')}`",
            f"DOI: `{first.get('doi','')}`",
            f"Local full paper: `{first.get('has_local_full_paper','')}`",
            "",
            "## Local Or Source File",
            "",
            f"`{first.get('local_file','') or first.get('source_file','')}`",
            "",
            "## Why It Is In The Map",
            "",
        ]
        for _, row in group.iterrows():
            lines.append(f"- {wiki_link(row['argument_title'])}: {row.get('selection_reason','')}; score `{row.get('score_v2','')}`.")
        snippets = [str(x).strip() for x in group["snippet"].tolist() if str(x).strip()]
        if snippets:
            lines.extend(["", "## Evidence Snippets", ""])
            for snip in snippets[:3]:
                lines.append(f"- {clean_snippet(snip, 500)}")
        (PAPER_DIR / f"{note_name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_index(seed: pd.DataFrame) -> None:
    lines = [
        "# Literature Review Argument Index",
        "",
        "This V2 map links each dissertation literature-review argument to candidate papers from both local PDFs and the clean RIS corpus.",
        "",
        "Important: `anchor_local_pdf` means readable now; `strong_ris_download_candidate` means likely valuable but needs full-paper retrieval before final citation.",
        "",
        "## Argument Chain",
        "",
    ]
    for arg in ARGUMENTS:
        sub = seed[seed["argument_key"] == arg["key"]]
        n = len(sub)
        n_pdf = (sub["has_local_full_paper"] == "yes").sum()
        n_ris = (sub["has_local_full_paper"] != "yes").sum()
        lines.append(f"- {wiki_link(arg['title'])} ({n} seeds; {n_pdf} local/full-paper candidates; {n_ris} RIS-only)")
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
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    seed = build_seed_table()
    seed.to_csv(SEED_CSV, index=False)
    missing = seed[seed["has_local_full_paper"] != "yes"].copy()
    missing.to_csv(MISSING_CSV, index=False)
    write_argument_notes(seed)
    write_paper_notes(seed)
    write_index(seed)
    print(f"Wrote {SEED_CSV}")
    print(f"Wrote {MISSING_CSV}")
    print(f"Wrote argument notes to {ARG_DIR}")
    print(f"Wrote paper notes to {PAPER_DIR}")
    print(seed.groupby("argument_title").agg(
        seeds=("title", "count"),
        local_or_matched=("has_local_full_paper", lambda s: (s == "yes").sum()),
        ris_only=("has_local_full_paper", lambda s: (s != "yes").sum()),
        anchors=("candidate_tier", lambda s: s.isin(["anchor_local_pdf", "local_support"]).sum()),
    ).to_string())


if __name__ == "__main__":
    main()
