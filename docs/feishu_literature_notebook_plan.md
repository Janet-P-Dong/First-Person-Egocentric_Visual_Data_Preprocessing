# Feishu Literature Notebook Plan

Updated: 2026-07-07

## Goal

Build a Feishu-based research notebook for the TDSEM developmental calibration literature. Feishu will serve as the readable, shareable, and searchable workspace. The local project will remain the evidence engine for PDFs, metadata, extraction, citation mining, and reproducible analysis.

This is a "NotebookLM-like" workflow, but with a stronger research backbone: every generated note should trace back to a paper, DOI, local PDF path, page/section evidence where available, and one of the nine dissertation literature areas.

## Core Principle

Feishu is the knowledge interface. The local project is the source-of-truth processing layer.

Do not rely on conversational memory alone. Every item should be represented in a table, note, citation-mining tracker, or local manifest.

## Feishu Workspace Structure

### 1. Feishu Wiki or Folder: TDSEM Literature Notebook

Suggested top-level pages:

1. `00 Project Dashboard`
2. `01 Caregiving and Scaffolding`
3. `02 Child Agency in Parent-Child Systems`
4. `03 Joint Attention as Social Learning`
5. `04 RJA and IJA as Distinct Pathways`
6. `05 Heterogeneity and Developmental Localization`
7. `06 Dyadic Neural Organization`
8. `07 Neural Directionality and Leadership`
9. `08 Longitudinal Recalibration`
10. `09 Similar Study Designs`
11. `Citation Mining Tracker`
12. `Claim and Evidence Bank`
13. `Reading Log`
14. `Supervisor-Ready Summaries`

### 2. Feishu Base or Sheet: Source Registry

This is the master table for all papers.

Suggested columns:

| Column | Purpose |
|---|---|
| `source_id` | Stable local ID. |
| `area_id` | One of the nine areas. |
| `area_title` | Human-readable area label. |
| `foundation_rank` | Rank within the 25-paper area packet. |
| `foundation_status` | `foundation`, `backward_candidate`, `forward_candidate`, `selected_expansion`, `excluded`. |
| `title` | Paper title. |
| `authors` | Author string when available. |
| `year` | Publication year. |
| `doi` | DOI if available. |
| `local_pdf_path` | Local file path if we have the PDF. |
| `feishu_doc_url` | Feishu note/doc URL after upload or note creation. |
| `zotero_key` | Zotero key if we connect Zotero later. |
| `priority` | `high`, `medium`, `low`, `exclude`. |
| `read_status` | `not_started`, `skimmed`, `read`, `annotated`, `synthesized`. |
| `notes_status` | `none`, `draft`, `checked`, `supervisor_ready`. |

### 3. Feishu Base or Sheet: Citation Mining Tracker

This tracks backward and forward expansion.

Suggested columns:

| Column | Purpose |
|---|---|
| `candidate_id` | Stable candidate ID. |
| `area_id` | Area where the candidate belongs. |
| `anchor_source_id` | Foundation paper that led us to this candidate. |
| `anchor_title` | Anchor paper title. |
| `citation_direction` | `backward_reference` or `forward_citation`. |
| `candidate_title` | Candidate paper title. |
| `candidate_authors` | Candidate authors. |
| `candidate_year` | Candidate year. |
| `candidate_doi` | Candidate DOI if available. |
| `role` | `classic_theory`, `measure_origin`, `method_origin`, `replication`, `critique`, `recent_extension`, `meta_analysis`, `similar_design`, `other`. |
| `why_relevant` | One-sentence reason. |
| `decision` | `keep`, `maybe`, `exclude`, `need_pdf`, `need_metadata`. |
| `local_pdf_status` | `available`, `missing`, `not_checked`. |
| `notes` | Free notes. |

### 4. Feishu Base or Sheet: Reading Notes

This is the paper-level annotation table.

Suggested columns:

| Column | Purpose |
|---|---|
| `source_id` | Links back to Source Registry. |
| `apa_reference` | APA 7 reference entry. |
| `one_sentence_summary` | What the paper does. |
| `constructs` | Caregiving, RJA, IJA, neural directionality, etc. |
| `methods` | Sample, design, measures, analysis. |
| `key_findings` | Main findings. |
| `supports_our_argument_by` | Direct link to dissertation. |
| `limitations_for_us` | Scope and caution. |
| `quotable_terms` | Short phrases or conceptual labels, not long quotes. |
| `evidence_quality` | `theory`, `review`, `meta_analysis`, `observational`, `longitudinal`, `experimental`, `method`. |
| `next_action` | Read, extract references, cite in intro, cite in method, etc. |

