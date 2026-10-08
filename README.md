# 🚀 BidFactory: Evidence-Grounded RFP Response

**Built for the RocketRide Buildathon – Mumbai Edition by Team HackHer**

## 💡 The Problem
Responding to a Request for Proposal (RFP) means reading a long document, pulling out every requirement, checking each one against what the company can actually prove, and drafting answers. It is slow, and the riskiest mistake is claiming a capability the company does not have.

**BidFactory automates the reading and drafting, but never invents capabilities.** Every answer is grounded in the company's own documents; anything without evidence is flagged for a person to decide.

---

## 🔄 How It Works

```
RFP upload (PDF / DOCX)
  → Requirement extraction      RocketRide pipeline calling Groq
  → Evidence retrieval          hybrid search over the company knowledge base
  → Compliance analysis         COVERED / PARTIALLY_COVERED / NOT_FOUND / NEEDS_HUMAN_REVIEW
  → Grounded draft response     written only from retrieved evidence
  → Human review                approve / revise / reject
  → Export                      DOCX proposal, CSV compliance matrix
```

1. **Upload.** The backend reads the text of the PDF or Word document.
2. **Requirement extraction.** The text is sent with extraction instructions to the `bid_factory.pipe` pipeline on RocketRide. The pipeline (`webhook → question → LLM → response`) calls Groq (`openai/gpt-oss-120b` through RocketRide's OpenAI-compatible LLM node) and returns the explicit requirements as structured JSON. The backend validates that JSON against its requirement schema.
3. **Evidence retrieval.** Each requirement is searched against the knowledge base in `data/knowledge_base/`. Documents are chunked and embedded with `all-MiniLM-L6-v2` (sentence-transformers) and stored in a SQLite vector store. Results are ranked by a hybrid score: 70% semantic similarity, 30% keyword overlap.
4. **Compliance analysis.** Based on the evidence found, each requirement gets a status and a confidence score. The thresholds are deliberately conservative:
   - `COVERED`: best match score ≥ 0.70 and at least half the requirement's terms appear in the evidence
   - `PARTIALLY_COVERED`: best match score ≥ 0.60 with some term overlap
   - `NEEDS_HUMAN_REVIEW`: related evidence was found but is not conclusive (the evidence is still attached)
   - `NOT_FOUND`: no relevant evidence at all

   Contradictions between the requirement and the evidence, or between evidence sources, are flagged as conflicts.
5. **Draft response.** Groq drafts a proposal answer **only from the retrieved evidence**. When there is no evidence, the draft says so instead of claiming the capability.
6. **Human review.** Every draft lands in the review queue; a reviewer approves, revises or rejects it. Nothing is sent automatically.
7. **Export.** The reviewed bid can be exported as a DOCX proposal or a CSV compliance matrix.

### Why `NOT_FOUND` is a feature
If the knowledge base has no evidence for a requirement, BidFactory does not guess. It marks the requirement `NOT_FOUND` with 0% confidence and routes it to human review. An RFP that asks for things the company has never documented will therefore show many `NOT_FOUND` items. That is the system refusing to hallucinate.

---

## 🏗 Architecture

```
User
 → BidFactory web app (React, hosted as a RocketRide app)
 → FastAPI backend (Docker on Railway)
     → RocketRide pipeline bid_factory.pipe → Groq     (requirement extraction)
     → Knowledge base: SQLite vector store             (evidence retrieval)
     → Groq                                            (grounded drafting, assistant chat)
```

| Part | Technology | Where it runs |
|---|---|---|
| Web app | React 18, TypeScript, Vite; Firebase email/password sign-in | RocketRide app `team_hackher.bid-factory` |
| API | FastAPI (Python 3.12), Uvicorn | Railway, built from the `Dockerfile` |
| AI pipeline | `bid_factory.pipe` (RocketRide) → Groq | RocketRide |
| Knowledge base | 12 company documents, sentence-transformers embeddings, SQLite | Indexed into the Docker image at build time |
| Graph enrichment | Neo4j (optional; skipped when not configured) | Local `docker-compose` only |

Bids and review items are held in memory, so they reset when the backend restarts.

---

## ⚙️ Run Locally

```bash
# Backend (http://localhost:8000)
pip install -r requirements.txt
python scripts/ingest_kb.py          # build the knowledge-base index
python -m uvicorn backend.main:app --reload --port 8000

# Frontend (http://localhost:3000, proxies /api to the backend)
cd frontend
npm install
npm run dev
```

Copy `.env.example` to `.env` and fill in the values. Key variables:

- `ROCKETRIDE_URI`, `ROCKETRIDE_APIKEY`: RocketRide connection used by the backend to run the pipeline
- `ROCKETRIDE_GROQ_KEY`: Groq key for drafting and chat in the backend. The pipeline reads the same variable from RocketRide's Variables.
- `FRONTEND_ORIGINS`: CORS allowlist (JSON list), e.g. `["https://staging.rocketride.ai"]`
- `AI_FALLBACK_DIRECT_GROQ`: optional; when `true`, extraction calls Groq directly if the pipeline is unavailable. Off by default, so a pipeline failure returns HTTP 503 instead of a silent substitute.

Secrets are only ever read from environment variables or RocketRide Variables; none are stored in the repository.

---

## 🧪 Tests and Checks

```bash
python -m pytest                       # backend test suite
cd frontend && npm run lint && npm run build   # type-check, lint, production build
rocketride validate bid_factory.pipe   # pipeline validation
python -m scripts.rr_pipeline_check    # run the pipeline on real_rfp.pdf
```

Health check: `GET /api/health` → `{"status": "ok", "service": "BidFactory API"}`

### Demo documents
- `demo_assets/Golden_Demo_RFP.docx` (recommended): security and SLA requirements (RBAC, TLS 1.3, AES-256, a 24/7 support clause) that each retrieve supporting evidence from the knowledge base, so the compliance, evidence and draft-response views are fully populated.
- `real_rfp.pdf`: six short service requirements (support, encryption, availability, security module, backups, response time); each returns related evidence for human review.
- `real_test_rfp.docx`: a mix of evidence-backed items and `NOT_FOUND` items.
- `demo_rfp.docx`, `demo_rfp_simple.docx`: further samples.

Requirement extraction uses an LLM, so the exact number and wording of requirements can vary slightly between runs.

---
*Developed with ❤️ by **Team HackHer** for the RocketRide Buildathon.*
