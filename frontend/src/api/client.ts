// API client for AWS Infrastructure Sizing Tool backend

export interface AnalyzeResponse {
  session_id: string;
  sizing_report_md: string;
  bom_md: string;
  html_report: string;
  report_data_json: string;
  generated_at: string;
}

export interface SessionListItem {
  id: string;
  created_at: string;
  prompt_snippet: string;
  region: string;
  had_diagram: boolean;
  total_monthly_cost: number | null;
}

export interface SessionListResponse {
  sessions: SessionListItem[];
  total: number;
  page: number;
  per_page: number;
}

export interface ApiError {
  error: string;
  details?: string[];
}

export class ApiClientError extends Error {
  public status: number;
  public details?: string[];

  constructor(message: string, status: number, details?: string[]) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.details = details;
  }
}

const NETWORK_ERROR_MESSAGE =
  "Network error. Please check your connection and try again.";

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let apiError: ApiError;
    try {
      apiError = (await response.json()) as ApiError;
    } catch {
      throw new ApiClientError(
        "An unexpected error occurred",
        response.status,
      );
    }
    throw new ApiClientError(
      apiError.error,
      response.status,
      apiError.details,
    );
  }
  return (await response.json()) as T;
}

export async function analyzeInputs(
  diagram: File | null,
  prompt: string,
  region: string,
  nfrDoc: File | null = null,
): Promise<AnalyzeResponse> {
  const formData = new FormData();
  if (diagram) {
    formData.append("diagram", diagram);
  }
  if (nfrDoc) {
    formData.append("nfr_doc", nfrDoc);
  }
  formData.append("prompt", prompt);
  formData.append("region", region);

  let response: Response;
  try {
    response = await fetch("/api/analyze", {
      method: "POST",
      body: formData,
    });
  } catch {
    throw new ApiClientError(NETWORK_ERROR_MESSAGE, 0);
  }

  return handleResponse<AnalyzeResponse>(response);
}

export async function getSessions(
  page = 1,
  perPage = 20,
): Promise<SessionListResponse> {
  let response: Response;
  try {
    response = await fetch(
      `/api/sessions?page=${page}&per_page=${perPage}`,
    );
  } catch {
    throw new ApiClientError(NETWORK_ERROR_MESSAGE, 0);
  }

  return handleResponse<SessionListResponse>(response);
}

export async function getSession(id: string): Promise<AnalyzeResponse> {
  let response: Response;
  try {
    response = await fetch(`/api/sessions/${id}`);
  } catch {
    throw new ApiClientError(NETWORK_ERROR_MESSAGE, 0);
  }

  return handleResponse<AnalyzeResponse>(response);
}

export async function deleteSession(id: string): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`/api/sessions/${id}`, {
      method: "DELETE",
    });
  } catch {
    throw new ApiClientError(NETWORK_ERROR_MESSAGE, 0);
  }

  if (!response.ok) {
    let apiError: ApiError;
    try {
      apiError = (await response.json()) as ApiError;
    } catch {
      throw new ApiClientError(
        "An unexpected error occurred",
        response.status,
      );
    }
    throw new ApiClientError(
      apiError.error,
      response.status,
      apiError.details,
    );
  }
}
