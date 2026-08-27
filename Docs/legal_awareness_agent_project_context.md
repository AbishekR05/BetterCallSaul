# Legal Awareness Agent --- Project Context

## 1. Project Idea

Build a **Legal Awareness AI system for common people**, combining **RAG
(Retrieval-Augmented Generation)** with **Agentic AI where it is
genuinely useful**.

The goal is **not** to create an "AI lawyer." The goal is to provide
accessible, source-grounded legal information and help users identify
potential legal considerations **before they take an action**.

Core idea:

> Help ordinary people understand relevant legal information and
> potential legal constraints before they invest time, money, or effort
> into something.

------------------------------------------------------------------------

## 2. Origin Story / Motivation

The project is inspired by a real experience.

I was working on an e-commerce website for fireworks/crackers. I planned
to go beyond simply displaying products and wanted to implement things
such as payment gateways and the rest of the e-commerce functionality.

Later, I discovered that there were legal/regulatory constraints around
selling fireworks online in India. The work I had already done was
therefore potentially wasted because I had not checked the legal
feasibility of the business idea early enough.

This led to the core realization:

> If I had been able to have a conversation with an AI system that could
> check relevant laws and regulations before I started building, I could
> have discovered the legal constraints much earlier.

This becomes the motivation for the project.

The fireworks example should be presented as the **origin story**, not
necessarily as the entire scope of the product.

------------------------------------------------------------------------

# 3. Core Problem Statement

People often discover legal constraints **after** they have already
invested substantial time, money, or effort into an activity.

Examples:

-   Starting a business
-   Selling a product online
-   Signing a contract
-   Renting a property
-   Employment-related situations
-   Consumer disputes
-   Traffic-related matters
-   Uploading or using copyrighted material
-   Running regulated businesses

The system should provide a way for users to ask:

> "Before I do this, what legal things should I know?"

rather than only:

> "I already have a legal problem. What do I do?"

This **preventive legal-awareness angle** is one of the project's
strongest differentiators.

------------------------------------------------------------------------

# 4. RAG vs Agent --- Important Design Decision

A major discussion point:

## RAG does NOT require an agent.

A conventional RAG system already performs retrieval:

``` text
User Query
    ↓
Embedding
    ↓
Vector / Hybrid Search
    ↓
Relevant Legal Documents
    ↓
LLM
    ↓
Grounded Answer
```

RAG answers:

> "What information should I retrieve for this question?"

An agent answers:

> "What actions/tools do I need to use to solve this problem?"

Therefore, we should **not add an agent just because Agentic AI is
trendy**.

------------------------------------------------------------------------

# 5. Why Add an Agent?

The agent becomes useful when a query requires:

-   Multiple retrieval steps
-   Query decomposition
-   Choosing between different tools
-   External/current information
-   Jurisdiction-specific investigation
-   Checking whether retrieved evidence is sufficient
-   Multi-step reasoning/workflows
-   Combining multiple sources

Example:

> "I want to start an online fireworks business in Chennai. Can I sell
> them online, what licenses would I need, and what restrictions should
> I know about?"

The agent can decompose this into:

1.  Is online sale permitted?
2.  Which laws/rules regulate fireworks?
3.  What licenses are required?
4.  Does location/jurisdiction matter?
5.  Are there additional restrictions?
6.  Is the available evidence sufficient?

Then it can use different tools/RAG searches as needed.

------------------------------------------------------------------------

# 6. Proposed Agentic Workflow

Conceptually:

``` text
User Query
    ↓
Agent
    ↓
Understand Intent / Risk
    ↓
Determine Required Actions
    ↓
┌─────────────────────────────────┐
│ Legal RAG                        │
│ Official-source search           │
│ Document analysis                │
│ Other tools                     │
└─────────────────────────────────┘
    ↓
Evidence
    ↓
Check Evidence Sufficiency
    ↓
LLM
    ↓
Plain-English Answer
    ↓
Sources / Citations
```

The agent should **orchestrate** RAG rather than replace RAG.

A useful conceptual distinction:

> **RAG is a capability/tool available to the agent.**

------------------------------------------------------------------------

# 7. Recommended Development Strategy

Do NOT start by building the agent.

Build the system incrementally:

## Version 1 --- Basic RAG

``` text
Legal Documents
    ↓
Document Processing
    ↓
Chunking
    ↓
Embeddings
    ↓
Vector DB
    ↓
Retriever
    ↓
LLM
    ↓
Cited Answer
```

Get this working properly first.

## Version 2 --- Improved RAG

Add:

-   Better chunking
-   Metadata
-   Hybrid retrieval
-   BM25/keyword search
-   Vector search
-   Reranking
-   Source/page/section citations
-   Retrieval evaluation

## Version 3 --- Agentic RAG

Add:

-   Intent classification
-   Query decomposition
-   Tool selection
-   Multiple RAG searches
-   Official web/source lookup where appropriate
-   Evidence sufficiency checks
-   Fallback strategies

