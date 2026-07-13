# First-Person-Egocentric_Visual_Data_Preprocessing

Research pipeline and literature-method collection for first-person/egocentric visual data preprocessing, cloud classification, and developmental calibration research.

This repository contains a reproducible Python pipeline for a doctoral dissertation literature review. The project imports Web of Science `savedrecs.txt` exports, extracts bibliographic metadata, prepares text for BERT/BERTopic clustering, and supports human-in-the-loop evidence mapping for developmental psychology literature.

The pipeline supports a systematic review and evidence map, not a meta-analysis.

## Repository Structure

```text
data/
  raw/                 # Web of Science exports; never edit or overwrite
  processed/           # Cleaned metadata tables
docs/                  # Protocol and methodological documentation
outputs/
  figures/             # Topic visualizations and plots
  tables/              # Bibliometric, coding, and evidence-map CSVs
src/                   # Pipeline scripts
tests/                 # Future parser and pipeline tests
```

## Method Collections

- [Egocentric First-Person Video: Literature Review, Trends, and Pipeline Protocol](docs/egocentric_first_person_video_pipeline_review.md) collects datasets, benchmark papers, model families, cloud architecture patterns, and a standardized literature-review process for first-person video pipelines from AI/AR glasses and wearable cameras. It also frames how egocentric visual events can later be aligned with emotional, physiological, and developmental change.

## Pipeline Stages

### 1. Parse a Web of Science TXT export

Use this for plain-text `savedrecs.txt` exports:

```bash
python3 src/01_parse_wos.py \
  --input data/raw/savedrecs_clusterA.txt \
  --output data/processed/clusterA_clean.csv
```

The cleaned CSV includes title, abstract, author keywords, Keywords Plus, authors, publication year, journal, DOI, Web of Science categories, Times Cited, and a combined text field for later sentence-transformer embeddings.

### 2. Summarize bibliometrics

```bash
python3 src/02_bibliometric_summary.py \
  --input data/processed/clusterA_clean.csv \
  --output-dir outputs/tables
```

This creates paper counts by year, top cited papers, top journals, and missing-data reports.

### 3. Parse the current Web of Science RIS corpus

The current TDSEM corpus is stored as RIS exports in `data/raw/ris/`.

```bash
python3 src/03_parse_ris_corpus.py
```

Primary output:

- `data/processed/tdsem_ris_corpus_clean.csv`

Current parsed corpus size: 13,087 records.

### 4. Run BERTopic semantic clustering

Install optional topic-modeling dependencies first:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-topic-modeling.txt
```

Download the default MiniLM embedding model into the project cache:

```bash
HF_HOME=.cache/huggingface .venv/bin/python - <<'PY'
from sentence_transformers import SentenceTransformer
SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
PY
```

For a natural-density BERTopic solution, run:

```bash
HF_HOME=.cache/huggingface MPLCONFIGDIR=.cache/matplotlib \
.venv/bin/python src/04_bertopic_semantic_clustering.py \
  --deduplicate-doi \
  --min-topic-size 35 \
  --local-files-only \
  --save-model
```

For a fixed presentation-friendly number of topics, use KMeans with `--n-topics`:

```bash
HF_HOME=.cache/huggingface MPLCONFIGDIR=.cache/matplotlib \
.venv/bin/python src/04_bertopic_semantic_clustering.py \
  --clusterer kmeans \
  --n-topics 30 \
  --output-dir outputs/topics_k30 \
  --deduplicate-doi \
  --local-files-only \
  --save-model
```

This stage uses `sentence-transformers/all-MiniLM-L6-v2`, UMAP, HDBSCAN or KMeans, and BERTopic's c-TF-IDF topic representation. It writes paper-topic assignments, topic keywords, topic sizes, representative papers, topic coherence scores, a topic similarity matrix, interactive HTML visualizations, static PNG figures, and an optional saved BERTopic model.

Main adjustable parameters:

- `--clusterer hdbscan`: lets BERTopic discover the number of topics from density.
- `--clusterer kmeans --n-topics 30`: forces a fixed topic count for comparison or presentation.
- `--min-topic-size`: larger values produce fewer, broader HDBSCAN topics.
- `--n-neighbors`: adjusts UMAP's local/global structure tradeoff.
- `--min-df`: filters rare terms from c-TF-IDF topic labels.

### 5. Prepare evidence maps

```bash
python3 src/05_prepare_evidence_maps.py
```

To merge a specific topic model into the evidence map:

```bash
python3 src/05_prepare_evidence_maps.py \
  --topic-assignments outputs/topics_k30/paper_topic_assignments.csv \
  --output-dir outputs/evidence_maps_k30
```

This creates dissertation-oriented evidence-map tables in `outputs/evidence_maps/`, including:

- `paper_evidence_map.csv`
- `manual_coding_template.csv`
- `theory_by_method.csv`
- `theory_by_agency_marker.csv`
- `agency_by_caregiving_construct.csv`
- `theory_by_unresolved_gap.csv`
- `method_by_unresolved_gap.csv`
- `top100_relevance_weighted_cited.csv`

The evidence-map stage is transparent and rule-based. It classifies papers by theory, empirical method, child agency marker, caregiving/scaffolding construct, research-question type, extracted finding/gap quotes, unresolved gap, and dissertation relevance.

### 6. Classify BERTopic topics

After a topic model and topic-linked evidence map have been created, classify topics into dissertation-facing families:

```bash
MPLCONFIGDIR=.cache/matplotlib \
python3 src/06_classify_topics.py \
  --topic-dir outputs/topics_k30 \
  --evidence-map outputs/evidence_maps_k30/paper_evidence_map.csv \
  --output-dir outputs/topic_classification_k30
```

This creates:

- `topic_classification.csv`
- `topic_label_review_template.csv`
- `topic_family_summary.csv`
- `topic_priority_queue.csv`
- `figures/topic_family_paper_counts.png`
- `figures/topic_priority_tiers.png`

Topic classification is rule-based and reviewable. It translates empirical BERTopic clusters into higher-order topic families such as child agency and joint attention, caregiving/scaffolding, developmental pathways, neural calibration, physiological regulation, attachment, methods, and off-domain search noise.

### 7. Export the topic map to Obsidian

Create an Obsidian-ready Markdown map:

```bash
python3 src/07_export_obsidian_topic_map.py
```

Output folder:

- `obsidian/TDSEM_Topic_Map/`

Open `00_TDSEM_Topic_Map_Index.md` as the entry point. The export includes one index note, one note per topic family, one note per BERTopic topic, and embedded summary figures in `Assets/`.

## Dissertation Construct Focus

The evidence mapping is oriented around how child agency and caregiving jointly organize developmental functioning across behavioral, neural, and longitudinal timescales. In this project, initiating joint attention and responding to joint attention are treated as established markers of agency and responsiveness. Parenting scaffolding and emotional support are interpreted through Responsive Interactions for Learning and related parent-child interaction constructs.
