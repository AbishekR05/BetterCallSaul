# Project Context

We are building a **Legal Awareness AI / Agentic RAG system for Indian law**.

The target users are **laymen users who have little or no knowledge of the law relevant to the domain or situation they are asking about**.

The eventual system will:

1. Understand a user's legal situation/question.
2. Retrieve relevant Indian legislation and judicial precedents.
3. Explain the information in plain English.
4. Provide source citations.
5. Handle Central and State/UT jurisdiction.
6. Provide procedural/practical guidance from authoritative sources.
7. Use an agentic layer for complex, multi-step questions.

The eventual architecture is:

```text
User
 ↓
React Frontend
 ↓
FastAPI Backend
 ↓
Query Understanding
 ↓
 ┌─────────────────────┐
 │                     │
Simple Query      Complex Query
 │                     │
 ▼                     ▼
RAG                   Agent
                        │
                  ┌─────┼─────┐
                  ▼     ▼     ▼
                 RAG   Search Tools
                  │     │     │
                  └─────┼─────┘
                        ▼
                  Evidence Layer
                        ↓
                       LLM
                        ↓
             Plain-English Answer
                 + Citations
```

Gemini will initially be used as the LLM, but the architecture should remain model-agnostic.

---

# Phase 1A Status

Phase 1A acquired a large filtered corpus from:

**Open India Law**

Source:

`https://huggingface.co/datasets/vaquill/open-india-law`

The acquisition produced approximately:

* **15.7 million filtered records**
* Approximately **28.8 GB** stored on Google Drive

The acquisition process is persistent/checkpointed.

The corpus covers legal material across many conceptual domains, including:

### Core / Everyday

* Consumer Protection
* Employment & Labour
* Workplace Rights
* Wages & Minimum Wages
* Employee Benefits & Social Security
* Business & Entrepreneurship
* Startups / MSME
* E-commerce
* Contracts & Agreements
* Property Law
* Land & Real Estate
* Rental / Tenancy
* Housing / Apartments / RERA
* Family Law
* Marriage & Divorce
* Maintenance
* Inheritance & Succession
* Wills & Probate
* Motor Vehicles / Traffic
* Road Safety
* Personal Injury / Compensation
* Criminal Law
* Criminal Procedure
* Evidence
* Civil Procedure
* Legal Aid
* Dispute Resolution
* Arbitration
* Mediation
* Cyber Law / Digital Law
* Online Fraud
* Financial Fraud
* Data Protection & Privacy
* Digital Rights
* Defamation
* Constitutional Rights
* Human Rights
* Women & Child Protection
* Senior Citizen Rights
* Disability Rights

### Business / Regulatory

* Company / Corporate Law
* Banking & Finance
* Insurance
* Taxation
* Intellectual Property
* Copyright
* Patents
* Trademarks
* Competition / Antitrust
* Securities / Investments
* Insolvency / Bankruptcy
* Regulatory Compliance
* Licensing & Permits
* Import / Export
* Food Safety
* Drugs / Pharmaceuticals Regulation
* Product Safety
* Manufacturing / Industrial Regulation
* Shops & Establishments
* Telecom
* Media / Entertainment
* Electronic Signatures / Electronic Records

### Public / Sectoral

* Education Law
* Healthcare / Medical Law
* Environmental Law
* Public Health
* Government Services / Citizen Rights
* Electricity / Utilities
* Transportation
* Agriculture / Rural Legal Issues
* Public Distribution / Essential Services

These are conceptual domains. They are NOT guaranteed to be exact dataset labels.

---

# Phase 1B Status

Phase 1B is currently running **in parallel** with Phase 1C.

Its purpose is:

* Inspecting the acquired corpus
* Normalizing records
* Inspecting schemas
* Classifying source types
* Normalizing jurisdiction
* Classifying domains
* Inspecting text quality
* Detecting duplicates
* Preserving provenance
* Producing normalized records

At the current checkpoint, Phase 1B had inspected:

* 47 / 59 files
* 5,937,549 records
* 5,937,496 retained
* 53 duplicates removed
* 0 empty-text records
* 6 extremely short records (<100 chars)

