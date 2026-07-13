# TDSEM Project Recorder

This document is the running record for the Theory-Driven Systematic Evidence Mapping project. It links decisions, scripts, outputs, and search strings so each step can be checked later.

## Project Frame

Project title: Theory-Driven Systematic Evidence Mapping for Developmental Calibration Research.

Current dissertation argument: development is organized through dynamic relations between child agency and caregiving, producing heterogeneous developmental pathways across behavioral, neural, and longitudinal timescales.

Review type: systematic evidence map, not meta-analysis.

## Completed Steps

### 2026-06-22 - Web of Science Pilot Parser

Purpose: parse Web of Science `savedrecs.txt` exports.

Script:

- `src/01_parse_wos.py`

Key output:

- `data/processed/clusterA_clean.csv`

Verification:

- Parsed 500 WoS records from the initial joint-attention export.
- Missing abstracts: 0/500.
- Missing DOI: 29/500.

### 2026-06-22 - Bibliometric Summary

Purpose: summarize cleaned WoS metadata.

Script:

- `src/02_bibliometric_summary.py`

Outputs:

- `outputs/tables/bibliometric_summary.csv`
- `outputs/tables/top50_cited.csv`
- `outputs/tables/papers_by_year.csv`
- `outputs/tables/top_journals.csv`
- `outputs/tables/missing_data_report.csv`

### 2026-06-22 - Pilot Rule-Based Mapping

Purpose: create a standalone transparent pilot mapping script before BERT/BERTopic.

Script:

- `run_joint_attention_mapping.py`

Output folder:

- `output_joint_attention_mapping/`

Notes:

- Uses transparent keyword dictionaries.
- Does not use BERT or online APIs.
- Added readable fallback PNG plots and abstract quote evidence for developmental assumption coding.

### 2026-06-23 - Cluster A Search Decision

Cluster A name: Developmental Systems and Transactional Parent-Child Development.

Decision: use the relational developmental systems query as the master theory corpus because it captures theory-relevant empirical work that may not explicitly name developmental systems theory.

Updated Web of Science result count: 708 records.

Web of Science result set:

- https://webofscience.clarivate.cn/wos/woscc/summary/93d29d1f-c801-457f-92ac-af1ebe92cbf3-01baf025cc/relevance/1

Cluster A search string:

```text
TS=(
  "developmental systems theory"
  OR "transactional model"
  OR "transactional development"
  OR "dynamic systems theory"
  OR "child effects"
  OR "parent effects"
  OR "co-regulation"
  OR coregulation
  OR equifinality
  OR multifinality
)
AND TS=(
  "parent-child"
  OR "parent child"
  OR mother*
  OR maternal
  OR father*
  OR paternal
  OR caregiv*
)
AND TS=(
  child*
  OR infant*
  OR toddler*
  OR preschool*
)
```

### 2026-06-23 - Updated Web of Science Cluster Result Sets

Purpose: record the current retrieval plan for the expanded TDSEM literature corpus.

Cluster A - Relational Developmental Systems:

- Records: 708.
- Link: https://webofscience.clarivate.cn/wos/woscc/summary/93d29d1f-c801-457f-92ac-af1ebe92cbf3-01baf025cc/relevance/1
- Query focus: developmental systems theory, transactional/dynamic systems, child effects, parent effects, co-regulation, equifinality, and multifinality in parent/caregiver-child early development.

Cluster B - Child Agency:

- Records: 2,213.
- Link: https://webofscience.clarivate.cn/wos/woscc/summary/4634fe90-2dc1-441a-83e7-4a4d63a26078-01baf09116/relevance/1
- Query focus: child agency, active child, child effects, child-driven/child-led/child-initiated processes, child participation, social participation, shared intentionality, social engagement, and child-directed interaction in parent/caregiver-child early development.

Cluster B2 - Responding to Joint Attention:

- Records: 124.
- Link: https://webofscience.clarivate.cn/wos/woscc/summary/ac602b1a-4ec7-4f6c-9833-2fea9498cdb5-01baf1648a/relevance/1
- Query focus: responding to joint attention, response to joint attention, RJA, responding joint attention, and joint attention response, with developmental and outcome terms.

