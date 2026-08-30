# Phase 1B: Corpus Inspection & Normalization

**Project:** Legal Awareness AI / Agentic RAG
**Phase:** 1B — Corpus Inspection, Normalization, Validation, Deduplication, Classification
**Status:** Specification (implementation to be carried out separately by Antigravity)

---

## Project context

Phase 1A has been successfully completed.

We used the **Open India Law** dataset as our primary legal corpus and filtered it toward a broad set of legal domains useful for laymen users.

The completed acquisition produced:

- **15,745,223 filtered records**
- Approximately **28.8 GB** stored on Google Drive
- Acquisition was performed automatically
- Progress is persistent/checkpointed
- The raw filtered corpus must NOT be deleted or modified destructively

The project is intended for **laymen users who have little or no knowledge of the law relevant to their question/situation**.

The final system will provide:

1. Statutes & Legislation
2. Judicial Precedents
3. Procedural & Practical Legal Information

The eventual architecture is:

```
User
→ React frontend
→ FastAPI backend
→ Query understanding
→ Simple query → RAG
→ Complex query → Agent
→ RAG / search / tools
→ Evidence layer
→ LLM
→ Plain-English answer + citations
```

The LLM will initially use the Gemini API, but the architecture should remain model-agnostic.

The final system will prioritize:

- Authoritative/source-grounded answers
- Plain-English explanations
- Legal citations
- Jurisdiction awareness
- Current vs historical law awareness
- Uncertainty handling
- Privacy/data minimization

## Phase 1B Objective

The objective of Phase 1B is:

> **Inspect, understand, normalize, validate, deduplicate, classify, and prepare the Phase 1A corpus for later RAG indexing.**

This phase is NOT the RAG embedding/indexing phase.

Do NOT build the vector database yet.

Do NOT generate embeddings yet.

Do NOT start the agent yet.

Do NOT delete raw source data.

The coding/implementation of this specification will be done separately by **Antigravity**.

Therefore, this Markdown file must be written as a highly detailed engineering specification that another coding agent can implement without needing to guess the requirements.

---

# Requirements for Phase 1B

## 1. Locate and inventory the acquired corpus

The implementation must first locate the Phase 1A output on Google Drive / the configured local workspace.

Determine:

- Number of files
- File formats
- Total storage
- Records per file
- Legislation vs judgments vs other source types
- Dataset structure
- Available columns
- Available metadata
- Text fields
- Source URLs
- Jurisdiction information
- Court information
- Dates
- Document types
- Existing domain labels if any

Do NOT assume column names.

The implementation must inspect the actual files/schema first.

Generate an inventory report.

---

## 2. Corpus statistics

Produce detailed statistics including:

### Overall

- Total records
- Total files
- Total storage
- Average record size
- Missing text percentage
- Missing metadata percentage

### By source type

For example:

- Legislation
- Acts
- Rules
- Regulations
- Notifications
- Orders
- Guidelines
- Judgments
- Other

Use actual categories found in the dataset.

### By jurisdiction

Calculate:

- Central / India
- Each State
- Each Union Territory
- Unknown / missing

### Judicial statistics

Where applicable:

- Supreme Court
- Each High Court
- Other courts/tribunals if present

### Temporal statistics

Calculate distribution by:

- Year
- Decade
- Earliest record
- Latest record

Do not assume that the latest record represents current law.

---

## 3. Domain analysis

Our conceptual domain list includes:

### Core / Everyday

Consumer Protection
Employment & Labour
Workplace Rights
Wages & Minimum Wages
Employee Benefits & Social Security
Business & Entrepreneurship
Startups / MSME
E-commerce
Contracts & Agreements
Property Law
Land & Real Estate
Rental / Tenancy
Housing / Apartments / RERA
Family Law
Marriage & Divorce
Maintenance
Inheritance & Succession
Wills & Probate
Motor Vehicles / Traffic
Road Safety
Personal Injury / Compensation
Criminal Law
Criminal Procedure
Evidence
Civil Procedure
Legal Aid
Dispute Resolution
Arbitration
Mediation
Cyber Law / Digital Law
Online Fraud
Financial Fraud
Data Protection & Privacy
Digital Rights
Defamation
Constitutional Rights
Human Rights
Women & Child Protection
Senior Citizen Rights
Disability Rights

