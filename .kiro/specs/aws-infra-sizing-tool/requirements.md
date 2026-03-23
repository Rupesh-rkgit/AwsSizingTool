# Requirements Document

## Introduction

The AWS Infrastructure Sizing and Bill of Materials (BOM) Generator is an AI-powered tool that takes architecture diagrams, non-functional requirements (NFRs), volumetric details, and a text prompt as input, and produces detailed AWS infrastructure sizing recommendations and a Bill of Materials with cost estimates. The tool provides a user-friendly web frontend for uploading inputs, viewing generated reports, and downloading output files in multiple formats (Markdown, HTML).

## Glossary

- **Sizing_Engine**: The backend AI service that analyzes inputs (architecture diagrams, NFRs, volumetrics, prompt) and generates infrastructure sizing recommendations and BOM data.
- **Frontend**: The web-based user interface where users upload inputs, configure parameters, view results, and download output files.
- **Architecture_Diagram**: An image file (PNG, JPG, JPEG, or WEBP) depicting the AWS architecture topology and service relationships.
- **NFR**: Non-Functional Requirements — performance, latency, throughput, availability, and other quality attributes that constrain the infrastructure sizing.
- **Volumetrics**: Quantitative workload details such as record counts, request rates, batch frequencies, and data volumes.
- **BOM**: Bill of Materials — an itemized list of AWS services, their specifications, quantities, unit prices, and estimated monthly/annual costs.
- **Sizing_Report**: The generated output containing infrastructure sizing recommendations, resource specifications, latency budgets, pod/node calculations, and cost optimization strategies.
- **Input_Validator**: The component that validates uploaded files and user-provided text inputs before processing.
- **Report_Generator**: The component that formats Sizing_Engine output into downloadable Markdown and HTML report files.
- **Session**: A single user interaction from input submission through report generation and download.

## Requirements

### Requirement 1: Architecture Diagram Upload

**User Story:** As a cloud architect, I want to upload an AWS architecture diagram image, so that the tool can understand the service topology and relationships for sizing.

#### Acceptance Criteria

1. THE Frontend SHALL accept architecture diagram uploads in PNG, JPG, JPEG, and WEBP formats.
2. THE Frontend SHALL display a preview of the uploaded architecture diagram.
3. WHEN an uploaded file exceeds 20 MB, THE Input_Validator SHALL reject the upload and display an error message stating the maximum allowed file size.
4. WHEN an uploaded file is not in a supported image format, THE Input_Validator SHALL reject the upload and display an error message listing the supported formats.
5. THE Frontend SHALL allow the user to remove an uploaded diagram and upload a replacement.

### Requirement 2: NFR and Volumetric Input

**User Story:** As a cloud architect, I want to provide non-functional requirements and volumetric details via a text prompt, so that the tool can size infrastructure to meet specific performance and capacity targets.

#### Acceptance Criteria

1. THE Frontend SHALL provide a text input area for entering NFRs, volumetric details, and sizing instructions.
2. WHEN the text prompt is empty and the user attempts to submit, THE Input_Validator SHALL display an error message requesting at least a text prompt or an architecture diagram.
3. THE Frontend SHALL allow submission with only a text prompt (no diagram), only a diagram (no prompt), or both a text prompt and a diagram.
4. THE Frontend SHALL preserve the text prompt content during the Session until the user clears the input or starts a new Session.

### Requirement 3: AI-Powered Sizing Analysis

**User Story:** As a cloud architect, I want the tool to analyze my architecture diagram and requirements using AI, so that I receive right-sized AWS infrastructure recommendations.

#### Acceptance Criteria

1. WHEN the user submits inputs, THE Sizing_Engine SHALL analyze the architecture diagram (if provided) to identify AWS services and their topological relationships.
2. WHEN the user submits inputs, THE Sizing_Engine SHALL parse NFRs from the text prompt to extract latency targets, throughput requirements, batch processing volumes, and scheduling frequencies.
3. WHEN both an architecture diagram and a text prompt are provided, THE Sizing_Engine SHALL correlate the diagram services with the NFR constraints to produce sizing recommendations.
4. THE Sizing_Engine SHALL generate instance type recommendations with vCPU, memory, and storage specifications for each identified compute resource.
5. THE Sizing_Engine SHALL generate a latency budget breakdown showing expected latency contribution of each component in the request path.
6. THE Sizing_Engine SHALL generate batch processing sizing with pod counts, parallelism settings, and resource requests/limits scaled to the provided volumetrics.
7. THE Sizing_Engine SHALL generate autoscaling configurations (HPA parameters, node group min/max, Karpenter NodePool specs) based on the workload characteristics.
8. IF the Sizing_Engine encounters an unrecognizable architecture diagram, THEN THE Sizing_Engine SHALL return a descriptive error indicating which parts of the diagram could not be interpreted.

### Requirement 4: Bill of Materials Generation