Cluster B2 companion - Initiating Joint Attention:

- Records: 97.
- Link: https://webofscience.clarivate.cn/wos/woscc/summary/a1d7823b-bb3c-4aa3-9634-ae3ce9f63da0-01baf19bcc/relevance/1
- Query focus: initiating to joint attention, initiating joint attention, IJA, and joint attention response, with developmental and outcome terms.

Cluster C - Responsive Caregiving and Observational Support:

- Records: 1,657.
- Link: https://webofscience.clarivate.cn/wos/woscc/summary/fe6f0b58-6768-4b09-9ea3-8214c284c864-01baf27d8d/relevance/1
- Query focus: responsive caregiving, parental/maternal/caregiver responsiveness, caregiver/parent/paternal sensitivity, scaffolding, guided participation, cognitive stimulation, learning support, responsive interaction, and observational parent-child interaction measurement.

Next retrieval step:

- Export each Web of Science result set as full-record text files into `data/raw/`.
- Suggested filenames: `savedrecs_clusterA_rds.txt`, `savedrecs_clusterB_child_agency.txt`, `savedrecs_clusterB2_rja.txt`, `savedrecs_clusterB2_ija.txt`, and `savedrecs_clusterC_caregiving.txt`.
- After export, rerun the parser and bibliometric scripts with cluster labels preserved.

### 2026-06-23 - Curated Reading Library Audit

Purpose: clean and audit the user's hand-curated reading folders before scaling TDSEM outward.

Input folders:

- `/Users/janet/Desktop/Study 1 Reading`
- `/Users/janet/Desktop/Study2 Readings`

Script:

- `run_literature_audit.py`

Outputs:

- `output_literature_audit/developmental_calibration_library.csv`
- `output_literature_audit/manual_library_review.csv`
- `output_literature_audit/extraction_report.csv`
- `output_literature_audit/duplicate_report.csv`

Verification:

- Files inventoried: 248.
- PDF files: 247.
- PDFs with extracted text: 245.
- Duplicate file hashes: 6.

### 2026-06-23 - Reading Folder Organization

Purpose: copy curated readings into an organized folder with citation-like filenames while leaving originals untouched.

Script:

- `run_reading_file_organizer.py`

Manifest:

- `output_literature_audit/file_rename_manifest.csv`

Organized copy folder:

- `/Users/janet/Desktop/TDSEM_Organized_Readings`

Filename pattern:

```text
LastName_Year_Source_Title.pdf
```

Status:

- 248 manifest rows processed.
- 0 final errors after existing-file guard.
- 53 high-confidence filename-pattern matches.
- 195 lower-confidence names copied and flagged as `Needs_Human_Check = True`.

### 2026-06-23 - Current Reading Coverage Assessment

Purpose: identify what the current seed library already covers and what searches should fill next.

Script:

- `run_reading_coverage_assessment.py`

Outputs:

- `output_literature_audit/coverage/current_reading_coverage_report.md`
- `output_literature_audit/coverage/coverage_by_tdsem_cluster.csv`
- `output_literature_audit/coverage/chapter_section_gap_table.csv`
- `output_literature_audit/coverage/top_readings_by_cluster.csv`

Key findings:

- Strong coverage: neural/longitudinal organization, caregiving/parent-child interaction, methodology/measurement.
- Moderate coverage: relational developmental systems, child agency/joint attention, heterogeneity/pathways.
- Major gaps: child agency, responding to joint attention, neural directionality.

### 2026-06-23 - Imported Dissertation Framework Note

Purpose: save a ChatGPT dissertation-project note locally so it can be referenced by the TDSEM workflow.

Saved note:

- `chatgpt_project_notes/developmental_calibration_framework_and_seven_studies.md`

Contents:

- central dissertation problem,
- developmental calibration framework,
- seven-study architecture,
- integrated conclusion linking child agency, caregiving support, neural organization, and developmental change.

### 2026-06-23 - Imported Literature Review Plan