### Business / Regulatory

Company / Corporate Law
Banking & Finance
Insurance
Taxation
Intellectual Property
Copyright
Patents
Trademarks
Competition / Antitrust
Securities / Investments
Insolvency / Bankruptcy
Regulatory Compliance
Licensing & Permits
Import / Export
Food Safety
Drugs / Pharmaceuticals Regulation
Product Safety
Manufacturing / Industrial Regulation
Shops & Establishments
Telecom
Media / Entertainment
Electronic Signatures / Electronic Records

### Public / Sectoral

Education Law
Healthcare / Medical Law
Environmental Law
Public Health
Government Services / Citizen Rights
Electricity / Utilities
Transportation
Agriculture / Rural Legal Issues
Public Distribution / Essential Services

These are conceptual categories, NOT guaranteed dataset labels.

The implementation must inspect actual metadata/content and determine how these concepts map onto the acquired corpus.

Do not falsely classify records based on a single generic keyword.

Produce a domain coverage report.

---

## 4. Domain classification strategy

Use a hierarchical classification strategy.

Prefer, in order:

1. Existing authoritative domain/category metadata
2. Subject/category fields
3. Document title
4. Act/law title
5. Issuing authority
6. Referenced legislation
7. Section headings
8. Strong keyword combinations
9. Semantic classification only where necessary

The classification system should be transparent and reproducible.

Create a domain mapping configuration, for example:

`config/domain_mapping.json`

The mapping should be editable without changing the main processing code.

A record may belong to multiple domains.

Example:

A consumer e-commerce regulation could belong to:

- Consumer Protection
- E-commerce
- Business & Entrepreneurship

Do not force every document into exactly one domain.

---

## 5. Jurisdiction normalization

Normalize jurisdiction metadata into a consistent representation.

Examples:

```text
level: central
state: null
country: India
```

or:

```text
level: state
state: Tamil Nadu
country: India
```

or:

```text
level: union_territory
state: null
ut: Delhi
country: India
```

Preserve the original source value as well.

Do not destroy original metadata.

---

## 6. Legal document normalization

Create a normalized schema for downstream RAG processing.

The schema should support both legislation and judicial material.

Suggested fields:

```json
{
  "record_id": "...",
  "source_type": "...",
  "title": "...",
  "text": "...",
  "jurisdiction": "...",
  "level": "...",
  "state": "...",
  "court": "...",
  "domain": [],
  "document_type": "...",
  "date": "...",
  "effective_date": "...",
  "authority": "...",
  "citation": "...",
  "source_url": "...",
  "original_source_id": "...",
  "dataset_version": "...",
  "is_historical": false
}
```

This is only a conceptual schema.

Adapt it to the actual data.

Do not invent values.

---

## 7. Text quality inspection

Analyze legal text quality.

Detect:

- Empty text
- Extremely short text
- Corrupted encoding
- HTML artifacts
- Broken Unicode
- Repeated boilerplate
- Duplicate paragraphs
- OCR-like garbage
- Broken formatting
- Excessive whitespace
- Page-number noise
- Header/footer repetition

Generate quality statistics.

Do not aggressively "clean" legal text in a way that could alter legal meaning.

Keep the original text available.

---

## 8. Deduplication

Detect duplicates using multiple signals:

- Source record ID
- Source URL
- Citation
- Case metadata
- Exact text hash
- Normalized text hash
- Court + case number + date where available

Handle near-duplicates carefully.

Do NOT merge documents merely because they have similar titles.

Do NOT delete historical versions of legislation.

The output should distinguish:

- Exact duplicate
- Near duplicate
- Historical version
- Amendment
- Distinct document

Prefer marking duplicates rather than destructive deletion during this phase.

---

## 9. Legislation versioning

Legal documents can have multiple versions.

The normalization process must preserve:

- Original date
- Effective date where available
- Amendment information
- Historical/current status where determinable
- Source URL
- Version/provenance information

Do not assume the newest document is automatically the correct answer for every historical question.

Do not silently overwrite old legislation.

---

## 10. Judicial precedent normalization

For judgments, preserve:

