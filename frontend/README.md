# BidFactory

**Evidence-grounded RFP response by Team HackHer**

Responding to a Request for Proposal means reading a long document, finding every requirement, checking each one against what your company can actually prove, and drafting answers. BidFactory automates the reading and drafting, and never invents capabilities. Every answer is grounded in your own documents, and anything without evidence is flagged for a person to decide.

## How it works

1. **Upload an RFP** (PDF or Word).
2. **Requirement extraction:** a RocketRide pipeline calls Groq to pull out the explicit requirements as structured data.
3. **Evidence retrieval:** each requirement is searched against the company knowledge base using hybrid semantic and keyword search.
4. **Compliance analysis:** every requirement gets a status and a confidence score:
   - `COVERED` / `PARTIALLY_COVERED`: a strong evidence match was found
   - `NEEDS_HUMAN_REVIEW`: related evidence was found but is not conclusive
   - `NOT_FOUND`: no supporting evidence exists, so no capability is claimed
5. **Grounded drafts:** a proposal answer is drafted only from the retrieved evidence.
6. **Human review:** approve, revise or reject every draft. Nothing is sent automatically.
7. **Export:** download the reviewed bid as a DOCX proposal or a CSV compliance matrix.

A built-in assistant can also answer questions about the RFP process.

## Getting started

1. Open BidFactory and create an account or sign in.
2. Go to **New RFP**, upload a PDF or DOCX RFP and click **Analyze RFP**.
3. Open the bid to see **Requirements & Evidence** and **AI Responses**, then approve or revise the drafts in **Reviews**.
4. Use **Export DOCX** or **Export CSV** on the bid workspace.

The demo knowledge base describes a sample company's security, compliance, SLA, pricing and past-project documentation. RFP requirements outside those topics correctly come back as `NOT_FOUND`.

## Architecture

- Web app: React + TypeScript, hosted on RocketRide
- API: FastAPI (Python) on Railway
- Requirement extraction: RocketRide pipeline (`webhook → question → LLM`) using Groq
- Knowledge base: sentence-transformers embeddings in a SQLite vector store

Bids and review items are kept in memory on the demo backend and reset when it restarts.
