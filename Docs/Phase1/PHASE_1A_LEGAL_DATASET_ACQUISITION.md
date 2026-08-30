# Phase 1A — Legal Dataset Acquisition

## Objective

Build a broad but manageable **domain-filtered Indian legal corpus** for our Legal Awareness RAG project.

We are **NOT downloading the entire Open India Law corpus**. We will filter it to important legal domains useful to laymen, while preserving Central, State, and Union Territory jurisdiction information.

The acquisition must be automated as much as possible and upload/store the selected data directly in Google Drive using the already-configured Google Drive API setup.

---

## 1. Primary Dataset

Use **Open India Law** as the primary large-scale legal corpus:

https://huggingface.co/datasets/vaquill/open-india-law

Before downloading large files, inspect the actual dataset and determine:

- Configurations/splits
- File formats
- Schema/columns
- Jurisdiction fields
- Document/source type fields
- Domain/topic fields, if available
- Whether legislation and judgments are separated
- Approximate size of relevant subsets
- License and provenance

**Do not invent column names or filtering fields.** Inspect the real schema first.

---

## 2. Domains to Include

We want broad coverage of important everyday legal problems without downloading irrelevant material.

Prioritize these domains:

### Core / Everyday
1. Consumer Protection
2. Employment & Labour
3. Workplace Rights
4. Wages & Minimum Wages
5. Employee Benefits & Social Security
6. Business & Entrepreneurship
7. Startups / MSME
8. E-commerce
9. Contracts & Agreements
10. Property Law
11. Land & Real Estate
12. Rental / Tenancy
13. Housing / Apartments / RERA
14. Family Law
15. Marriage & Divorce
16. Maintenance
17. Inheritance & Succession
18. Wills & Probate
19. Motor Vehicles / Traffic
20. Road Safety
21. Personal Injury / Compensation
22. Criminal Law
23. Criminal Procedure
24. Evidence
25. Civil Procedure
26. Legal Aid
27. Dispute Resolution
28. Arbitration
29. Mediation
30. Cyber Law / Digital Law
31. Online Fraud
32. Financial Fraud
33. Data Protection & Privacy
34. Digital Rights
35. Defamation
36. Constitutional Rights
37. Human Rights
38. Women & Child Protection
39. Senior Citizen Rights
40. Disability Rights

### Business / Regulatory
41. Company / Corporate Law
42. Banking & Finance
43. Insurance
44. Taxation
45. Intellectual Property
46. Copyright
47. Patents
48. Trademarks
49. Competition / Antitrust
50. Securities / Investments
51. Insolvency / Bankruptcy
52. Regulatory Compliance
53. Licensing & Permits
54. Import / Export
55. Food Safety
56. Drugs / Pharmaceuticals Regulation
57. Product Safety
58. Manufacturing / Industrial Regulation
59. Shops & Establishments
60. Telecom
61. Media / Entertainment
62. Electronic Signatures / Electronic Records

### Public / Sectoral
63. Education Law
64. Healthcare / Medical Law
65. Environmental Law
66. Public Health
67. Government Services / Citizen Rights
68. Electricity / Utilities
69. Transportation
70. Agriculture / Rural Legal Issues
71. Public Distribution / Essential Services

These are **conceptual domains**, not guaranteed dataset labels. Map them to the actual metadata/content available after schema inspection.

---

## 3. Jurisdiction

Central and State laws are part of the **Statutes & Legislation** layer.

Retain:

- Central / India
- State-specific legislation
- Union Territory legislation
- State-specific rules/regulations

Do not discard jurisdiction metadata.

Each processed item should retain fields such as:

```json
{
  "jurisdiction": "...",
  "level": "central/state/UT",
  "state": "...",
  "domain": "...",
  "document_type": "...",
  "title": "...",
  "year": "...",
  "authority": "...",
  "source": "...",
  "source_url": "..."
}
```

Only populate fields that actually exist or can be transparently derived.

---

## 4. Three Legal Knowledge Layers

### A. Statutes & Legislation

Collect relevant:

- Acts
- Statutes
- Rules
- Regulations
- Notifications
- Circulars
- Orders
- Guidelines
- Other relevant government legal instruments

### B. Judicial Precedents

Collect relevant:

- Supreme Court judgments
- High Court judgments
- Important precedents
- Relevant judicial orders

**Do NOT download all millions of judgments.** Filter to our selected domains using available metadata/relevance signals.

### C. Procedural & Practical Data

This will later be collected separately from official government/regulator sources:

- Complaint procedures
- Filing processes
- Required documents
- Authorities/agencies
- Official forms
- Official portals
- Deadlines/time limits where authoritative
- Government helplines
- Practical procedural guidance

---

## 5. Do NOT Download Everything

The goal is:

**Large source corpus → domain filtering → manageable project corpus**

NOT:

**Large source corpus → download everything → huge storage/vector DB**

Filter as early as possible. Prefer metadata/server-side filtering or streaming where supported.

Before large downloads, generate a report containing:

