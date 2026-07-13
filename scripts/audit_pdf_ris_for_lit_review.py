from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
from pypdf import PdfReader


ROOT = Path("/Users/janet/Documents/TDSEM Developmental Calibration Research")
PDF_ROOT = Path("/Users/janet/Desktop/TDSEM_Organized_Readings")
RIS_ROOT = ROOT / "data/raw/ris"
OUT_DIR = ROOT / "outputs/literature_pdf_ris_audit"


CLAIMS = {
    "caregiving_foundation": {
        "label": "Responsive caregiving/scaffolding is a strong developmental context",
        "keywords": [
            "parental sensitivity", "maternal sensitivity", "responsive parenting",
            "responsiveness", "scaffolding", "parent-child interaction",
            "caregiver sensitivity", "sensitive caregiving", "emotional availability",
            "mutuality", "synchrony", "teaching", "tutoring",
        ],
    },
    "child_agency": {
        "label": "Children actively shape interaction rather than passively receive caregiving",
        "keywords": [
            "child agency", "child effects", "child-led", "child led",
            "bidirectional", "transactional", "reciprocal", "child-to-parent",
            "initiative", "initiating", "follow the leader", "who leads",
        ],
    },
    "joint_attention": {
        "label": "Joint attention is an early social-learning marker/mechanism",
        "keywords": [
            "joint attention", "shared attention", "social attention",
            "social learning", "early social communication", "ESCS",
        ],
    },
    "rja_ija_distinction": {
        "label": "RJA and IJA are distinct developmental processes",
        "keywords": [
            "responding to joint attention", "response to joint attention", "RJA",
            "initiating joint attention", "initiation of joint attention", "IJA",
            "joint attention bids", "following joint attention",
        ],
    },
    "heterogeneity_localization": {
        "label": "Developmental effects are heterogeneous/nonlinear/localized",
        "keywords": [
            "heterogeneity", "individual differences", "moderator", "moderation",
            "nonlinear", "non-linear", "threshold", "trajectory", "trajectories",
            "profile", "state space", "latent class", "differential", "context-dependent",
        ],
    },
    "dyadic_neural": {
        "label": "Parent-child interaction can be studied as dyadic neural organization",
        "keywords": [
            "hyperscanning", "interbrain", "inter-brain", "brain-to-brain",
            "neural synchrony", "fNIRS", "functional near-infrared",
            "parent-child neural", "dyadic neural",
        ],
    },
    "neural_directionality": {
        "label": "Directionality/effective connectivity is needed to study influence/leadership",
        "keywords": [
            "granger", "effective connectivity", "directionality", "directional",
            "information flow", "causal", "causality", "leader", "follower",
            "who leads", "who follows", "leadership",
        ],
    },
    "longitudinal_recalibration": {
        "label": "Developmental calibration/recalibration requires longitudinal change",
        "keywords": [
            "longitudinal", "prospective", "developmental change", "change over time",
            "stability", "developmental trajectories", "cascade", "recalibration",
            "developmental movement",
        ],
    },
}

COUNTER_TERMS = [
    "inconsistent", "mixed", "null", "not significant", "non-significant",
    "weak", "limited", "varied", "heterogeneous", "context", "risk",
    "maladaptive", "unclear", "unknown", "gap", "less is known",
    "remains unclear", "not yet clear",
]


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def priority_from_path(path: Path) -> str:
    rel = path.relative_to(PDF_ROOT)
    return rel.parts[0] if rel.parts else ""


def domain_from_path(path: Path) -> str:
    rel = path.relative_to(PDF_ROOT)
    return rel.parts[1] if len(rel.parts) > 1 else ""


def extract_pdf_text(path: Path, max_pages: int = 8) -> tuple[str, str]:
    try:
        reader = PdfReader(str(path))
        parts = []
        for page in reader.pages[:max_pages]:
            try:
                parts.append(page.extract_text() or "")
            except Exception:
                continue
        text = norm(" ".join(parts))
        return text, ""
    except Exception as exc:
        return "", f"{type(exc).__name__}: {exc}"


def score_claims(text: str) -> dict[str, int]:
    low = text.lower()
    scores = {}
    for key, spec in CLAIMS.items():
        score = 0
        for kw in spec["keywords"]:
            score += low.count(kw.lower())
        scores[key] = score
    return scores