Purpose: save a ChatGPT dissertation-project note outlining the planned literature review structure.

Saved note:

- `chatgpt_project_notes/literature_review_plan_developmental_calibration.md`

Contents:

- chapter-level literature review plan,
- theoretical progression from dynamic systems to child agency, caregiving, heterogeneity, neural organization, and longitudinal calibration,
- contradictions, methodological limitations, and research gaps motivating the dissertation.

## Current Search Strategy Implication

The current reading library is not balanced enough to define the whole dissertation corpus. It is strong for Studies 1-2 and neural calibration framing, but the next Web of Science searches should deliberately fill:

1. explicit child agency beyond joint attention,
2. responding to joint attention,
3. developmental heterogeneity, pathways, profiles, and landscapes,
4. neural directionality and effective connectivity,
5. explicit developmental systems and transactional theory.

Detailed search strings are maintained in:

- `docs/search_strategy.md`

Gap-filling Web of Science and Google Scholar keyword bundles are maintained in:

- `docs/gap_filling_search_keywords.md`

Chapter 1 theory-first search planning is maintained in:

- `docs/chapter1_dynamic_systems_search_plan.md`

### 2026-06-24 - Updated Web of Science Cluster D/E Result Sets

Purpose: record the next retrieval wave for heterogeneity, neural directionality, and longitudinal recalibration.

Cluster D - Heterogeneity, Pathways, and Profiles:

- Records: 2,392 after choosing Highly Cited Papers.
- Link: https://webofscience.clarivate.cn/wos/woscc/summary/2649ba67-b580-4e39-a25b-71bdd3734d90-01bb0afa23/relevance/1
- Query focus: developmental heterogeneity, developmental variability, individual differences, person-centered methods, latent profile/class analysis, trajectories/pathways, equifinality/multifinality, nonlinear development, state space/state space grid, growth mixture, developmental cascades, and differential susceptibility in parent/caregiver-child early development.

Cluster E1 - Neural Directionality:

- Records: 4,880.
- Link: https://webofscience.clarivate.cn/wos/woscc/summary/c3848f5d-9065-4786-aaea-23ceb580abca-01bb0e3a3d/relevance/1
- Query focus: effective connectivity, Granger causality, neural/directional connectivity, leader-follower dynamics, parent-child influence, brain-to-brain coupling, and interbrain/inter-brain directionality in parent/caregiver-child neural interaction literatures.

Cluster E2 - Longitudinal Recalibration:

- Records: more than 80,000.
- Link: https://webofscience.clarivate.cn/wos/woscc/summary/f345c928-bb99-4c8a-a5b2-d660c8ebea25-01bb0faf3f/relevance/1
- Sampling decision: download the top 1,000 records sorted by relevance.
- Query focus: developmental cascades, stability, change, continuity, transitions, reorganization, recalibration, pathways, trajectories, longitudinal follow-up, growth modeling, latent growth, and cross-lagged designs across parent/caregiver-child early development.

Next retrieval step:

- Export Cluster D, E1, and E2 from Web of Science as full-record text files into `data/raw/`.
- Suggested filenames: `savedrecs_clusterD_heterogeneity_highly_cited.txt`, `savedrecs_clusterE1_neural_directionality.txt`, and `savedrecs_clusterE2_longitudinal_recalibration_top1000.txt`.
- For Cluster E2, preserve the Web of Science sort order as relevance and document that the export is a relevance-ranked sample rather than the full result set.

### 2026-06-24 - Stored Web of Science RIS Exports

Purpose: store user-downloaded Web of Science RIS exports as raw source files for the TDSEM study corpus.

Stored folder:

- `data/raw/ris/`

Manifest:

- `data/raw/ris_manifest.csv`

Files stored: 18 RIS files.

Record-count audit:

- Cluster A: 708 records.
- Cluster B child agency: 2,213 records across three parts.
- Cluster B2 IJA: 97 records.
- Cluster B2 RJA: 124 records.
- Cluster C caregiving primary export: 1,658 records across two parts.
- Cluster C RIFL targeted export: 15 records.
- Cluster D heterogeneity/pathways/profiles: 2,392 records across three parts.
- Cluster E1 neural directionality: 3,880 records across four parts.
- Cluster E2 longitudinal recalibration: 2,000 records across two parts.