- Court
- Case name
- Parties
- Citation
- Case number
- Judgment date
- Judges/bench if available
- Referenced Acts/sections
- Jurisdiction
- Source URL
- Full text
- Domain classification

Do not treat every judgment as an equally important precedent.

Add metadata that can later support relevance ranking.

---

## 11. Source provenance

Every record must retain provenance.

At minimum:

- Dataset
- Dataset version/release
- Original record ID
- Original source URL
- Source type
- Download/acquisition date

This is essential because the final legal assistant must be able to cite its evidence.

---

## 12. Current vs historical information

Build metadata that allows later retrieval to distinguish:

- Current law
- Historical law
- Unknown status

Do not attempt complex legal validity determination unless the source data reliably supports it.

Flag uncertain cases for later review.

---

## 13. Output structure

Do NOT overwrite the Phase 1A raw corpus.

Create a new normalized output layer:

```text
Legal-Awareness-RAG/
├── 01_raw_filtered/
│   ├── legislation/
│   └── judgments/
│
├── 02_normalized/
│   ├── legislation/
│   ├── judgments/
│   └── other/
│
├── 03_metadata/
│   ├── inventory/
│   ├── domain/
│   ├── jurisdiction/
│   └── quality/
│
└── 04_reports/
    ├── corpus_inventory.json
    ├── corpus_statistics.json
    ├── domain_coverage.json
    ├── jurisdiction_statistics.json
    ├── quality_report.json
    └── PHASE_1B_REPORT.md
```

Use efficient formats such as Parquet where appropriate.

Do not create millions of tiny files.

---

## 14. Memory/storage constraints

The corpus is approximately 28.8 GB.

The implementation must be designed for large data.

Use:

- Streaming
- Batch processing
- Chunked reads
- Incremental writes
- Checkpointing
- Resumability

Avoid loading the entire corpus into RAM.

The script must be restartable.

If processing is interrupted, it must continue from the last completed file/batch.

---

## 15. Google Drive strategy

The raw corpus is already stored in Google Drive.

Do not unnecessarily re-download the entire 28.8 GB to the local machine.

Prefer:

- Drive API
- Streaming
- Batch processing
- Local temporary files only when necessary

If Google Drive processing is impractical, clearly document the limitation and use the safest available approach.

---

## 16. Validation

After normalization, validate:

- Record count before vs after
- Number of removed duplicates
- Number of invalid records
- Number of records missing text
- Number of records missing provenance
- Number of records without domain classification
- Number of records without jurisdiction
- Number of legislation records
- Number of judgment records

No silent record loss.

Every excluded record should have a reason where practical.

---

## 17. Do NOT build RAG yet

This phase must STOP after normalization and analysis.

Do NOT:

- Generate embeddings
- Create FAISS index
- Create pgvector index
- Call Gemini for every document
- Build the retriever
- Build an agent
- Build frontend
- Fine-tune a model

The next phase will use the normalized corpus to design **legal-aware chunking and RAG indexing**.

---

## 18. Definition of Done

Phase 1B is complete when:

- [ ] Entire Phase 1A corpus has been inventoried
- [ ] Schema has been inspected
- [ ] Record counts are known
- [ ] Storage statistics are known
- [ ] Source types are classified
- [ ] Central/State/UT jurisdiction is normalized
- [ ] Court metadata is normalized
- [ ] Domains are mapped
- [ ] Domain coverage report exists
- [ ] Text quality is measured
- [ ] Duplicates are identified
- [ ] Historical/current metadata is preserved where available
- [ ] Judicial metadata is normalized
- [ ] Provenance is preserved
- [ ] Normalized corpus is written separately
- [ ] No raw source data is destroyed
- [ ] Processing is checkpointed/resumable
- [ ] Final Phase 1B report is generated

**STOP HERE.**

The implementation agent must report:

1. Total records inspected
2. Records retained
3. Records flagged/removed and why
4. Legislation count
5. Judgment count
6. Counts by domain
7. Counts by jurisdiction
8. Counts by court
9. Date ranges
10. Duplicate statistics
11. Text-quality statistics
12. Normalized corpus size
13. Any missing/weak metadata
14. Any limitations discovered
15. Recommended next steps for Phase 1C

Do not proceed automatically into RAG indexing.