## Version 4 --- Production/Portfolio Version

Add:

-   Authentication
-   User accounts
-   Chat history
-   Conversation memory
-   Document uploads
-   Privacy controls
-   Observability
-   Evaluation dashboard
-   React frontend
-   FastAPI backend
-   Docker/deployment
-   Strong GitHub README
-   Architecture diagram
-   Demo

------------------------------------------------------------------------

# 8. Legal Knowledge Base

The RAG knowledge base should be based on **reliable, authoritative
sources**.

Potential source categories:

-   Acts
-   Rules
-   Government notifications
-   Government guidelines
-   Official regulatory documents
-   Relevant court judgments
-   Official FAQs/public information
-   Other authoritative legal sources

The project should prioritize **source-grounded answers** instead of
allowing the LLM to answer from its general training knowledge.

Each retrieved chunk should ideally retain metadata such as:

``` text
document_id
title
source
date
jurisdiction
section
page
document_type
url
```

------------------------------------------------------------------------

# 9. Retrieval Architecture

A stronger RAG pipeline:

``` text
User Query
    ↓
Query Processing
    ↓
Hybrid Retrieval
    ├── Vector Search
    └── Keyword/BM25 Search
    ↓
Candidate Results
    ↓
Reranker
    ↓
Top Relevant Chunks
    ↓
Context Construction
    ↓
LLM
    ↓
Answer + Citations
```

The goal is to avoid relying only on naive top-k vector similarity.

------------------------------------------------------------------------

# 10. Legal Awareness Scope

Do NOT initially attempt to cover all Indian law.

Start with a manageable set of domains, potentially:

-   Consumer rights
-   Employment
-   Rental/tenancy
-   Online business/e-commerce
-   Traffic/basic civil matters

The exact initial domains can be finalized later.

The fireworks example can be included as a demonstration/use case.

------------------------------------------------------------------------

# 11. Safety / Legal Positioning

The product should be positioned as:

> **Legal information / legal awareness assistant**

NOT:

> "AI lawyer"

and NOT:

> "A system that provides definitive legal advice."

Responses should distinguish between:

-   General legal information
-   Potential applicability
-   Possible options/resources
-   Situations where professional legal advice is appropriate

For high-impact or uncertain situations, the system should encourage
consultation with a qualified legal professional.

This is both a product and system-design requirement.

------------------------------------------------------------------------

# 12. User Data / Database Architecture

There should be a database for **application/user data**, separate
conceptually from the legal knowledge base.

Recommended initial stack:

## PostgreSQL + pgvector

This allows us to use PostgreSQL for relational application data and
pgvector for embeddings without unnecessarily introducing many different
databases.

Conceptual architecture:

``` text
                    PostgreSQL
                         │
          ┌──────────────┼──────────────┐
          ↓              ↓              ↓
        Users        Conversations    Messages
          │              │              │
          └──────────────┼──────────────┘
                         │
                       pgvector
                         │
                  Legal embeddings
                  Document chunks
                  Retrieval metadata
```

Potentially use object storage for uploaded files.

------------------------------------------------------------------------

# 13. User Data to Store

Potential application data:

-   User/account ID
-   Authentication-related data
-   Conversation ID
-   Chat messages
-   Timestamps
-   User preferences
-   Source/citation references
-   Uploaded document metadata

Avoid unnecessarily storing highly sensitive personal information.

Potentially sensitive information could appear in legal conversations,
such as:

-   Government ID numbers
-   Bank information
-   Addresses
-   Personal legal documents
-   Employment details
-   Contract contents

The architecture should follow data minimization.

------------------------------------------------------------------------

# 14. Chat History

Chat history is useful for multi-turn conversations.

Example:

``` text
User:
"My landlord hasn't returned my deposit."

User:
"What can I do?"

User:
"The agreement says the deposit must be returned within 30 days."
```

The system needs conversation context to answer the third message
correctly.

Suggested structure:

``` text
User
 └── Conversation
      ├── Message
      │    ├── role
      │    ├── content
      │    └── timestamp
      │
      ├── Message
      │    ├── role
      │    ├── content
      │    └── citations
      │
      └── Message
```

------------------------------------------------------------------------

# 15. Memory vs Chat History

These should be treated differently.

## Short-term memory

Current conversation context.

Used to maintain continuity during a conversation.

## Long-term memory

Only information that is appropriate and useful to retain.

Do not automatically remember every detail mentioned by the user.

Ideally provide controls such as:

-   Delete conversation
-   Delete my data
-   Don't save this conversation

------------------------------------------------------------------------

# 16. Citations / Evidence Tracking

Because this is a legal system, every answer should ideally retain the
evidence used to produce it.

Example:

``` text
Answer Message
 ├── Answer text
 ├── Timestamp
 └── Sources
      ├── document_id
      ├── page
      ├── section
      ├── source URL
      └── retrieval/reranking information
```