Audit flags:

- Cluster E1 was previously recorded as a 4,880-record search, but only 3,880 records are stored. If the full E1 corpus is intended, retrieve the missing 1,000-record part.
- Cluster E2 was previously planned as a top-1,000 relevance-ranked sample, but 2,000 records are stored. Confirm whether both parts should remain in the analytic corpus or whether Part 2 should be archived as overflow.

### 2026-06-24 - Parsed RIS Corpus Content

Purpose: parse the stored RIS source files into a readable corpus table for screening, bibliometric audit, and later semantic mapping.

Script:

- `src/03_parse_ris_corpus.py`

Primary output:

- `data/processed/tdsem_ris_corpus_clean.csv`

Audit outputs:

- `outputs/tables/ris_cluster_summary.csv`
- `outputs/tables/ris_duplicate_doi_report.csv`
- `outputs/tables/ris_top_cited_by_cluster.csv`
- `outputs/tables/ris_keyword_frequency_by_cluster.csv`
- `outputs/tables/ris_content_sample_by_cluster.csv`

Verification:

- Parsed records: 13,087.
- Missing abstracts: 374 (2.9%).
- Missing DOI: 482 (3.7%).
- Records sharing a DOI with another record: 1,003.

Records by cluster/subcluster:

- Cluster A relational developmental systems: 708.
- Cluster B child agency: 2,213.
- Cluster B2 initiating joint attention: 97.
- Cluster B2 responding to joint attention: 124.
- Cluster C caregiving and observational support: 1,658.
- Cluster C RIFL: 15.
- Cluster D heterogeneity/pathways/profiles: 2,392.
- Cluster E1 neural directionality: 3,880.
- Cluster E2 longitudinal recalibration: 2,000.

Notes:

- The cleaned table includes title, abstract, keywords, authors, year, journal, DOI, Web of Science accession, citation-count fields parsed from RIS notes, source file, subcluster, and combined text.
- The duplicate DOI report should be used before creating a final analytic corpus, because overlap across conceptual clusters is expected and theoretically useful but should not be double-counted in corpus-level summaries.
- A copy of all 18 RIS source files and parsed metadata outputs was saved into `/Users/janet/Desktop/TDSEM_Organized_Readings/WOS_Citations/`. Parsed CSV outputs were stored in `/Users/janet/Desktop/TDSEM_Organized_Readings/WOS_Citations/Parsed_Metadata/`.

### 2026-06-26 - Construct Language Patch for RIFL and BERT Mapping

Purpose: refine the core construct language for RIFL, mediation interpretation, later BERT/BERTopic searches, and dissertation writing.

Decision:

- Avoid repeatedly writing "caregiving effect" when discussing RIFL or mediation findings.
- Treat RIFL-related findings as evidence about developmental scaffolding and the functional translation of parental support.

Preferred language:

- developmental scaffolding,
- translation of parental developmental support,
- effective scaffolding,
- uptake of parental scaffolding,
- functional translation of parental support.

Updated guide:

- `docs/construct_language_for_semantic_mapping.md`

Implication for later semantic modeling:

- Keep broad caregiving terms for recall.
- Use scaffolding/support-translation terms for seed terms, topic labels, construct interpretation, and mediation write-up.

### 2026-07-01 - TDSEM Semantic Clustering and Evidence-Map Pipeline

Purpose: move from corpus construction into reproducible topic modeling and dissertation-oriented evidence mapping.

Current analytic corpus:

- `data/processed/tdsem_ris_corpus_clean.csv`
- Parsed records: 13,087.
- Raw source RIS files remain in `data/raw/ris/`.

BERTopic clustering script:

- `src/04_bertopic_semantic_clustering.py`

Planned BERTopic outputs:

