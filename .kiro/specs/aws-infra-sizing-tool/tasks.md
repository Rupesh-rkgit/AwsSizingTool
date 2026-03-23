# Implementation Plan: AWS Infrastructure Sizing Tool

## Overview

Build a web application with a Python FastAPI backend and React TypeScript frontend that uses Amazon Bedrock (Claude 3.5 Sonnet v2) to analyze architecture diagrams and NFR/volumetric text, producing AWS infrastructure sizing reports and a Bill of Materials. The backend handles AI orchestration, structured data modeling (Pydantic), report rendering (Markdown + HTML via Jinja2), and session persistence (SQLite). The frontend provides upload, input, tabbed report viewing, and ZIP download capabilities.

## Tasks

- [x] 1. Set up project structure, configuration, and data models
  - [x] 1.1 Create backend project structure and install dependencies
    - Create `backend/` directory with `main.py`, `config.py`, `models/`, `services/`, `templates/` directories
    - Create `requirements.txt` with: fastapi, uvicorn, boto3, pydantic, pydantic-settings, aiosqlite, python-multipart, jinja2, pyyaml, python-magic, pytest, hypothesis
    - Create `config.yaml` with all configuration sections (bedrock, aws, app, database, report, logging) as specified in the design
    - _Requirements: 3.1, 3.2, 4.6_

  - [x] 1.2 Implement configuration loading with pydantic-settings
    - Create `backend/config.py` with `BedrockConfig`, `DatabaseConfig`, `AppConfig`, and `Settings` classes
    - Implement YAML file loading with environment variable overrides (env vars take highest priority)
    - Implement the `default_pricing_region` default of "us-east-1"
    - _Requirements: 4.6_

  - [x] 1.3 Implement Pydantic data models for SizingReportData and BOMData
    - Create `backend/models/sizing.py` with all data models: `NFRSummaryItem`, `ServiceConfig`, `ConfigParameter`, `NodeGroupSpec`, `PodSpec`, `HPAConfig`, `LatencyBudgetItem`, `KubernetesManifest`, `BatchJobSpec`, `CostOptimizationStrategy`, `MonitoringMetric`, `SizingReportData`
    - Create `backend/models/bom.py` with: `BOMLineItem`, `BOMTier`, `BOMSection`, `CostSummaryItem`, `SavingsPlanScenario`, `BOMServiceSummary`, `BOMData`
    - Create `backend/models/envelope.py` with: `ReportMetadata`, `ReportEnvelope`
    - Add Pydantic validators for structural invariants (e.g., `min_replicas <= max_replicas`, `vcpu > 0`, `parallelism >= 1`, `monthly_estimate >= 0`)
    - _Requirements: 3.4, 3.5, 3.6, 3.7, 4.1, 4.2, 4.3, 4.4, 4.5, 10.1, 10.2_

  - [x] 1.4 Write property test: SizingReportData structural completeness
    - **Property 4: SizingReportData structural completeness**
    - Generate random valid `SizingReportData` objects with Hypothesis; verify every node group has non-empty `instance_type`, `vcpu > 0`, `memory_gib > 0`; every latency budget item has non-empty `component` and `expected_latency`; every batch job has `parallelism >= 1` and non-empty pod resource fields; every HPA config has `min_replicas <= max_replicas` and `cpu_target_percent > 0`
    - Tag: `Feature: aws-infra-sizing-tool, Property 4: SizingReportData structural completeness`
    - **Validates: Requirements 3.4, 3.5, 3.6, 3.7**

  - [x] 1.5 Write property test: BOMData structural completeness
    - **Property 5: BOMData structural completeness**
    - Generate random valid `BOMData` objects with H32qwypothesis; verify every line item has non-empty `line_item`, `specification`, `quantity`, `unit_price`, and `monthly_estimate >= 0`; every tier has at least one section; `savings_plans` is non-empty; `service_summary` entries have non-empty `service`, `purpose`, `specification`
    - Tag: `Feature: aws-infra-sizing-tool, Property 5: BOMData structural completeness`
    - **Validates: Requirements 4.1, 4.2, 4.4, 4.5**

