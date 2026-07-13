# Method Protocol

## Purpose

This protocol documents a theory-driven systematic evidence mapping workflow for developmental calibration research. The review is designed to organize a heterogeneous literature around theories, empirical methods, research questions, findings, limitations, and unresolved debates, rather than to estimate pooled effect sizes.

## Corpus Construction

The initial corpus is constructed from Web of Science exports saved as `savedrecs.txt` files. Raw exports are stored in `data/raw/` and are treated as immutable source records. Stage 01 parses these records into standardized bibliographic metadata for downstream bibliometric summaries, semantic clustering, and manual coding.

## Metadata Extraction

The first parser extracts titles, abstracts, keywords, authors, publication years, journals, DOIs, Web of Science categories, and Times Cited counts. It also creates a combined text field from title, abstract, author keywords, and Keywords Plus to support BERT-based semantic clustering.

## Planned Analytic Stages

Subsequent stages will generate bibliometric summaries, run BERTopic with sentence-transformer embeddings, export topic assignments and topic descriptors, prepare human coding templates, and synthesize evidence-map tables for theory-by-debate, theory-by-method, and debate-by-gap analyses.

## Project Record

The running project record is maintained in `docs/project_recorder.md`. Search strings and cluster rationale are maintained in `docs/search_strategy.md`. These documents should be updated whenever a search string, inclusion boundary, script, or output location changes.