The process is NOT finished.

The final corpus may contain **10M+ normalized legal records**.

Therefore, Phase 1C must NOT assume that the entire normalized corpus already exists.

---

# CRITICAL REQUIREMENT: PHASE 1B AND PHASE 1C RUN IN PARALLEL

Phase 1C must be designed as an **incremental consumer** of Phase 1B.

The architecture should be:

```text
                 Phase 1A
             Raw Filtered Corpus
                     │
                     ▼
              ┌─────────────┐
              │   Phase 1B  │
              │ Normalize   │
              └──────┬──────┘
                     │
              completed batch
                     │
                     ▼
              ┌─────────────┐
              │   Phase 1C  │
              │   Chunking  │
              └──────┬──────┘
                     │
                     ▼
              Chunked Corpus
```

Phase 1C must NEVER process a file that Phase 1B is still writing.

It should only process **completed/committed Phase 1B outputs**.

---

# Producer / Consumer Checkpointing

Design a persistent manifest/checkpoint system.

Conceptually:

```json
{
  "file": "normalized_xxx.parquet",
  "phase_1b_status": "complete",
  "phase_1c_status": "pending"
}
```

Phase 1C should:

1. Read the manifest.
2. Find normalized files marked `complete`.
3. Find which ones are still `pending` for Phase 1C.
4. Process them incrementally.
5. Mark successful files/batches as complete.
6. Continue looking for newly completed Phase 1B files.
7. Eventually process all normalized files.

If Phase 1C is interrupted:

```text
Phase 1C restart
 ↓
Read checkpoint
 ↓
Skip completed work
 ↓
Continue from first incomplete batch
```

Do NOT rely solely on filenames to determine completion.

---

# Phase 1C Objective

The purpose of Phase 1C is:

> **Convert normalized legal documents into high-quality, legally meaningful retrieval units while preserving legal structure, context, provenance, jurisdiction, and relationships to their source documents.**

The goal is NOT simply:

> "Split everything into 500 tokens."

Legal documents have structure that must be preserved.

---

# Two Primary Chunking Strategies

## 1. Legislation Chunking

Legislation should be structured hierarchically.

Conceptually:

```text
Act
 ├── Preamble
 ├── Part
 │    └── Chapter
 │         └── Section
 │              ├── Subsection
 │              │    └── Clause
 │              └── Explanation
 ├── Schedule
 └── Annexure
```

Where the source contains these structures, preserve them.

A section should preferably remain a coherent retrieval unit.

If a section is too large, split it into meaningful subsections/clauses rather than blindly cutting at arbitrary token counts.

Each chunk should know its parent:

```text
Act
 ↓
Chapter
 ↓
Section
 ↓
Subsection
 ↓
Chunk
```

---

## 2. Judicial Judgment Chunking

Judgments require a different strategy.

Preserve structures where detectable:

```text
Judgment
 ├── Case metadata
 ├── Facts
 ├── Issues
 ├── Arguments
 ├── Evidence
 ├── Reasoning
 ├── Findings
 ├── Ratio / legal reasoning
 ├── Decision
 └── Final order
```

Where explicit headings are unavailable, use paragraph boundaries and contextual grouping.

Do not destroy paragraph ordering.

Preserve paragraph numbers if available.

---

# Parent-Child Retrieval Design

Design the chunks so that we can eventually support:

```text
Parent Document
      │
      ├── Section
      │      ├── Chunk 1
      │      ├── Chunk 2
      │      └── Chunk 3
      │
      └── Metadata
```

This allows future retrieval to return:

* The precise chunk
* Its parent section
* The document title
* Relevant surrounding context

Avoid creating isolated chunks that have no relationship to their source.

---

# Chunk Metadata

Every chunk should preserve/inherit relevant metadata.

Recommended conceptual schema:

