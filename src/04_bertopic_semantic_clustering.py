"""Run BERTopic semantic clustering on the cleaned TDSEM RIS corpus.

This stage requires optional topic-modeling dependencies:

    bertopic sentence-transformers umap-learn hdbscan

It writes paper-topic assignments, topic keywords, topic sizes,
representative papers, topic coherence scores, a topic similarity matrix,
and simple presentation figures.
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity


DEFAULT_INPUT = Path("data/processed/tdsem_ris_corpus_clean.csv")
DEFAULT_OUTPUT_DIR = Path("outputs/topics")
DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
RANDOM_SEED = 123


def require_bertopic_dependencies() -> dict[str, object]:
    """Import BERTopic dependencies with a clear error message."""
    missing = []
    modules = {}
    for import_name, package_name in [
        ("bertopic", "bertopic"),
        ("sentence_transformers", "sentence-transformers"),
        ("umap", "umap-learn"),
        ("hdbscan", "hdbscan"),
    ]:
        try:
            modules[import_name] = __import__(import_name)
        except ImportError:
            missing.append(package_name)

    if missing:
        joined = " ".join(missing)
        raise RuntimeError(
            "Missing BERTopic dependencies. Install them in your Python environment with:\n"
            f"python3 -m pip install {joined}\n"
            "Then rerun this script."
        )
    return modules


def clean_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def load_corpus(input_path: Path, min_chars: int, deduplicate_doi: bool) -> pd.DataFrame:
    if not input_path.exists():
        raise FileNotFoundError(f"Input corpus does not exist: {input_path}")
    df = pd.read_csv(input_path)
    if "combined_text" not in df.columns:
        raise ValueError("Input corpus must contain combined_text.")

    df["combined_text"] = df["combined_text"].map(clean_text)
    df = df[df["combined_text"].str.len() >= min_chars].copy()
    if deduplicate_doi and "doi" in df.columns:
        cited = pd.to_numeric(df.get("total_times_cited"), errors="coerce").fillna(0)
        df = df.assign(_citation_sort=cited)
        has_doi = df["doi"].fillna("").astype(str).str.strip().ne("")
        deduped = df[has_doi].sort_values("_citation_sort", ascending=False).drop_duplicates("doi")
        no_doi = df[~has_doi]
        df = pd.concat([deduped, no_doi], ignore_index=True).drop(columns="_citation_sort")
    return df.reset_index(drop=True)


def fit_bertopic(
    docs: Sequence[str],
    model_name: str,
    local_files_only: bool,
    clusterer: str,
    n_topics: int,
    min_topic_size: int,
    n_neighbors: int,
    min_df: int,
    calculate_probabilities: bool,
):
    deps = require_bertopic_dependencies()
    BERTopic = deps["bertopic"].BERTopic
    SentenceTransformer = deps["sentence_transformers"].SentenceTransformer
    UMAP = deps["umap"].UMAP

    from sklearn.feature_extraction.text import CountVectorizer
    from sklearn.cluster import KMeans

    embedding_model = SentenceTransformer(model_name, local_files_only=local_files_only)
    umap_model = UMAP(
        n_neighbors=n_neighbors,
        n_components=5,
        min_dist=0.0,
        metric="cosine",
        random_state=RANDOM_SEED,
    )
    if clusterer == "hdbscan":
        HDBSCAN = deps["hdbscan"].HDBSCAN
        cluster_model = HDBSCAN(
            min_cluster_size=min_topic_size,
            metric="euclidean",
            cluster_selection_method="eom",
            prediction_data=True,
        )
    elif clusterer == "kmeans":
        if n_topics < 2:
            raise ValueError("--n-topics must be at least 2 when --clusterer kmeans is used.")
        cluster_model = KMeans(n_clusters=n_topics, random_state=RANDOM_SEED, n_init="auto")
        calculate_probabilities = False
    else:
        raise ValueError(f"Unknown clusterer: {clusterer}")

    vectorizer_model = CountVectorizer(
        stop_words="english",
        min_df=min_df,
        ngram_range=(1, 2),
    )
    topic_model = BERTopic(
        embedding_model=embedding_model,
        umap_model=umap_model,
        hdbscan_model=cluster_model,
        vectorizer_model=vectorizer_model,
        calculate_probabilities=calculate_probabilities,
        verbose=True,
    )
    topics, probabilities = topic_model.fit_transform(list(docs))
    return topic_model, topics, probabilities


def tokenize(text: str) -> set[str]:
    tokens = re.findall(r"[a-z][a-z\-]{2,}", text.lower())
    stop = {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "from",
        "were",
        "are",
        "was",
        "children",
        "child",
        "development",
        "study",
        "studies",
    }
    return {token for token in tokens if token not in stop}


def topic_words(topic_model, topic: int, top_n: int) -> list[str]:
    words = topic_model.get_topic(topic) or []
    return [word for word, _ in words[:top_n]]


def calculate_npmi_coherence(docs: Sequence[str], words: Sequence[str]) -> float:
    """Calculate a simple document-level NPMI coherence score."""
    words = [word.lower().replace(" ", "_") for word in words if word]
    if len(words) < 2:
        return np.nan

    doc_sets = []
    for doc in docs:
        token_set = tokenize(doc)
        phrase_tokens = set(token_set)
        lower_doc = doc.lower()
        for word in words:
            if "_" in word and word.replace("_", " ") in lower_doc:
                phrase_tokens.add(word)
        doc_sets.append(phrase_tokens)

    n_docs = max(len(doc_sets), 1)
    df = Counter()
    cooc = Counter()
    for token_set in doc_sets:
        present = [word for word in words if word in token_set]
        for word in present:
            df[word] += 1
        for i, word_i in enumerate(present):
            for word_j in present[i + 1 :]:
                cooc[tuple(sorted((word_i, word_j)))] += 1

    scores = []
    for i, word_i in enumerate(words):
        for word_j in words[i + 1 :]:
            pair = tuple(sorted((word_i, word_j)))
            p_i = df[word_i] / n_docs
            p_j = df[word_j] / n_docs
            p_ij = cooc[pair] / n_docs
            if p_i == 0 or p_j == 0 or p_ij == 0:
                continue
            pmi = math.log(p_ij / (p_i * p_j))
            npmi = pmi / (-math.log(p_ij))
            scores.append(npmi)
    return float(np.mean(scores)) if scores else np.nan


def create_topic_keywords(topic_model, topic_info: pd.DataFrame, top_n: int) -> pd.DataFrame:
    rows = []
    for topic in topic_info["Topic"]:
        if int(topic) == -1:
            continue
        words = topic_model.get_topic(int(topic)) or []
        for rank, (word, weight) in enumerate(words[:top_n], start=1):
            rows.append({"topic_id": int(topic), "rank": rank, "keyword": word, "weight": weight})
    return pd.DataFrame(rows)


def create_topic_coherence(
    df: pd.DataFrame,
    topics: Sequence[int],
    topic_model,
    topic_info: pd.DataFrame,
    top_n: int,
) -> pd.DataFrame:
    docs_by_topic: dict[int, list[str]] = defaultdict(list)
    for doc, topic in zip(df["combined_text"], topics):
        if int(topic) != -1:
            docs_by_topic[int(topic)].append(doc)

    rows = []
    for topic in topic_info["Topic"]:
        topic = int(topic)
        if topic == -1:
            continue
        words = topic_words(topic_model, topic, top_n)
        docs = docs_by_topic.get(topic, [])
        rows.append(
            {
                "topic_id": topic,
                "topic_size": len(docs),
                "top_words": "; ".join(words),
                "npmi_coherence": calculate_npmi_coherence(docs, words),
            }
        )
    return pd.DataFrame(rows).sort_values("topic_id")


def create_topic_similarity_matrix(topic_keywords: pd.DataFrame) -> pd.DataFrame:
    """Create topic similarity using weighted top-keyword vectors."""
    if topic_keywords.empty:
        return pd.DataFrame()

    topics = sorted(topic_keywords["topic_id"].unique())
    vocab = sorted(topic_keywords["keyword"].unique())
    vocab_index = {word: index for index, word in enumerate(vocab)}
    matrix = np.zeros((len(topics), len(vocab)))
    topic_index = {topic: index for index, topic in enumerate(topics)}
    for _, row in topic_keywords.iterrows():
        matrix[topic_index[row["topic_id"]], vocab_index[row["keyword"]]] = row["weight"]
    similarity = cosine_similarity(matrix)
    return pd.DataFrame(similarity, index=topics, columns=topics).rename_axis("topic_id")


def create_assignments(df: pd.DataFrame, topics: Sequence[int], probabilities) -> pd.DataFrame:
    assignments = df.copy()
    assignments["topic_id"] = topics
    if probabilities is not None:
        try:
            assignments["topic_probability"] = np.max(probabilities, axis=1)
        except Exception:
            assignments["topic_probability"] = np.nan
    else:
        assignments["topic_probability"] = np.nan
    return assignments


def create_representative_papers(assignments: pd.DataFrame, n: int) -> pd.DataFrame:
    cited = pd.to_numeric(assignments.get("total_times_cited"), errors="coerce").fillna(0)
    ranked = assignments.assign(_cited=cited)
    ranked = ranked[ranked["topic_id"] != -1]
    keep = [
        "topic_id",
        "record_id",
        "cluster",
        "subcluster",
        "title",
        "authors",
        "publication_year",
        "journal",
        "doi",
        "total_times_cited",
        "abstract",
    ]
    return (
        ranked.sort_values(["topic_id", "_cited"], ascending=[True, False])
        .groupby("topic_id")
        .head(n)
        .loc[:, [column for column in keep if column in ranked.columns]]
    )


def save_visualizations(topic_model, output_dir: Path) -> None:
    viz_dir = output_dir / "visualizations"
    viz_dir.mkdir(parents=True, exist_ok=True)
    visualizers = {
        "topics.html": topic_model.visualize_topics,
        "barchart.html": topic_model.visualize_barchart,
        "hierarchy.html": topic_model.visualize_hierarchy,
    }
    for filename, func in visualizers.items():
        try:
            fig = func()
            fig.write_html(viz_dir / filename)
        except Exception as exc:
            (viz_dir / f"{filename}.error.txt").write_text(str(exc), encoding="utf-8")


def save_presentation_figures(
    topic_info: pd.DataFrame,
    topic_coherence: pd.DataFrame,
    topic_similarity: pd.DataFrame,
    output_dir: Path,
) -> None:
    """Save static PNG figures for slides and dissertation progress meetings."""
    import matplotlib.pyplot as plt

    fig_dir = output_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    topics = topic_info[topic_info["Topic"] != -1].copy()
    topics = topics.sort_values("Count", ascending=False).head(25)
    if not topics.empty:
        labels = [f"{int(row.Topic)}: {str(row.Name)[:45]}" for row in topics.itertuples()]
        plt.figure(figsize=(12, max(6, len(topics) * 0.32)))
        plt.barh(labels[::-1], topics["Count"].to_numpy()[::-1], color="#356a8a")
        plt.xlabel("Number of papers")
        plt.title("Largest BERTopic Topics")
        plt.tight_layout()
        plt.savefig(fig_dir / "topic_sizes_top25.png", dpi=220)
        plt.close()

    coherence = topic_coherence.dropna(subset=["npmi_coherence"]).sort_values(
        "npmi_coherence", ascending=False
    ).head(25)
    if not coherence.empty:
        labels = [f"{int(row.topic_id)}: {str(row.top_words)[:55]}" for row in coherence.itertuples()]
        plt.figure(figsize=(12, max(6, len(coherence) * 0.32)))
        plt.barh(labels[::-1], coherence["npmi_coherence"].to_numpy()[::-1], color="#5d7f3f")
        plt.xlabel("NPMI coherence")
        plt.title("Most Coherent Topics")
        plt.tight_layout()
        plt.savefig(fig_dir / "topic_coherence_top25.png", dpi=220)
        plt.close()

    if not topic_similarity.empty:
        matrix = topic_similarity.copy()
        if len(matrix) > 35:
            matrix = matrix.iloc[:35, :35]
        plt.figure(figsize=(10, 9))
        plt.imshow(matrix.to_numpy(), aspect="auto", cmap="viridis")
        plt.colorbar(label="Cosine similarity")
        plt.xticks(range(len(matrix.columns)), matrix.columns, rotation=90, fontsize=7)
        plt.yticks(range(len(matrix.index)), matrix.index, fontsize=7)
        plt.title("Topic Similarity Matrix")
        plt.tight_layout()
        plt.savefig(fig_dir / "topic_similarity_matrix.png", dpi=220)
        plt.close()


def save_topic_model(topic_model, output_dir: Path, model_name: str) -> None:
    model_dir = output_dir / "bertopic_model"
    try:
        topic_model.save(
            str(model_dir),
            serialization="safetensors",
            save_ctfidf=True,
            save_embedding_model=model_name,
        )
    except TypeError:
        topic_model.save(str(model_dir))
    except Exception as exc:
        (output_dir / "bertopic_model_save_error.txt").write_text(str(exc), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run BERTopic on the TDSEM RIS corpus.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--clusterer", choices=["hdbscan", "kmeans"], default="hdbscan")
    parser.add_argument("--n-topics", type=int, default=30, help="Fixed topic count for --clusterer kmeans.")
    parser.add_argument("--min-chars", type=int, default=80)
    parser.add_argument("--min-topic-size", type=int, default=35)
    parser.add_argument("--n-neighbors", type=int, default=15)
    parser.add_argument("--min-df", type=int, default=5)
    parser.add_argument("--top-n-words", type=int, default=12)
    parser.add_argument("--representative-n", type=int, default=8)
    parser.add_argument("--sample-size", type=int, default=0, help="Optional sample size for pilot runs.")
    parser.add_argument("--deduplicate-doi", action="store_true")
    parser.add_argument("--calculate-probabilities", action="store_true")
    parser.add_argument("--save-model", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    try:
        df = load_corpus(args.input, args.min_chars, args.deduplicate_doi)
        if args.sample_size and args.sample_size < len(df):
            df = df.sample(args.sample_size, random_state=RANDOM_SEED).reset_index(drop=True)
        topic_model, topics, probabilities = fit_bertopic(
            docs=df["combined_text"].tolist(),
            model_name=args.model_name,
            local_files_only=args.local_files_only,
            clusterer=args.clusterer,
            n_topics=args.n_topics,
            min_topic_size=args.min_topic_size,
            n_neighbors=args.n_neighbors,
            min_df=args.min_df,
            calculate_probabilities=args.calculate_probabilities,
        )
        topic_info = topic_model.get_topic_info()
        topic_keywords = create_topic_keywords(topic_model, topic_info, args.top_n_words)
        topic_coherence = create_topic_coherence(
            df, topics, topic_model, topic_info, args.top_n_words
        )
        topic_similarity = create_topic_similarity_matrix(topic_keywords)
        assignments = create_assignments(df, topics, probabilities)
        representatives = create_representative_papers(assignments, args.representative_n)

        assignments.to_csv(args.output_dir / "paper_topic_assignments.csv", index=False)
        topic_info.to_csv(args.output_dir / "topic_sizes.csv", index=False)
        topic_keywords.to_csv(args.output_dir / "topic_keywords.csv", index=False)
        topic_coherence.to_csv(args.output_dir / "topic_coherence.csv", index=False)
        topic_similarity.to_csv(args.output_dir / "topic_similarity_matrix.csv")
        representatives.to_csv(args.output_dir / "representative_papers.csv", index=False)
        save_visualizations(topic_model, args.output_dir)
        save_presentation_figures(topic_info, topic_coherence, topic_similarity, args.output_dir)
        if args.save_model:
            save_topic_model(topic_model, args.output_dir, args.model_name)

        print("\nBERTopic TDSEM Topic Model")
        print("--------------------------")
        print(f"Documents modeled: {len(df)}")
        print(f"Clusterer: {args.clusterer}")
        if args.clusterer == "kmeans":
            print(f"Fixed k topics requested: {args.n_topics}")
        print(f"Topics found, including outlier topic -1: {len(topic_info)}")
        print(f"Outputs saved to: {args.output_dir}")
        print()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
