# AWS Infrastructure Sizing Tool

A web application that analyzes AWS architecture diagrams and non-functional requirements (NFRs) to generate comprehensive infrastructure sizing recommendations and cost estimates using Amazon Bedrock AI.

---

## Quick Start

> **Prerequisites:** Python 3.11+, Node.js 18+, an AWS account with Bedrock access.

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/AwsSizingTool.git
cd AwsSizingTool

# 2. Set up credentials (see "AWS Credentials" section below)
cp backend/.env.example backend/.env
# → edit backend/.env and paste your Bedrock token

# 3. Install & start backend
cd backend
pip install -r requirements.txt
cd ..
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# 4. Install & start frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Project Structure](#2-project-structure)
3. [AWS Credentials Setup](#3-aws-credentials-setup)
4. [Backend Setup](#4-backend-setup)
5. [Frontend Setup](#5-frontend-setup)
6. [Running the Application](#6-running-the-application)
7. [Configuration Reference](#7-configuration-reference)
8. [How to Use the App](#8-how-to-use-the-app)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Prerequisites

| Tool | Minimum Version | Check |
|---|---|---|
| Python | 3.11 | `python --version` |
| pip | 23+ | `pip --version` |
| Node.js | 18.x | `node --version` |
| npm | 9.x | `npm --version` |
| Git | any | `git --version` |
| AWS account | — | with Bedrock enabled in your region |

---

## 2. Project Structure

```
AwsSizingTool/
├── backend/                  # FastAPI Python backend
│   ├── main.py               # API entry point
│   ├── config.py             # Settings loader
│   ├── config.yaml           # Default configuration
│   ├── requirements.txt      # Python dependencies
│   ├── .env.example          # Credentials template (copy → .env)
│   ├── models/               # Pydantic data models
│   ├── services/             # Business logic
│   │   ├── bedrock_client.py # AWS Bedrock API wrapper
│   │   ├── sizing_engine.py  # AI analysis orchestration
│   │   ├── report_generator.py
│   │   ├── database.py       # SQLite session storage
│   │   └── ...
│   └── tests/                # Pytest test suite
├── frontend/                 # React + TypeScript + Vite frontend
│   ├── src/
│   │   ├── App.tsx           # Root component
│   │   ├── api/client.ts     # API client
│   │   └── components/       # UI components
│   ├── package.json
│   └── vite.config.ts        # Dev server + API proxy config
├── data/                     # SQLite DB (auto-created, gitignored)
└── .gitignore
```

---

## 3. AWS Credentials Setup

The backend calls **Amazon Bedrock** to run the AI analysis. You need valid credentials with Bedrock access.

### Option A — Bedrock Bearer Token (recommended for dev)

This is the approach used in `.env.example`. Tokens are short-lived (12 hours) pre-signed URLs.

**How to generate:**

1. Go to [AWS Console → Amazon Bedrock](https://console.aws.amazon.com/bedrock)
2. Ensure **Claude Haiku / Sonnet** model access is enabled in your region (Settings → Model access)
3. Generate a pre-signed bearer token using the AWS CLI:

```bash
aws bedrock generate-api-key \
  --model-id us.anthropic.claude-haiku-4-5-20251001-v1:0 \
  --region us-east-1
```

Or via the Console under **API Keys / Access**.

4. Copy the token and paste it into `backend/.env`:

```env
AWS_BEARER_TOKEN_BEDROCK=bedrock-api-key-<your-token-here>
```

> ⚠️ Tokens expire after **12 hours**. Regenerate and update `.env` when you see `AccessDeniedException`.

---

### Option B — Standard IAM Credentials (long-lived)

If you have an IAM user or role with Bedrock permissions, configure them via the standard boto3 chain:

**Via `~/.aws/credentials`:**

```ini
[default]
aws_access_key_id = AKIA...
aws_secret_access_key = ...
```

**Via environment variables:**

```bash
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=us-east-1
```

The IAM policy must include at minimum:

```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModel",
    "bedrock:Converse"
  ],
  "Resource": "arn:aws:bedrock:us-east-1::foundation-model/*"
}
```

---

## 4. Backend Setup

```bash
# From the repo root
cd backend

# Create and activate a virtual environment (recommended)
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up credentials
cp .env.example .env
# Edit .env and add your AWS_BEARER_TOKEN_BEDROCK
```

The SQLite database is created automatically at `data/sizing_tool.db` on first run — no setup needed.

---

## 5. Frontend Setup

```bash
# From the repo root
cd frontend

# Install dependencies
npm install
```

The frontend proxies all `/api/*` requests to `http://localhost:8000` (configured in `vite.config.ts`). No additional frontend configuration is needed.

---

## 6. Running the Application

Open **two terminals** from the repo root:

### Terminal 1 — Backend

```bash
# Windows (loads .env automatically via load_dotenv)
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# macOS / Linux
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

API docs available at: **http://localhost:8000/docs**

### Terminal 2 — Frontend

```bash
cd frontend
npm run dev
```

You should see:
```
VITE ready in 1234 ms
➜  Local:   http://localhost:5173/
```

Open **http://localhost:5173** in your browser.

---

## 7. Configuration Reference

All backend settings live in `backend/config.yaml`. Environment variables override YAML values.

| Setting | Default | Description |
|---|---|---|
| `bedrock.region` | `us-east-1` | AWS region for Bedrock API calls |
| `bedrock.model_id` | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | Claude model to use |
| `bedrock.max_tokens` | `16384` | Max tokens per API response |
| `bedrock.timeout_seconds` | `120` | Request timeout |
| `database.path` | `data/sizing_tool.db` | SQLite file location |
| `app.cors_origins` | `["http://localhost:5173"]` | Allowed CORS origins |
| `app.max_upload_size_mb` | `20` | Max diagram file size |

**Environment variable overrides:**

| Env Var | Overrides |
|---|---|
| `AWS_BEARER_TOKEN_BEDROCK` | Bedrock auth token |
| `AWS_DEFAULT_REGION` | `bedrock.region` |
| `BEDROCK_MODEL_ID` | `bedrock.model_id` |
| `DATABASE_PATH` | `database.path` |

---

## 8. How to Use the App

1. **Input screen** — Provide one or more of:
   - Upload an **architecture diagram** (PNG/JPG/WEBP, max 20 MB)
   - Upload an **NFR document** (.txt or .md)
   - Type a **text prompt** describing your requirements
   - Select your **AWS region**

2. **Analyze** — Click the **Analyze** button. Analysis typically takes 30–90 seconds. A floating toast shows progress — you can freely browse past sessions while waiting.

3. **Result screen** — View three report tabs:
   - **Sizing Report** — Detailed service configs, node groups, Kubernetes specs
   - **Bill of Materials** — Cost breakdown with monthly/annual totals
   - **HTML Preview** — Styled self-contained report (click **Open Full Screen** for full interactivity)

4. **Download** — Use the buttons in the result header to download reports as Markdown files, HTML, or a ZIP bundle of all three.

5. **Past Sessions** — Previous analyses are saved in the left sidebar. Click any session to reload its report.

---

## 9. Troubleshooting

### `AccessDeniedException: Authentication failed`

Your Bedrock bearer token has expired (12-hour lifetime). Generate a new one and update `backend/.env`. The backend picks it up immediately on next request (no restart needed due to `load_dotenv(override=True)`).

### `502 Bedrock service error`

Usually an expired or invalid token. See above. Also verify:
- Your AWS account has Bedrock enabled in the configured region
- The model ID in `config.yaml` is available in your region

### `Network error. Please check your connection`

The backend is not running or is on a different port. Ensure `uvicorn` is running on port 8000 and the Vite proxy in `vite.config.ts` points to the correct port.

### Port already in use

```bash
# Find and kill the process on port 8000 (macOS/Linux)
lsof -ti:8000 | xargs kill -9

# Windows
netstat -ano | findstr :8000
# then: taskkill /F /PID <PID>
```

### Frontend shows blank page / module errors

```bash
cd frontend
npm install   # reinstall node_modules
npm run dev
```

---

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