```json
{
  "chunk_id": "...",
  "document_id": "...",
  "parent_id": "...",
  "chunk_index": 0,

  "source_type": "legislation/judgment/other",

  "title": "...",
  "domain": [],
  "jurisdiction": "...",
  "level": "central/state/UT",
  "state": "...",

  "court": "...",

  "act": "...",
  "chapter": "...",
  "part": "...",
  "section": "...",
  "subsection": "...",
  "clause": "...",

  "case_name": "...",
  "citation": "...",
  "paragraph_number": "...",

  "date": "...",
  "effective_date": "...",

  "text": "...",

  "source_url": "...",
  "original_source_id": "...",

  "dataset_version": "...",

  "is_historical": false
}
```

This is conceptual.

Use the actual normalized Phase 1B schema where possible.

Do NOT invent metadata.

---

# Chunk Size Strategy

Do not use one universal chunk size for every legal document.

Design a configurable strategy.

The implementation should support:

* Minimum chunk size
* Preferred chunk size
* Maximum chunk size
* Overlap where necessary
* Structure-aware splitting
* Different settings for legislation and judgments

Prefer semantic/legal boundaries over arbitrary character/token boundaries.

For example:

```text
Good:
Section 12
 ├── subsection (1)
 ├── subsection (2)
 └── subsection (3)

Bad:
Section 12
 └── random 500-token split
```

However, extremely long sections/judgment passages must still be split to maintain retrieval efficiency.

---

# Context Preservation

A chunk should not lose necessary context.

For example, if a chunk contains:

> "The authority may impose the penalty..."

the chunk should ideally retain enough parent context to understand:

* Which authority?
* Which situation?
* Which Act?
* Which section?
* Which jurisdiction?

Use metadata and optional contextual prefixes where appropriate.

Example conceptual representation:

```text
[Consumer Protection Act, 2019]
[Chapter III]
[Section 20]
[Subsection (2)]

<actual legal text>
```

Do not alter the legal meaning of the original text.

---

# Cross-References

Legal documents frequently contain references such as:

* "under section 12"
* "subject to section 18"
* "as prescribed"
* "notwithstanding anything contained in..."
* "in accordance with the rules"

Do not attempt to resolve every cross-reference during Phase 1C.

However, preserve them.

Create metadata that allows future retrieval/linking of referenced sections where possible.

---

# Amendments / Historical Versions

Do NOT merge all versions of a law into one chunk.

Preserve:

* Document version
* Date
* Effective date
* Amendment information
* Source URL
* Historical/current status where known

Future RAG retrieval must be capable of distinguishing historical law from current law.

---

# Deduplication at Chunk Level

Do not aggressively deduplicate legally distinct material.

Use hashes only to identify obvious duplicates.

Potential duplicate signals:

* Exact normalized text hash
* Document ID
* Section ID
* Paragraph ID

Do NOT merge chunks from different:

* Jurisdictions
* Courts
* Versions
* Acts
* Judgments

unless they are demonstrably identical.

---

# Scale Requirements

This is a VERY LARGE corpus.

Phase 1C must be designed for potentially:

**10M+ normalized records**

and potentially many more chunks.

The implementation MUST:

* Stream data
* Process in batches
* Avoid loading entire datasets into RAM
* Use efficient columnar formats
* Write incrementally
* Checkpoint frequently
* Resume after failure
* Avoid millions of tiny files
* Avoid unnecessary copying
* Produce statistics incrementally

Do not build a giant in-memory dataframe.

---

# Output Format

Prefer **Parquet** for the chunked corpus.

Do not create one file per chunk.

Use reasonably sized partition files.

Potential structure:

```text
03_chunked/
├── legislation/
│   ├── batch_0001.parquet
│   ├── batch_0002.parquet
│   └── ...
│
├── judgments/
│   ├── batch_0001.parquet
│   ├── batch_0002.parquet
│   └── ...
│
└── other/
```

Partitioning can later be optimized by:

* Source type
* Jurisdiction
* Domain
* Year

but avoid creating an excessive number of tiny partitions.

---

# Storage Efficiency

Because the corpus is already ~28.8 GB:

* Use compression
* Avoid duplicating full documents unnecessarily
* Store source-document references instead of copying massive parent text into every chunk
* Store contextual prefixes only where useful
* Keep raw/normalized/chunked layers separate