This lets the user inspect where an answer came from.

This is especially important for trust and hallucination reduction.

------------------------------------------------------------------------

# 17. Overall Architecture

Current conceptual architecture:

``` text
                         LEGAL AWARENESS AGENT
                                  │
                                  ▼
                              User Query
                                  │
                                  ▼
                         Intent / Risk Analysis
                                  │
                         ┌────────┴────────┐
                         │                 │
                    Simple Query      Complex Query
                         │                 │
                         ▼                 ▼
                        RAG          Agentic Workflow
                         │                 │
                         │          ┌──────┼──────┐
                         │          ▼      ▼      ▼
                         │         RAG   Search  Tools
                         │          │      │      │
                         └──────────┴──────┴──────┘
                                  │
                                  ▼
                           Evidence Check
                                  │
                                  ▼
                              LLM Response
                                  │
                         ┌────────┴────────┐
                         ▼                 ▼
                  Plain-English        Sources /
                     Answer             Citations
```

------------------------------------------------------------------------

# 18. Proposed Technology Stack

Initial candidate stack:

### Frontend

-   React
-   Tailwind CSS

### Backend

-   Python
-   FastAPI

### AI

-   LLM API
-   Embedding model
-   Agent orchestration framework (e.g. LangGraph, if justified)

### RAG

-   PostgreSQL + pgvector initially
-   Hybrid search
-   Reranker

### Database

-   PostgreSQL
-   pgvector

### Evaluation

-   RAGAS and/or custom evaluation pipeline

### Deployment

-   Docker
-   Cloud deployment

Do not use tools/frameworks just for resume buzzwords. Every technology
should have a defensible reason.

------------------------------------------------------------------------

# 19. Evaluation Strategy

One of the strongest project ideas is to compare:

### A. Basic RAG

Question → Retrieve → LLM

### B. Improved RAG

Question → Hybrid Retrieval → Reranking → LLM

### C. Agentic RAG

Question → Agent → Tool/RAG selection → Evidence → LLM

Evaluate:

-   Retrieval precision
-   Retrieval recall
-   Context relevance
-   Answer relevance
-   Faithfulness
-   Citation correctness
-   Hallucination rate
-   Latency
-   Token usage/cost
-   Agent/tool-selection accuracy

Important research/engineering question:

> **Does adding an agent actually improve legal question answering
> compared with a well-designed RAG system?**

If the agent improves certain query classes but not others, that is
still a valuable finding.

------------------------------------------------------------------------

# 20. Interview Positioning

A strong interview explanation:

> "While developing an e-commerce platform for fireworks, I spent
> significant effort implementing the product catalog and payment
> infrastructure. I later discovered legal constraints around the online
> sale of fireworks, which meant I had invested effort before validating
> whether the business model was legally feasible. That experience made
> me think about building a legal-awareness system that could help
> people identify relevant legal considerations before they take
> potentially consequential actions."

Then explain:

> "I initially designed it as a conventional RAG system because legal
> answers need to be grounded in authoritative sources. I only
> introduced an agentic layer for queries requiring multi-step
> investigation, query decomposition, source selection, or multiple
> tools. The agent orchestrates the workflow, while RAG provides the
> grounded legal evidence."

This is much stronger than saying:

> "I built an Agentic RAG project because it is trending."

------------------------------------------------------------------------

# 21. Estimated Timeline

A realistic target is **3--4 weeks of focused development**, or around
**5--6 weeks alongside college/job preparation**.

Approximate breakdown:

  Phase                                 Estimated Time
  ----------------------------------- ----------------
  Problem definition + architecture          1--2 days
  Legal knowledge base                       3--5 days
  Basic RAG                                  4--5 days
  Improved retrieval                         3--4 days
  Conversation layer                         2--3 days
  Agentic layer                              4--6 days
  Evaluation                                 3--4 days
  Frontend + deployment                      4--6 days
  Documentation/demo                         2--3 days

Target:

-   **Day 3--5:** working RAG MVP
-   **Week 2:** strong retrieval pipeline
-   **Week 3:** agentic RAG
-   **Week 4:** portfolio-ready system

------------------------------------------------------------------------

# 22. Core Project Philosophy

The project should NOT be:

> "Let's add RAG and agents because jobs ask for them."

Instead:

> **Start with the actual problem, build the simplest system that solves
> it, then introduce agents only where they provide measurable value.**

Core architecture philosophy:

``` text
Legal Knowledge
      ↓
Reliable Retrieval
      ↓
Grounded Answers
      ↓
Agentic Orchestration only when necessary
      ↓
Evaluation
      ↓
Privacy + Reliability
```

The strongest version of this project demonstrates:

**RAG engineering + Agent orchestration + Retrieval evaluation +
Legal-source grounding + Privacy-aware system design + Full-stack
implementation.**