- [x] 2. Implement input validation (backend and frontend)
  - [x] 2.1 Implement server-side InputValidator
    - Create `backend/services/input_validator.py`
    - Validate file type via magic bytes (accept PNG, JPG, JPEG, WEBP only)
    - Validate file size (reject if > 20 MB / 20,971,520 bytes)
    - Validate at least one input is present (diagram or prompt)
    - Detect corrupted/unreadable images and return descriptive errors
    - Return HTTP 400 with structured error JSON for all validation failures
    - _Requirements: 1.1, 1.3, 1.4, 2.2, 2.3, 9.1, 9.2_

  - [x] 2.2 Write property test: File type validation is exact
    - **Property 1: File type validation is exact**
    - Generate random file extensions/MIME types with fast-check; verify the validator accepts if and only if the format is PNG, JPG, JPEG, or WEBP
    - Tag: `Feature: aws-infra-sizing-tool, Property 1: File type validation is exact`
    - **Validates: Requirements 1.1, 1.4**

  - [x] 2.3 Write property test: File size validation rejects oversized files
    - **Property 2: File size validation rejects oversized files**
    - Generate random file sizes (0 to 100MB) with fast-check; verify the validator rejects if and only if size exceeds 20 MB
    - Tag: `Feature: aws-infra-sizing-tool, Property 2: File size validation rejects oversized files`
    - **Validates: Requirements 1.3**

  - [x] 2.4 Write property test: Input combination validation
    - **Property 3: Input combination validation requires at least one input**
    - Generate all 4 boolean combos of (has_diagram, has_prompt) with fast-check; verify accept iff at least one is true
    - Tag: `Feature: aws-infra-sizing-tool, Property 3: Input combination validation requires at least one input`
    - **Validates: Requirements 2.2, 2.3, 9.1**

- [x] 3. Implement Bedrock integration and Sizing Engine
  - [x] 3.1 Implement BedrockClient wrapper
    - Create `backend/services/bedrock_client.py`
    - Implement `BedrockClient` class wrapping boto3 Bedrock Runtime `converse` API
    - Handle image (base64) + text content blocks in the Converse API request
    - Configure timeout, retries with adaptive exponential backoff, and credential resolution via boto3 chain
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 3.2 Implement PromptBuilder
    - Create `backend/services/prompt_builder.py`
    - Build system prompt with detailed instructions for structured JSON output conforming to `SizingReportData` and `BOMData` schemas
    - Build user message combining the text prompt and image reference
    - Include AWS pricing knowledge and example output sections in the system prompt
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_

  - [x] 3.3 Implement SizingEngine orchestrator
    - Create `backend/services/sizing_engine.py`
    - Orchestrate: receive validated inputs → call PromptBuilder → call BedrockClient → parse response into `SizingReportData` and `BOMData` Pydantic models
    - Implement retry logic for LLM response parse failures (up to 2 retries with corrective prompt)
    - Handle unrecognizable diagram errors from the LLM and return descriptive error
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_

- [x] 4. Checkpoint - Ensure backend core compiles and unit tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement Report Generator (Markdown, HTML, serialization)
  - [x] 5.1 Implement JSON serialization and deserialization
    - Create `backend/services/report_generator.py` with `ReportGenerator` class
    - Implement `serialize(envelope: ReportEnvelope) -> str` using `model_dump_json`
    - Implement `deserialize(json_str: str) -> ReportEnvelope` using `model_validate_json`
    - _Requirements: 10.1, 10.2, 10.3_

  - [x] 5.2 Write property test: Report data round-trip serialization
    - **Property 12: Report data round-trip serialization**
    - Generate random valid `ReportEnvelope` objects with Hypothesis; serialize to JSON then deserialize; verify the result equals the original
    - Tag: `Feature: aws-infra-sizing-tool, Property 12: Report data round-trip serialization`
    - **Validates: Requirements 10.1, 10.2, 10.3**

  - [x] 5.3 Implement Sizing Report Markdown renderer
    - Implement `render_sizing_markdown(data: SizingReportData) -> str`
    - Render all sections: NFR summary, service configs, node groups, pod specs, HPA configs, latency budget, Kubernetes YAML snippets, batch jobs, cost optimization, container best practices, network config, monitoring metrics
    - Include Kubernetes YAML snippets (Deployment, HPA, Job, Karpenter NodePool) from `kubernetes_manifests`
    - _Requirements: 5.1, 5.5, 10.4_

  - [x] 5.4 Write property test: Sizing Markdown contains all report data
    - **Property 7: Sizing Markdown contains all report data**
    - Generate random valid `SizingReportData` with Hypothesis; render to Markdown; verify the output contains every node group's `instance_type`, every latency budget item's `component`, every batch job's `frequency`, and every HPA config's `target_deployment`
    - Tag: `Feature: aws-infra-sizing-tool, Property 7: Sizing Markdown contains all report data`
    - **Validates: Requirements 5.1, 10.4**

  - [x] 5.5 Implement BOM Markdown renderer
    - Implement `render_bom_markdown(data: BOMData) -> str`
    - Render all tiers with sections, line items, subtotals, cost summary, savings plans, service summary, and notes
    - _Requirements: 5.2_

  - [x] 5.6 Write property test: BOM Markdown contains all cost data
    - **Property 8: BOM Markdown contains all cost data**
    - Generate random valid `BOMData` with Hypothesis; render to Markdown; verify the output contains every tier's `tier_name`, every section's `section_name`, and the formatted `total_monthly` value
    - Tag: `Feature: aws-infra-sizing-tool, Property 8: BOM Markdown contains all cost data`
    - **Validates: Requirements 5.2**

  - [x] 5.7 Write property test: BOM cost calculation consistency
    - **Property 6: BOM cost calculation consistency**
    - Generate random `BOMData` with known line item costs using Hypothesis; verify sum of tier subtotals equals `total_monthly` (within 0.01 tolerance), `total_annual` equals `total_monthly * 12` (within 0.12 tolerance), and each tier's subtotal equals sum of its section subtotals
    - Tag: `Feature: aws-infra-sizing-tool, Property 6: BOM cost calculation consistency`
    - **Validates: Requirements 4.3**

  - [x] 5.8 Implement HTML report renderer with Jinja2
    - Create `backend/templates/report.html` Jinja2 template matching the example HTML report style (top bar, TOC sidebar, color-coded sections for architecture/infra/BOM, styled tables, code blocks, summary cards)
    - Implement `render_html_report(sizing: SizingReportData, bom: BOMData) -> str`
    - Include table of contents with anchor links to each section
    - _Requirements: 5.3, 5.4_

  - [x] 5.9 Write property test: HTML report contains both sections with TOC
    - **Property 9: HTML report contains both sections with TOC**
    - Generate random valid `ReportEnvelope` with Hypothesis; render to HTML; verify the output contains at least one element with id matching each TOC anchor, both sizing and BOM sections, and well-formed HTML structure
    - Tag: `Feature: aws-infra-sizing-tool, Property 9: HTML report contains both sections with TOC`
    - **Validates: Requirements 5.3, 5.4**