def best_snippet(text: str, keywords: list[str], width: int = 420) -> str:
    low = text.lower()
    hits = [(low.find(kw.lower()), kw) for kw in keywords if low.find(kw.lower()) >= 0]
    if not hits:
        return ""
    idx, _ = min(hits, key=lambda x: x[0])
    start = max(0, idx - width // 2)
    end = min(len(text), idx + width // 2)
    return norm(text[start:end])


def stance_from_text(text: str) -> str:
    low = text.lower()
    if any(term in low for term in COUNTER_TERMS):
        return "support_with_tension_or_gap"
    return "mostly_support"


def audit_pdfs() -> list[dict[str, str]]:
    rows = []
    pdfs = sorted(PDF_ROOT.rglob("*.pdf"))
    for path in pdfs:
        pr = priority_from_path(path)
        dom = domain_from_path(path)
        include = pr in {"A_Must_Read", "B_Important"} or dom in {
            "Neural_Directionality", "Joint_Attention", "Transactional_Development",
            "Developmental_Heterogeneity",
        }
        if not include:
            continue
        text, err = extract_pdf_text(path)
        scores = score_claims(text)
        for claim, score in scores.items():
            if score <= 0:
                continue
            snippet = best_snippet(text, CLAIMS[claim]["keywords"])
            rows.append({
                "source_type": "PDF",
                "priority": pr,
                "domain": dom,
                "file": str(path),
                "title_or_file": path.stem,
                "claim_key": claim,
                "claim_label": CLAIMS[claim]["label"],
                "keyword_score": score,
                "stance_hint": stance_from_text(snippet or text[:2000]),
                "evidence_snippet": snippet[:700],
                "extraction_error": err,
            })
    return rows


def parse_ris_file(path: Path) -> list[dict[str, str]]:
    records = []
    current: dict[str, list[str]] = defaultdict(list)
    last_tag = None
    for raw in path.read_text(errors="ignore").splitlines():
        if re.match(r"^[A-Z0-9]{2}  - ", raw):
            tag, value = raw[:2], raw[6:]
            if tag == "ER":
                if current:
                    records.append({k: " ".join(v) for k, v in current.items()})
                current = defaultdict(list)
                last_tag = None
            else:
                current[tag].append(value.strip())
                last_tag = tag
        elif raw.startswith("      ") and last_tag:
            current[last_tag].append(raw.strip())
    if current:
        records.append({k: " ".join(v) for k, v in current.items()})
    for rec in records:
        rec["source_file"] = str(path)
    return records


def audit_ris() -> list[dict[str, str]]:
    rows = []
    for path in sorted(RIS_ROOT.glob("*.ris")):
        for rec in parse_ris_file(path):
            title = rec.get("TI") or rec.get("T1") or ""
            abstract = rec.get("AB") or rec.get("N2") or ""
            keywords = " ".join([rec.get("KW", ""), rec.get("N1", "")])
            text = norm(" ".join([title, abstract, keywords]))
            if not text:
                continue
            scores = score_claims(text)
            for claim, score in scores.items():
                if score <= 0:
                    continue
                rows.append({
                    "source_type": "RIS",
                    "priority": "",
                    "domain": Path(path).stem,
                    "file": str(path),
                    "title_or_file": title,
                    "year": rec.get("PY", ""),
                    "authors": rec.get("AU", ""),
                    "journal": rec.get("JO") or rec.get("T2", ""),
                    "doi": rec.get("DO", ""),
                    "claim_key": claim,
                    "claim_label": CLAIMS[claim]["label"],
                    "keyword_score": score,
                    "stance_hint": stance_from_text(text),
                    "evidence_snippet": best_snippet(text, CLAIMS[claim]["keywords"])[:700],
                    "extraction_error": "",
                })
    return rows


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = audit_pdfs() + audit_ris()
    out_csv = OUT_DIR / "pdf_ris_claim_hits.csv"
    fieldnames = [
        "source_type", "priority", "domain", "file", "title_or_file", "year",
        "authors", "journal", "doi", "claim_key", "claim_label",
        "keyword_score", "stance_hint", "evidence_snippet", "extraction_error",
    ]
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    df = pd.DataFrame(rows)
    if df.empty:
        print("No rows generated.")
        return
    summary = (
        df.groupby(["claim_key", "claim_label", "source_type", "stance_hint"])
        .size()
        .reset_index(name="n_hits")
        .sort_values(["claim_key", "source_type", "stance_hint"])
    )
    summary.to_csv(OUT_DIR / "claim_hit_summary.csv", index=False)

    top = (
        df.sort_values(["claim_key", "keyword_score"], ascending=[True, False])
        .groupby("claim_key")
        .head(12)
    )
    top.to_csv(OUT_DIR / "top_sources_by_claim.csv", index=False)

    print(f"Wrote {out_csv}")
    print(f"Wrote {OUT_DIR / 'claim_hit_summary.csv'}")
    print(f"Wrote {OUT_DIR / 'top_sources_by_claim.csv'}")
    print(f"Rows: {len(df)} | PDFs/RIS with claim hits: {df['file'].nunique()}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
