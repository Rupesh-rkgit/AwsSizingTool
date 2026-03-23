# AWS Infrastructure Sizing Tool

A web application that analyzes AWS architecture diagrams and non-functional requirements (NFRs) to generate comprehensive infrastructure sizing recommendations and cost estimates using Amazon Bedrock AI.

## What It Does

This tool takes one or more of the following inputs:

- **Architecture Diagram** (PNG, JPG, JPEG, WEBP — max 20 MB): An image of your AWS architecture. The AI analyzes the diagram to identify services, relationships, and topology.
- **NFR Document** (.txt, .md — max 5 MB): A text file containing your non-functional requirements, volumetric details, SLAs, throughput targets, etc.
- **Text Prompt** (free-form): Inline description of your requirements, workload characteristics, and sizing constraints.

At least one input is required. You can combine all three for the most comprehensive analysis.

The tool sends these inputs to Amazon Bedrock (Claude) which produces:

1. **Infrastructure Sizing Report** — Detailed recommendations including:
   - Service configurations (EC2, EKS, RDS, CloudFront, etc.)
   - Kubernetes node groups, pod specs, and HPA configurations
   - Latency budgets and monitoring metrics
   - Kubernetes YAML manifests (Deployments, HPAs, Jobs, Karpenter NodePools)
   - Batch job specifications
   - Cost optimization strategies
   - Container best practices and network configuration

2. **Bill of Materials (BOM)** — Itemized cost breakdown including:
   - Tiered cost structure (Compute, Networking, Storage, etc.)
   - Per-service line items with unit pricing
   - Monthly and annual cost totals
   - Savings Plans scenarios (1-year, 3-year commitments)
   - Service summary table

3. **HTML Report** — A styled, self-contained HTML document with:
   - Navigation sidebar with anchor links
   - Color-coded sections for Infrastructure vs BOM
   - Summary cards for total costs
   - Printable layout

All reports can be downloaded individually (Markdown, HTML) or as a ZIP bundle.

## Architecture

```
┌─────────────────┐         ┌──────────────────────────────────┐
│   React + Vite  │  /api/  │       FastAPI Backend             │
│   Frontend      │────────▶│                                  │
│   (port 5173)   │         │  InputValidator                  │
└─────────────────┘         │    ↓                             │
                            │  PromptBuilder                   │
                            │    ↓                             │
                            │  BedrockClient ──▶ Amazon Bedrock│
                            │    ↓                             │
                            │  SizingEngine (parse + retry)    │
                            │    ↓                             │
                            │  ReportGenerator (MD, HTML, JSON)│
                            │    ↓                             │
                            │  DatabaseManager (SQLite)        │
                            └──────────────────────────────────┘
```

### Backend (Python / FastAPI)

| File | Purpose |
|------|---------|
| `backend/main.py` | FastAPI app with endpoints: `POST /api/analyze`, `GET /api/sessions`, `GET /api/sessions/{id}`, `DELETE /api/sessions/{id}` |
| `backend/config.py` | Layered config: defaults → `config.yaml` → environment variables |
| `backend/config.yaml` | Default configuration (model ID, region, timeouts, CORS, etc.) |
| `backend/services/input_validator.py` | Validates file types (magic bytes), file sizes, NFR documents, and ensures at least one input |
| `backend/services/bedrock_client.py` | Thin wrapper around `boto3` Bedrock Runtime Converse API with timeout and retry config |
| `backend/services/prompt_builder.py` | Constructs system prompt (with JSON schema instructions) and user message |
| `backend/services/sizing_engine.py` | Orchestrates: prompt building → Bedrock call → JSON parsing → Pydantic validation, with retry on parse failures |
| `backend/services/report_generator.py` | Renders Markdown, HTML (Jinja2), and JSON serialization |
| `backend/services/database.py` | Async SQLite (aiosqlite) for session history and report storage |
| `backend/models/sizing.py` | Pydantic models for the sizing report (NFRs, service configs, node groups, pod specs, HPAs, etc.) |
| `backend/models/bom.py` | Pydantic models for the BOM (tiers, sections, line items, savings plans) |
| `backend/models/envelope.py` | Combined report envelope with metadata |
| `backend/templates/report.html` | Jinja2 HTML template for the styled report |