**User Story:** As a cloud architect, I want the tool to generate a detailed Bill of Materials with cost estimates, so that I can understand the financial impact of the recommended infrastructure.

#### Acceptance Criteria

1. THE Sizing_Engine SHALL generate a BOM listing each AWS service, its specification, quantity, unit price, and estimated monthly cost.
2. THE Sizing_Engine SHALL group BOM line items by tier (web application, batch processing, networking, monitoring).
3. THE Sizing_Engine SHALL calculate a monthly cost subtotal for each tier and a total monthly and annual cost estimate.
4. THE Sizing_Engine SHALL include cost comparison scenarios for Savings Plans, Reserved Instances, and Spot pricing where applicable.
5. THE Sizing_Engine SHALL include a BOM line item summary table listing all AWS services/components with their purpose and specification.
6. THE Sizing_Engine SHALL base pricing on the AWS region specified by the user or default to us-east-1 on-demand pricing.

### Requirement 5: Report Output and Formatting

**User Story:** As a cloud architect, I want the sizing results presented in well-formatted reports, so that I can review, share, and archive the recommendations.

#### Acceptance Criteria

1. THE Report_Generator SHALL produce a Sizing Report in Markdown format containing infrastructure sizing recommendations, resource specifications, latency budgets, and autoscaling configurations.
2. THE Report_Generator SHALL produce a BOM document in Markdown format containing the itemized cost breakdown.
3. THE Report_Generator SHALL produce an HTML report combining the Sizing Report and BOM with styled tables, navigation, and a professional layout.
4. WHEN the Report_Generator formats the HTML report, THE Report_Generator SHALL include a table of contents with anchor links to each section.
5. THE Report_Generator SHALL include Kubernetes YAML snippets (Deployment, HPA, Job, Karpenter NodePool specs) in the Sizing Report where applicable.

### Requirement 6: Report Download

**User Story:** As a cloud architect, I want to download the generated reports, so that I can share them with stakeholders and archive them for future reference.

#### Acceptance Criteria

1. THE Frontend SHALL provide download buttons for each generated output file (Sizing Report Markdown, BOM Markdown, HTML Report).
2. WHEN the user clicks a download button, THE Frontend SHALL initiate a file download with a descriptive filename including the generation date.
3. THE Frontend SHALL provide a "Download All" option that bundles all output files into a single ZIP archive for download.

### Requirement 7: Results Display

**User Story:** As a cloud architect, I want to view the generated sizing details and BOM directly in the browser, so that I can review results without downloading files.

#### Acceptance Criteria

1. WHEN report generation completes, THE Frontend SHALL display the Sizing Report and BOM in a readable, formatted view within the browser.
2. THE Frontend SHALL provide tabbed or sectioned navigation to switch between the Sizing Report, BOM, and HTML Report views.
3. THE Frontend SHALL render Markdown tables, code blocks, and structured content with proper formatting in the browser view.

### Requirement 8: Processing Status and Feedback

**User Story:** As a cloud architect, I want to see the processing status while the tool generates my report, so that I know the tool is working and can estimate wait time.

#### Acceptance Criteria

1. WHEN the user submits inputs for processing, THE Frontend SHALL display a progress indicator showing that the Sizing_Engine is analyzing the inputs.
2. WHEN the Sizing_Engine completes processing, THE Frontend SHALL transition from the progress indicator to the results view.
3. IF the Sizing_Engine fails to generate a report, THEN THE Frontend SHALL display a descriptive error message explaining the failure reason.
4. WHILE the Sizing_Engine is processing, THE Frontend SHALL disable the submit button to prevent duplicate submissions.

### Requirement 9: Input Validation and Error Handling

**User Story:** As a cloud architect, I want clear validation feedback on my inputs, so that I can correct issues before submitting for analysis.

#### Acceptance Criteria

1. WHEN the user submits without providing any input (no diagram and no text prompt), THE Input_Validator SHALL display an error message requesting at least one input.
2. IF the uploaded file is corrupted or unreadable, THEN THE Input_Validator SHALL display an error message indicating the file could not be processed.
3. THE Input_Validator SHALL validate all inputs on the client side before sending the request to the Sizing_Engine.
4. IF the Sizing_Engine returns a processing error, THEN THE Frontend SHALL display the error details and allow the user to modify inputs and resubmit.

### Requirement 10: Parse and Print Sizing Report

**User Story:** As a developer, I want the Sizing Report data to be parseable and re-printable, so that the system can reliably serialize and deserialize report data.

#### Acceptance Criteria

1. THE Report_Generator SHALL serialize Sizing Report data into a structured JSON intermediate format before rendering to Markdown or HTML.
2. THE Report_Generator SHALL parse the structured JSON intermediate format back into the internal Sizing Report data model.
3. FOR ALL valid Sizing Report data objects, serializing to JSON then parsing back SHALL produce an equivalent data object (round-trip property).
4. THE Report_Generator SHALL format the structured JSON into Markdown and HTML output without data loss.