### 5. Feishu Base or Sheet: Claim and Evidence Bank

This turns readings into writing.

Suggested columns:

| Column | Purpose |
|---|---|
| `claim_id` | Stable claim ID. |
| `claim_text` | APA-style claim sentence. |
| `area_id` | Literature area. |
| `supporting_sources` | Linked source IDs. |
| `evidence_type` | Review, meta-analysis, longitudinal, method, etc. |
| `strength` | `strong`, `moderate`, `limited`, `speculative`. |
| `caveat` | Required limitation. |
| `dissertation_section` | Intro, literature review, methods, discussion. |
| `ready_to_write` | Yes/no. |

## Local-to-Feishu Pipeline

### Phase 1. Foundation Sync

Input:

- `outputs/core_papers_25_each_pdfs/manifest.csv`
- `docs/literature_claim_matrix.md`
- `docs/research_foundation_core_papers.md`

Output:

- Feishu Source Registry populated with the 225 foundation papers.
- Each paper assigned to one of the nine areas.
- Missing PDFs flagged.
- Anchor packets marked for first-pass reading.

### Phase 2. Reading Notes

For each high-priority anchor paper:

1. Extract metadata.
2. Read abstract, introduction, methods, key results, discussion, limitations, and reference list.
3. Create APA-style annotation.
4. Add it to Feishu Reading Notes.
5. Link it to the Claim and Evidence Bank.

### Phase 3. Backward Citation Mining

For each foundation anchor:

1. Extract reference list.
2. Identify classic theory, measure-origin, method-origin, and repeated sources.
3. Add candidates to Citation Mining Tracker.
4. Decide `keep`, `maybe`, or `exclude`.
5. Retrieve PDFs for selected candidates.

### Phase 4. Forward Citation Mining

For each foundation anchor:

1. Search who cited it.
2. Prioritize recent reviews, replications, critiques, and similar designs.
3. Add candidates to Citation Mining Tracker.
4. Retrieve PDFs for selected candidates.
5. Update Source Registry.

### Phase 5. Retrieval and Synthesis

Use local PDFs and notes for retrieval. Feishu stores the curated research layer.

Question examples:

- "Which papers justify separating RJA and IJA?"
- "Which studies support localized caregiving effects?"
- "What are the strongest objections to using MVGC as directionality evidence?"
- "Which citations support the first paragraph of the literature review?"

The answer should return:

1. direct answer;
2. source IDs;
3. APA references;
4. caveats;
5. writing-ready paragraph if requested.

## Feishu Connection Options

### Option A. Feishu Cursor Bridge

Status: installed locally as `Feishu Cursor Bridge.app`.

Use when:

- You want Feishu chat to trigger local research workflows.
- You want to send files, notes, or summaries back to a Feishu chat.

Limits:

- It is built for Cursor Agent, not native Codex.
- It stores credentials through Electron Store with a hardcoded encryption key.
- It injects Cursor MCP/rules/skills into `.cursor`, not Codex.

Safe use:

- Enter App ID/App Secret only in the app UI.
- Do not paste secrets into chat or commit them to this project.
- Use the bridge first for file/message exchange, not broad autonomous control.

### Option B. Feishu Official MCP or Open Platform API

Use when:

- We want direct document/table read-write.
- We want a true Feishu knowledge-base sync.

Likely needs:

- Feishu self-built app.
- OAuth or tenant token setup.
- Scoped permissions for docs/sheets/wiki/drive.
- A local script or MCP wrapper.

This is the better long-term route for a NotebookLM-like Feishu workspace.

## Security Rules

1. Never store Feishu App Secret in this repo.
2. Never paste Feishu App Secret into chat.
3. Keep credentials in the Feishu app UI, environment variables, or a local ignored secret file.
4. Use least-privilege Feishu permissions.
5. Separate read-only document access from write/send-message permissions where possible.
6. Keep generated summaries traceable to local source IDs and PDF paths.

## Immediate Next Step

Create importable CSV templates for:

1. `feishu_source_registry.csv`
2. `feishu_citation_mining_tracker.csv`
3. `feishu_reading_notes.csv`
4. `feishu_claim_evidence_bank.csv`

Then populate `feishu_source_registry.csv` from the current 225-paper manifest.