- `outputs/topics/paper_topic_assignments.csv`
- `outputs/topics/topic_sizes.csv`
- `outputs/topics/topic_keywords.csv`
- `outputs/topics/topic_coherence.csv`
- `outputs/topics/topic_similarity_matrix.csv`
- `outputs/topics/representative_papers.csv`
- `outputs/topics/visualizations/`

Status:

- Script syntax checks passed.
- BERTopic dependencies were installed in the project-local `.venv`.
- The default embedding model, `sentence-transformers/all-MiniLM-L6-v2`, was downloaded into `.cache/huggingface`.
- A fixed-topic KMeans BERTopic run was completed with `--n-topics 30`.

Evidence-map script:

- `src/05_prepare_evidence_maps.py`

Evidence-map outputs:

- `outputs/evidence_maps/paper_evidence_map.csv`
- `outputs/evidence_maps/manual_coding_template.csv`
- `outputs/evidence_maps/theory_by_method.csv`
- `outputs/evidence_maps/theory_by_agency_marker.csv`
- `outputs/evidence_maps/agency_by_caregiving_construct.csv`
- `outputs/evidence_maps/theory_by_unresolved_gap.csv`
- `outputs/evidence_maps/method_by_unresolved_gap.csv`
- `outputs/evidence_maps/cluster_by_theory.csv`
- `outputs/evidence_maps/cluster_by_method.csv`
- `outputs/evidence_maps/cluster_by_gap.csv`
- `outputs/evidence_maps/top100_cited_evidence_map.csv`
- `outputs/evidence_maps/top100_relevance_weighted_cited.csv`

Verification:

- Papers coded: 13,087.
- `paper_evidence_map.csv`: 13,087 rows and 53 columns.
- `manual_coding_template.csv`: 13,087 rows and 24 columns.
- Added `dissertation_relevance_score` so reading priorities can be sorted by conceptual relevance and citation count, not raw citation count alone.

Interpretive note:

- Raw citation ranking can surface highly cited but off-topic papers from broad clusters. For dissertation reading priorities, use `top100_relevance_weighted_cited.csv` first, then consult `top100_cited_evidence_map.csv` as a transparent bibliometric audit.

### 2026-07-02 - BERTopic Install, MiniLM Download, and k=30 Topic Model

Purpose: install BERTopic locally, download the MiniLM embedding model, generate visual outputs, and support adjustable topic-count comparisons.

Environment:

- Virtual environment: `.venv`
- Package list: `requirements-topic-modeling.txt`
- Hugging Face model cache: `.cache/huggingface`
- Matplotlib cache: `.cache/matplotlib`

Installed packages:

- `bertopic`
- `sentence-transformers`
- `umap-learn`
- `hdbscan`
- `seaborn`

Downloaded embedding model:

- `sentence-transformers/all-MiniLM-L6-v2`
- Verification: one test sentence produced a 384-dimensional embedding.

Pilot topic model:

- Output folder: `outputs/topics_pilot_k8/`
- Documents modeled: 300.
- Clusterer: KMeans.
- Fixed topics: 8.

Full presentation topic model:

- Output folder: `outputs/topics_k30/`
- Documents modeled after DOI deduplication and text filtering: 12,534.
- Clusterer: KMeans.
- Fixed topics: 30.

Topic outputs:

- `outputs/topics_k30/paper_topic_assignments.csv`
- `outputs/topics_k30/topic_sizes.csv`
- `outputs/topics_k30/topic_keywords.csv`
- `outputs/topics_k30/topic_coherence.csv`
- `outputs/topics_k30/topic_similarity_matrix.csv`
- `outputs/topics_k30/representative_papers.csv`
- `outputs/topics_k30/bertopic_model/`

Visual outputs:

- `outputs/topics_k30/visualizations/topics.html`
- `outputs/topics_k30/visualizations/barchart.html`
- `outputs/topics_k30/visualizations/hierarchy.html`
- `outputs/topics_k30/figures/topic_sizes_top25.png`
- `outputs/topics_k30/figures/topic_coherence_top25.png`
- `outputs/topics_k30/figures/topic_similarity_matrix.png`