The chunked corpus may be larger than the normalized corpus. This is expected.

Generate storage estimates before processing huge batches where practical.

---

# Google Drive

The source/normalized corpus is stored on Google Drive.

Phase 1C should support the existing Google Drive workflow.

Do not unnecessarily download the entire 28.8 GB corpus locally.

If local temporary processing is required:

* Process one manageable batch/file at a time.
* Delete temporary files after successful output.
* Never delete the authoritative raw/normalized corpus.

---

# Parallel Execution Safety

Phase 1B and Phase 1C may run simultaneously.

Therefore:

### Phase 1B writes:

```text
normalized/file_001.parquet
```

only after the file is fully written.

### Then it marks:

```text
file_001 = COMPLETE
```

### Phase 1C only processes:

```text
file_001 = COMPLETE
```

Never process partially written files.

Use atomic writes where possible:

```text
file.tmp
   ↓
fully written
   ↓
file.parquet
   ↓
manifest = COMPLETE
```

The ordering is critical.

---

# Phase 1C Monitoring

Generate incremental statistics.

Track:

* Files processed
* Records processed
* Chunks created
* Legislation chunks
* Judgment chunks
* Average chunk length
* Min/max chunk length
* Distribution of chunk sizes
* Documents with no valid chunks
* Records skipped
* Reasons for skips
* Duplicate chunks
* Processing rate
* Estimated remaining work

Produce a final Phase 1C report after completion.

---

# Quality Validation

Sample chunks from:

* Legislation
* Supreme Court judgments
* High Court judgments
* Central laws
* State laws
* Different domains

Validate:

* Legal text is intact
* Section numbers are preserved
* Paragraph ordering is preserved
* Metadata is correct
* Source URL is preserved
* Jurisdiction is correct
* No accidental truncation
* No unexpected text corruption
* Context remains understandable

Include automated validation where possible.

---

# Important: Do NOT Embed Yet

Phase 1C is ONLY:

**Normalization output → legally meaningful chunks → chunked corpus**

Do NOT:

* Generate embeddings
* Call Gemini for every chunk
* Build FAISS
* Build pgvector
* Build a retriever
* Build an agent
* Build frontend
* Fine-tune an LLM

Those belong to later phases.

---

# Phase 1C Completion

Phase 1C is complete when:

* [ ] Completed Phase 1B files can be consumed incrementally
* [ ] Producer/consumer checkpointing works
* [ ] Legislation chunking is structure-aware
* [ ] Judgment chunking is structure-aware
* [ ] Parent-child relationships are preserved
* [ ] Chunk metadata is complete
* [ ] Jurisdiction metadata is preserved
* [ ] Source provenance is preserved
* [ ] Historical/version information is preserved
* [ ] Cross-references are retained
* [ ] Chunk-level duplicates are identified
* [ ] Processing is batch-based
* [ ] Processing is resumable
* [ ] No entire corpus is loaded into RAM
* [ ] Chunked output uses efficient storage
* [ ] No millions of tiny files are created
* [ ] Quality validation has been performed
* [ ] Statistics are generated
* [ ] Final Phase 1C report is generated

---

# Critical STOP Condition

After Phase 1C completes:

**STOP.**

Do NOT automatically start embeddings or vector database creation.

The next phase will be **RAG Index Design & Embedding Strategy**, where we decide:

* Embedding model
* Vector database
* Hybrid retrieval
* Metadata filtering
* Reranking
* Index structure
* Retrieval strategy
* Cost/storage implications

The Phase 1C implementation agent must report:

1. Total normalized records consumed
2. Total chunks created
3. Legislation chunks
4. Judgment chunks
5. Other chunks
6. Average/median chunk size
7. Chunk-size distribution
8. Domain distribution
9. Jurisdiction distribution
10. Court distribution
11. Duplicate statistics
12. Skipped/invalid records
13. Storage size
14. Processing time
15. Processing rate
16. Any failures
17. Any structural parsing limitations
18. Recommended next steps

**Do not proceed beyond Phase 1C automatically.**