- [x] 6. Implement SQLite database layer
  - [x] 6.1 Implement DatabaseManager with aiosqlite
    - Create `backend/services/database.py` with `DatabaseManager` class
    - Implement schema creation (sessions + reports tables with indexes as specified in design)
    - Implement session CRUD: create session, update session status, get session, list sessions (paginated, most recent first), delete session (cascade to reports)
    - Implement report storage and retrieval
    - _Requirements: 7.1, 7.2_

- [x] 7. Wire up FastAPI endpoints
  - [x] 7.1 Implement POST /api/analyze endpoint
    - Create `backend/main.py` with FastAPI app, CORS middleware, and the analyze endpoint
    - Accept multipart form data: `diagram` (file, optional), `prompt` (text, optional), `region` (text, default "us-east-1")
    - Wire: InputValidator → SizingEngine → ReportGenerator → DatabaseManager → return all artifacts
    - Store session and reports in SQLite; return `session_id`, `sizing_report_md`, `bom_md`, `html_report`, `report_data_json`, `generated_at`
    - Handle all error conditions with correct HTTP status codes (400, 422, 502, 504, 500)
    - _Requirements: 2.3, 3.1, 3.8, 8.3, 9.1, 9.2, 9.4_

  - [x] 7.2 Implement session history endpoints
    - Implement `GET /api/sessions` with pagination (page, per_page query params)
    - Implement `GET /api/sessions/{id}` returning full report artifacts
    - Implement `DELETE /api/sessions/{id}` with 204 on success, 404 if not found
    - _Requirements: 7.1, 7.2_

- [x] 8. Checkpoint - Ensure all backend tests pass and API is functional
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Create React TypeScript frontend project
  - [x] 9.1 Scaffold frontend project and install dependencies
    - Create `frontend/` directory with Vite + React + TypeScript scaffold
    - Install dependencies: react, react-dom, react-markdown, remark-gfm, jszip, file-saver
    - Install dev dependencies: vitest, fast-check, @types/file-saver
    - Configure Vite proxy to backend (localhost:8000)
    - _Requirements: 1.1, 7.1_

  - [x] 9.2 Implement UploadPanel component
    - Create `frontend/src/components/UploadPanel.tsx`
    - Implement drag-and-drop and click-to-upload for architecture diagram images
    - Show image preview after upload, file info (name, size), and remove/replace button
    - Client-side validation: file type (PNG/JPG/JPEG/WEBP) and size (≤ 20 MB)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 9.3_

  - [x] 9.3 Implement PromptInput component
    - Create `frontend/src/components/PromptInput.tsx`
    - Textarea for NFR/volumetric text input
    - Preserve content during session until user clears or starts new session
    - _Requirements: 2.1, 2.4_

  - [x] 9.4 Implement SubmitButton and ProgressIndicator components
    - Create `frontend/src/components/SubmitButton.tsx` — validates at least one input present, disabled during processing
    - Create `frontend/src/components/ProgressIndicator.tsx` — spinner/progress bar during AI analysis, transitions to results on completion, shows error on failure
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 9.1_

  - [x] 9.5 Implement API client and form submission
    - Create `frontend/src/api/client.ts`
    - Implement `analyzeInputs(diagram: File | null, prompt: string, region: string)` — sends `POST /api/analyze` with multipart form data
    - Implement `getSessions()`, `getSession(id)`, `deleteSession(id)` for session history
    - Handle network errors and display descriptive messages
    - _Requirements: 2.3, 8.3, 9.4_