Topic-linked evidence-map outputs:

- Output folder: `outputs/evidence_maps_k30/`
- `paper_evidence_map.csv`: 13,087 rows and 53 columns.
- `manual_coding_template.csv`: 13,087 rows and 24 columns.
- `topic_by_theory.csv`: 31 rows and 12 columns.
- `topic_by_gap.csv`: 31 rows and 9 columns.

Parameter note:

- BERTopic with HDBSCAN does not use a traditional fixed `k`; it discovers dense topics using `--min-topic-size`, `--n-neighbors`, and clustering density.
- For presentation and comparison, the pipeline now supports fixed topic counts through `--clusterer kmeans --n-topics K`.
- The first full fixed solution used `K = 30`.

Initial model-quality note:

- The k=30 model surfaced meaningful developmental clusters such as trajectories/parenting, RSA/physiological regulation, child learning/language, caregiving/parenting, functional connectivity, autism/joint attention, hyperscanning/neural synchrony, attachment, infant-mother face interaction, and EEG asymmetry.
- It also surfaced off-domain search-noise clusters, including leader-follower workplace studies and economic Granger-causality papers. These should be handled through relevance scoring, cluster filtering, or revised search exclusions before final interpretation.

### 2026-07-02 - Higher-Order Topic Classification

Purpose: translate empirical BERTopic clusters into dissertation-facing topic families and priority tiers.

Script:

- `src/06_classify_topics.py`

Inputs:

- `outputs/topics_k30/topic_sizes.csv`
- `outputs/topics_k30/topic_keywords.csv`
- `outputs/topics_k30/representative_papers.csv`
- `outputs/topics_k30/topic_coherence.csv`
- `outputs/evidence_maps_k30/paper_evidence_map.csv`

Outputs:

- `outputs/topic_classification_k30/topic_classification.csv`
- `outputs/topic_classification_k30/topic_label_review_template.csv`
- `outputs/topic_classification_k30/topic_family_summary.csv`
- `outputs/topic_classification_k30/topic_priority_queue.csv`
- `outputs/topic_classification_k30/figures/topic_family_paper_counts.png`
- `outputs/topic_classification_k30/figures/topic_priority_tiers.png`

Topic families:

- Child Agency and Joint Attention.
- Caregiving, Scaffolding, and Parent-Child Interaction.
- Developmental Pathways and Heterogeneity.
- Neural Calibration and Directionality.
- Physiological Regulation.
- Learning, Language, and Academic Development.
- Attachment and Relational Security.
- Mental Health, Risk, and Adjustment.
- Methods and Measurement.
- Health and Public Health Context.
- Off-Domain / Search Noise.

Priority-tier results:

- A = core dissertation topic: 3,061 papers.
- B = important supporting topic: 7,141 papers.
- C = background or methodological context: 150 papers.
- D = boundary / likely exclusion: 2,182 papers.

Interpretive note:

- This classification is intentionally transparent and rule-based. It should be treated as a first-pass map, not final human coding.
- The `topic_label_review_template.csv` file is the best next file for manually refining topic names, topic families, and priority decisions.

### 2026-07-02 - Obsidian Topic Map Export

Purpose: convert the topic classification layer into an Obsidian-readable knowledge map.

Script:

- `src/07_export_obsidian_topic_map.py`

Output folder:

- `obsidian/TDSEM_Topic_Map/`

Entry note:

- `obsidian/TDSEM_Topic_Map/00_TDSEM_Topic_Map_Index.md`

Generated structure:

- `Assets/`: embedded summary figures.
- `Families/`: one note per higher-order topic family.
- `Topics/`: one note per BERTopic topic.
- `README.md`: short usage note.

Verification:

- Topics exported: 30.
- Topic families exported: 11.
- Summary figures were copied into the Obsidian folder so the index renders when `obsidian/TDSEM_Topic_Map/` is opened as a vault.

Use:

- Open `00_TDSEM_Topic_Map_Index.md` as the map entry point.
- Use topic notes for human labels, dissertation relevance decisions, and keep/background/exclude judgments.
