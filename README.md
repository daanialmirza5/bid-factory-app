# 🚀 BidFactory: Enterprise RFP Orchestration Pipeline

**Built for the RocketRide Buildathon – Mumbai Edition by Team HackHer**

## 💡 The Problem We Are Solving
Every year, enterprise sales and compliance teams waste thousands of manual hours reading dense, 60-page Requests for Proposals (RFPs). Sales engineers are forced to manually extract compliance rules, security requirements, and technical prerequisites, and then cross-reference them against internal knowledge bases just to draft a proposal. 

**BidFactory completely automates this excruciatingly manual process.** By leveraging advanced natural language NLP combined with Hybrid Vector RAG, BidFactory cuts RFP response turnaround times from 3 weeks to 3 minutes, saving organizations millions in operational overhead while completely eliminating human compliance errors.

---

## 🏆 Hackathon Judging Criteria Checkmarks
We meticulously engineered BidFactory to pass strict enterprise and hackathon requirements:
* **✅ Real-World Action:** Integrates directly with native email clients to draft proposal approvals and mocks CRM syncs.
* **✅ Cost Predictable:** The dashboard calculates exact LLM token utilization per run for highly predictable margins.
* **✅ Batch/Volume Tested:** Allows users to ingest multiple files (PDFs, DOCX, PNGs) simultaneously into the pipeline. 
* **✅ Security / Human-in-the-loop:** The AI is strictly barred from auto-sending responses. It flags ambiguous requirements for manual `Approve / Reject` review by a sales engineer.

---

## 🏗 Pipeline & Orchestration Flow

At the core of BidFactory is our custom `bid_factory.pipe`, deployed via the **RocketRide Cloud SDK**. 
Instead of relying on fragile, monolithic AI prompts, our system uses a multi-agent orchestration approach:

1. **Intelligent Ingestion:** When a document is uploaded, the system identifies its format. Text documents are shipped to the RocketRide Gemini Node for structural mapping.
2. **Resilient Failover OCR:** If a user uploads an image-based PDF that the cloud LLM cannot parse, the Python Pipeline automatically intercepts the failure and securely routes it to `Tesseract OCR` for local raster processing.
3. **Structured AI Extraction:** The mapped document is passed to `openai/gpt-oss-20b` (via Groq), prompting the AI to extract explicit requirements into strict JSON schemas. 
4. **Hybrid RAG Evidence Search:** We chunk the extracted requirements and embed them to perform Vector Search (Pinecone/Chroma) and Lexical Search (BM25) against the company's internal Knowledge Base. This guarantees the AI only answers based on verified corporate data, effectively eliminating hallucinations.
5. **AI Synthesis & Human Review:** The pipeline evaluates compliance status, drafts a response, and generates a compliance scorecard. Any ambiguous rules are sent to a robust Human-in-the-loop dashboard.

```mermaid
graph TD
    %% Nodes
    A[Upload RFP Batch] --> B[RocketRide Orchestration]
    
    subgraph Ingestion & Failover Layer
        B --> C{Image or Text?}
        C -- Text Document --> D[RocketRide Gemini Node]
        C -- Image Target --> E[Fallback: Native Local OCR]
        
        D --> F[Groq Requirement Extraction]
        E --> F
    end
    
    subgraph Enterprise Evidence RAG
        F --> G[Vector Embeddings]
        G --> H[Semantic + Lexical Search]
        H --> I[Synthesize Against Local KB]
    end
    
    subgraph Compliance Analytics
        I --> J[Evaluate Compliance Status]
        J -- "High Confidence" --> K[Generate Answer Draft]
        J -- "Ambiguous/Risky" --> L[Flag for Human Review]
    end
    
    K --> M[Approve via Dashboard]
    L --> M
    M --> N[Sync to CRM & Export DOCX]

    %% Styling
    style A fill:#f9fafb,stroke:#d1d5db,stroke-width:2px
    style B fill:#dbeafe,stroke:#3b82f6,stroke-width:2px
    style C fill:#dcfce7,stroke:#22c55e,stroke-width:2px
    style G fill:#fef9c3,stroke:#eab308,stroke-width:2px
    style J fill:#f3e8ff,stroke:#a855f7,stroke-width:2px
    style N fill:#ffedd5,stroke:#f97316,stroke-width:2px
```

## ⚙️ How to Run Locally

### 1. Start the Backend
Our backend is powered by FastAPI and Uvicorn.
```bash
# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server (Runs on port 8000)
python -m uvicorn backend.main:app --reload --port 8000
```

### 2. Start the Frontend
Our dashboard is built with React, TypeScript, and Vite.
```bash
cd frontend

# Install packages
npm install

# Start the Vite development server
npm run dev
```

Navigate to `http://localhost:3000` to view the Workspace Dashboard.

---

## Staging

### Environment
RocketRide Staging (`https://staging.rocketride.ai`)

### Architecture
- **Pipeline Orchestration**: RocketRide Cloud AI Pipeline (`bid_factory.pipe`)
- **Backend API**: FastAPI (Python 3.12) / Uvicorn with Hybrid RAG & Compliance Evaluation
- **Frontend**: React 18, TypeScript, Vite SPA with realtime dashboard
- **Database / Graph**: SQLite Vector Store + Neo4j Graph Topology (optional)
- **Container**: Multi-stage Docker deployment (Node 20 build + Python 3.12 runtime)

### Build
```bash
# Frontend production build
cd frontend
npm install
npm run build
cd ..

# Backend dependency verification
pip install -r requirements.txt
```

### Run
```bash
# Run unified application (serves API and built SPA)
uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Or run via Docker Compose
docker-compose up --build -d
```

### Environment Variables
Configure environment variables using `.env.example`:
- `ROCKETRIDE_URI`: RocketRide staging URI (`https://staging.rocketride.ai`)
- `ROCKETRIDE_APIKEY`: RocketRide deployment & execution API key
- `ROCKETRIDE_DEPLOY_URI`: Deployment target endpoint
- `ROCKETRIDE_DEPLOY_APIKEY`: API key for deployment target
- `ROCKETRIDE_GROQ_KEY` / `ROCKETRIDE_GEMINI_KEY`: AI provider keys for pipeline nodes
- `FRONTEND_ORIGINS`: Allowed CORS origins

### Health Check
- **API Endpoint**: `GET /api/health` -> `{"status": "ok", "service": "BidFactory API"}`
- **Docker Healthcheck**: Built-in container healthcheck querying `/api/health`

### Deployment
Deploy the pipeline artifact to RocketRide Staging using the official RocketRide CLI:
```bash
# Validate pipeline configuration
rocketride validate --uri https://staging.rocketride.ai --apikey $ROCKETRIDE_APIKEY bid_factory.pipe

# Deploy pipeline to registry
rocketride deploy add --uri https://staging.rocketride.ai --apikey $ROCKETRIDE_DEPLOY_APIKEY bid_factory.pipe

# Bind deployment to team/project
rocketride deploy publish --uri https://staging.rocketride.ai --apikey $ROCKETRIDE_DEPLOY_APIKEY 70dfea6f-6fdf-4222-952d-4f93bda1d0c5 1
```

---
*Developed with ❤️ by **Team HackHer** for the RocketRide Buildathon.*