- [x] 10. Implement report viewing and download
  - [x] 10.1 Implement ReportViewer component with tabs
    - Create `frontend/src/components/ReportViewer.tsx`
    - Tabbed container: Sizing Report tab, BOM tab, HTML Report tab
    - Render Markdown content with formatted tables and code blocks (react-markdown + remark-gfm)
    - HTML Report tab renders the combined HTML report via iframe or dangerouslySetInnerHTML
    - _Requirements: 7.1, 7.2, 7.3_

  - [x] 10.2 Implement DownloadManager component
    - Create `frontend/src/components/DownloadManager.tsx`
    - Individual download buttons for each artifact (Sizing Report MD, BOM MD, HTML Report)
    - Filenames include generation date (e.g., `AWS_Infrastructure_Sizing_2025-01-15.md`)
    - "Download All" button that bundles all files into a ZIP archive using JSZip
    - _Requirements: 6.1, 6.2, 6.3_

  - [x] 10.3 Write property test: Download filenames include generation date
    - **Property 10: Download filenames include generation date**
    - Generate random datetimes with fast-check; verify the filename generation function produces a string containing the YYYY-MM-DD date portion
    - Tag: `Feature: aws-infra-sizing-tool, Property 10: Download filenames include generation date`
    - **Validates: Requirements 6.2**

  - [x] 10.4 Write property test: ZIP bundle contains all report artifacts
    - **Property 11: ZIP bundle contains all report artifacts**
    - Generate random report artifact strings with fast-check; bundle to ZIP; verify the archive contains exactly 3 entries and each entry's content matches the original byte-for-byte
    - Tag: `Feature: aws-infra-sizing-tool, Property 11: ZIP bundle contains all report artifacts`
    - **Validates: Requirements 6.3**

- [x] 11. Implement session history UI
  - [x] 11.1 Implement SessionHistory component
    - Create `frontend/src/components/SessionHistory.tsx`
    - Sidebar or drawer listing past analysis sessions (date, prompt snippet, region, total monthly cost)
    - Click to reload a past report into the ReportViewer
    - _Requirements: 7.1, 7.2_

- [x] 12. Wire frontend App component together
  - [x] 12.1 Assemble App.tsx with all components
    - Create `frontend/src/App.tsx` wiring: UploadPanel + PromptInput + SubmitButton → ProgressIndicator → ReportViewer + DownloadManager + SessionHistory
    - Manage application state: current session, loading state, error state, report data
    - Handle full user flow: input → submit → progress → results → download
    - _Requirements: 1.1, 2.1, 2.3, 7.1, 8.1, 8.2, 8.3, 8.4_

- [x] 13. Checkpoint - Ensure all frontend and backend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. Final integration and validation
  - [x] 14.1 Add client-side validation mirroring server-side rules
    - Ensure frontend validates file type (PNG/JPG/JPEG/WEBP), file size (≤ 20 MB), and at least one input before sending to backend
    - Display appropriate error messages matching the design spec error handling table
    - _Requirements: 9.3, 9.4_

  - [x] 14.2 Wire error handling end-to-end
    - Ensure all backend error responses (400, 422, 502, 504, 500) are caught by the frontend and displayed with descriptive messages
    - Ensure failed sessions are stored in SQLite with `status = 'failed'` and `error_message`
    - Allow user to modify inputs and resubmit after errors
    - _Requirements: 8.3, 9.4_

- [x] 15. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties (Hypothesis for Python, fast-check for TypeScript)
- Unit tests validate specific examples and edge cases
- The backend uses Python (FastAPI, Pydantic, boto3, aiosqlite, Jinja2, Hypothesis)
- The frontend uses TypeScript (React, Vite, JSZip, fast-check, Vitest)