### Frontend (React + TypeScript + Vite)

| File | Purpose |
|------|---------|
| `frontend/src/App.tsx` | Main app layout: sidebar (session history) + main area (inputs + results) |
| `frontend/src/api/client.ts` | API client with typed request/response interfaces and error handling |
| `frontend/src/components/UploadPanel.tsx` | Drag-and-drop image upload with preview, validation, and file info |
| `frontend/src/components/NfrDocUpload.tsx` | NFR document upload (.txt, .md) with validation |
| `frontend/src/components/PromptInput.tsx` | Textarea for free-form NFR/volumetric text |
| `frontend/src/components/SubmitButton.tsx` | Submit button with loading state and input validation |
| `frontend/src/components/ProgressIndicator.tsx` | Loading spinner and error display with retry |
| `frontend/src/components/ReportViewer.tsx` | Tabbed viewer: Sizing Report (Markdown), BOM (Markdown), HTML Report (iframe) |
| `frontend/src/components/DownloadManager.tsx` | Individual file downloads + ZIP bundle (using JSZip + file-saver) |
| `frontend/src/components/SessionHistory.tsx` | Sidebar listing past sessions with select/delete |

## Data Flow

1. User provides inputs (diagram, NFR doc, text prompt, region)
2. Frontend sends `POST /api/analyze` as `multipart/form-data`
3. `InputValidator` checks file types, sizes, and ensures at least one input
4. NFR document content is decoded and merged with the text prompt
5. `PromptBuilder` constructs a system prompt with JSON schema instructions and a user message
6. `BedrockClient` sends the multimodal request (image + text) to Amazon Bedrock Converse API
7. `SizingEngine` parses the JSON response into Pydantic models, retrying up to 2 times on parse failures
8. `ReportGenerator` renders Markdown, HTML, and JSON outputs
9. `DatabaseManager` stores the session and reports in SQLite
10. Response returns all report artifacts to the frontend
11. `ReportViewer` displays reports in tabs; `DownloadManager` enables file downloads

## Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- An Amazon Bedrock API key (bearer token)

### Backend

```bash
cd backend
pip install -r requirements.txt
```

Create `backend/.env`:
```
AWS_BEARER_TOKEN_BEDROCK=your-bedrock-api-key-here
```

Start the server:
```bash
# From project root
uvicorn backend.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

### Configuration

Key settings in `backend/config.yaml`:

| Setting | Default | Description |
|---------|---------|-------------|
| `bedrock.region` | `us-east-1` | AWS region for Bedrock API calls |
| `bedrock.model_id` | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | Bedrock model (cross-region inference profile) |
| `bedrock.max_tokens` | `16384` | Max output tokens |
| `bedrock.timeout_seconds` | `120` | Request timeout |
| `app.port` | `8000` | Backend server port |
| `app.cors_origins` | `["http://localhost:5173"]` | Allowed CORS origins |
| `database.path` | `data/sizing_tool.db` | SQLite database path |

All settings can be overridden via environment variables:
- `AWS_DEFAULT_REGION` → `bedrock.region`
- `BEDROCK_MODEL_ID` → `bedrock.model_id`
- `APP_PORT` → `app.port`
- `DATABASE_PATH` → `database.path`

## Testing

```bash
# Backend (from project root)
python -m pytest backend/ -v

# Frontend (from frontend/)
npm test
```

## API Endpoints

### POST /api/analyze
Accepts `multipart/form-data` with:
- `diagram` (file, optional): Architecture diagram image
- `nfr_doc` (file, optional): NFR document (.txt or .md)
- `prompt` (string, optional): Free-form text
- `region` (string, default: "us-east-1"): AWS region

Returns JSON with `session_id`, `sizing_report_md`, `bom_md`, `html_report`, `report_data_json`, `generated_at`.

### GET /api/sessions?page=1&per_page=20
Returns paginated session history.

### GET /api/sessions/{session_id}
Returns full report artifacts for a session.

### DELETE /api/sessions/{session_id}
Deletes a session and its reports. Returns 204.