- Domain
- Estimated record count
- Estimated storage size
- Source type
- Jurisdiction coverage

---

## 6. Google Drive

A `credentials.json` OAuth client file is already available in the workspace.

Use:

- `google-api-python-client`
- `google-auth`
- `google-auth-oauthlib`
- `google-auth-httplib2` if required

The first authentication may require browser authorization.

### Security

**Never commit `credentials.json` to Git.**

Add it to `.gitignore`.

Do not print its contents, upload it to GitHub, or include secrets in reports.

Use the existing credentials rather than creating another OAuth project unless necessary.

---

## 7. Google Drive Folder Structure

Create:

```text
Legal-Awareness-RAG/
├── 01_raw_filtered/
│   ├── legislation/
│   └── judgments/
├── 02_processed/
│   ├── legislation/
│   └── judgments/
├── 03_metadata/
└── 04_reports/
```

Upload only the filtered project corpus.

---

## 8. Acquisition Script

Build a reusable Python acquisition script that:

1. Inspects the Open India Law dataset.
2. Identifies configurations/splits.
3. Inspects the schema.
4. Defines domain mapping.
5. Filters legislation and judgments.
6. Preserves Central/State/UT jurisdiction.
7. Preserves source URLs and provenance.
8. Deduplicates records where appropriate.
9. Records dataset version/date where available.
10. Creates a manifest.
11. Uploads selected data to Google Drive.
12. Supports resume/restart.
13. Avoids duplicate uploads.
14. Produces a final report.

The script must be safe to run multiple times.

---

## 9. Domain Mapping

Do not assume a clean `domain` column exists.

If necessary, map domains using available:

- Subject/category metadata
- Act/document title
- Issuing authority
- Legal category
- Provisions/sections
- Keywords
- Existing tags

Keep mappings in:

```text
config/domain_mapping.json
```

Use strong signals first. Avoid including a document merely because a single generic word appears in it.

---

## 10. Judicial Filtering

The case-law corpus is potentially enormous.

Filter judicial material using the strongest available signals:

1. Explicit domain/topic metadata
2. Referenced legislation/Act
3. Court and jurisdiction
4. Case subject/category
5. Relevant legal terminology
6. Keyword combinations
7. Semantic classification only if necessary

Prefer relevant Supreme Court and High Court precedents.

Do not attempt to download millions of judgments.

---

## 11. Deduplication

Handle:

- Duplicate judgments
- Repeated documents
- Same source under multiple records
- Metadata duplicates

Use, where available:

- Source ID
- Citation
- Court + case number + date
- Source URL
- Content hash

Do not silently remove distinct versions of legislation if they represent different amendments or historical versions.

---

## 12. Freshness / Versioning

Legal information changes.

Record:

- Dataset release/version
- Download date
- Source URL
- Original document date
- Effective/modified date where available
- Jurisdiction
- Document type

Do not silently overwrite historical/current versions.

---

## 13. Licensing / Provenance

Before using or redistributing data:

- Inspect the dataset license.
- Record the license.
- Record provenance.
- Preserve attribution/source URLs.
- Do not assume availability on Hugging Face means unrestricted redistribution.

If licensing is unclear, flag it in the report.

---

## 14. Expected Output

Google Drive:

```text
Legal-Awareness-RAG/
├── filtered legislation
├── filtered judgments
├── metadata
├── manifest
└── acquisition report
```

Workspace:

```text
scripts/
    acquire_open_india_law.py

config/
    domain_mapping.json

reports/
    acquisition_report.json
    acquisition_report.md

.gitignore
```

---

## 15. What NOT to Do

Do NOT:

- Download the entire Open India Law corpus.
- Download all judgments.
- Embed documents yet.
- Build the vector database yet.
- Start chunking yet.
- Call Gemini unnecessarily.
- Manually download hundreds of PDFs.
- Commit OAuth credentials.
- Invent dataset fields.
- Assume every document is current law.
- Treat third-party datasets as automatically authoritative.

This phase is **DATA ACQUISITION ONLY**.

---

## 16. Next Phase

After acquisition, STOP.

Do not automatically build embeddings or the vector database.

The next phase will be:

**Document normalization → legal-aware parsing → section-aware chunking → metadata enrichment.**

---

## Definition of Done

- [ ] Open India Law schema inspected
- [ ] License/provenance recorded
- [ ] Domains mapped to actual dataset structure
- [ ] Central + State/UT material retained
- [ ] Relevant legislation filtered/downloaded
- [ ] Relevant judicial material filtered/downloaded
- [ ] Duplicates handled
- [ ] Source URLs/provenance preserved
- [ ] Manifest created
- [ ] Count/storage report created
- [ ] Filtered corpus uploaded to Google Drive
- [ ] Script is resumable/re-runnable
- [ ] OAuth credentials protected
- [ ] No embeddings/vector DB created

**STOP after Phase 1A. Report collected record counts, storage size, domains, jurisdictions, source types, and limitations.**
