import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  analyzeInputs,
  getSessions,
  getSession,
  deleteSession,
  ApiClientError,
} from "../client";
import type { AnalyzeResponse, SessionListResponse } from "../client";

const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

beforeEach(() => {
  mockFetch.mockReset();
});

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  } as Response;
}

describe("analyzeInputs", () => {
  const sampleResponse: AnalyzeResponse = {
    session_id: "abc-123",
    sizing_report_md: "# Sizing",
    bom_md: "# BOM",
    html_report: "<html></html>",
    report_data_json: "{}",
    generated_at: "2025-01-15T00:00:00Z",
  };

  it("sends correct FormData with diagram, prompt, and region", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(sampleResponse));

    const file = new File(["img"], "arch.png", { type: "image/png" });
    const result = await analyzeInputs(file, "my prompt", "us-west-2");

    expect(mockFetch).toHaveBeenCalledOnce();
    const [url, options] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/analyze");
    expect(options.method).toBe("POST");

    const body = options.body as FormData;
    expect(body.get("diagram")).toBeInstanceOf(File);
    expect(body.get("prompt")).toBe("my prompt");
    expect(body.get("region")).toBe("us-west-2");
    expect(result).toEqual(sampleResponse);
  });

  it("sends FormData without diagram when null", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(sampleResponse));

    await analyzeInputs(null, "text only", "us-east-1");

    const body = (mockFetch.mock.calls[0] as [string, RequestInit])[1]
      .body as FormData;
    expect(body.get("diagram")).toBeNull();
    expect(body.get("prompt")).toBe("text only");
  });
});

describe("getSessions", () => {
  const sampleList: SessionListResponse = {
    sessions: [
      {
        id: "s1",
        created_at: "2025-01-15T00:00:00Z",
        prompt_snippet: "test",
        region: "us-east-1",
        had_diagram: true,
        total_monthly_cost: 1500,
      },
    ],
    total: 1,
    page: 1,
    per_page: 20,
  };

  it("returns parsed session list", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(sampleList));

    const result = await getSessions();

    expect(mockFetch).toHaveBeenCalledWith(
      "/api/sessions?page=1&per_page=20",
    );
    expect(result).toEqual(sampleList);
  });

  it("passes custom page and perPage", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(sampleList));

    await getSessions(2, 10);

    expect(mockFetch).toHaveBeenCalledWith(
      "/api/sessions?page=2&per_page=10",
    );
  });
});

describe("getSession", () => {
  const sampleSession: AnalyzeResponse = {
    session_id: "abc-123",
    sizing_report_md: "# Sizing",
    bom_md: "# BOM",
    html_report: "<html></html>",
    report_data_json: "{}",
    generated_at: "2025-01-15T00:00:00Z",
  };

  it("returns parsed session response", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(sampleSession));

    const result = await getSession("abc-123");

    expect(mockFetch).toHaveBeenCalledWith("/api/sessions/abc-123");
    expect(result).toEqual(sampleSession);
  });
});

describe("deleteSession", () => {
  it("returns void on 204", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 204,
    } as Response);

    const result = await deleteSession("abc-123");

    expect(mockFetch).toHaveBeenCalledWith("/api/sessions/abc-123", {
      method: "DELETE",
    });
    expect(result).toBeUndefined();
  });
});

describe("API error handling", () => {
  it("throws ApiClientError with server error message on 400", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse(
        { error: "Invalid file format", details: ["Supported formats: PNG"] },
        400,
      ),
    );

    await expect(analyzeInputs(null, "", "us-east-1")).rejects.toThrow(
      ApiClientError,
    );

    try {
      mockFetch.mockResolvedValueOnce(
        jsonResponse(
          {
            error: "Invalid file format",
            details: ["Supported formats: PNG"],
          },
          400,
        ),
      );
      await analyzeInputs(null, "", "us-east-1");
    } catch (e) {
      const err = e as ApiClientError;
      expect(err.message).toBe("Invalid file format");
      expect(err.status).toBe(400);
      expect(err.details).toEqual(["Supported formats: PNG"]);
    }
  });

  it("throws ApiClientError on 404 for getSession", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ error: "Session not found" }, 404),
    );

    await expect(getSession("nonexistent")).rejects.toThrow(ApiClientError);
  });

  it("throws ApiClientError on 404 for deleteSession", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ error: "Session not found" }, 404),
    );

    await expect(deleteSession("nonexistent")).rejects.toThrow(
      ApiClientError,
    );
  });

  it("throws ApiClientError with details on 422", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse(
        {
          error: "Could not generate report",
          details: ["The AI response could not be parsed"],
        },
        422,
      ),
    );

    try {
      await analyzeInputs(null, "test", "us-east-1");
    } catch (e) {
      const err = e as ApiClientError;
      expect(err.message).toBe("Could not generate report");
      expect(err.status).toBe(422);
      expect(err.details).toEqual(["The AI response could not be parsed"]);
    }
  });

  it("throws ApiClientError on 502 Bedrock unavailable", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse(
        {
          error: "Bedrock service unavailable",
          details: ["Rate limit exceeded"],
        },
        502,
      ),
    );

    try {
      await analyzeInputs(null, "test", "us-east-1");
    } catch (e) {
      const err = e as ApiClientError;
      expect(err.message).toBe("Bedrock service unavailable");
      expect(err.status).toBe(502);
      expect(err.details).toEqual(["Rate limit exceeded"]);
    }
  });

  it("throws ApiClientError on 504 timeout", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse(
        {
          error: "Analysis timed out",
          details: ["The Bedrock service took too long to respond."],
        },
        504,
      ),
    );

    try {
      await analyzeInputs(null, "test", "us-east-1");
    } catch (e) {
      const err = e as ApiClientError;
      expect(err.message).toBe("Analysis timed out");
      expect(err.status).toBe(504);
      expect(err.details).toEqual([
        "The Bedrock service took too long to respond.",
      ]);
    }
  });

  it("throws ApiClientError on 500 internal error", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse(
        {
          error: "Internal error",
          details: ["An unexpected error occurred"],
        },
        500,
      ),
    );

    try {
      await analyzeInputs(null, "test", "us-east-1");
    } catch (e) {
      const err = e as ApiClientError;
      expect(err.message).toBe("Internal error");
      expect(err.status).toBe(500);
      expect(err.details).toEqual(["An unexpected error occurred"]);
    }
  });

  it("handles non-JSON error responses gracefully", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: () => Promise.reject(new Error("not json")),
    } as unknown as Response);

    try {
      await analyzeInputs(null, "test", "us-east-1");
    } catch (e) {
      const err = e as ApiClientError;
      expect(err.message).toBe("An unexpected error occurred");
      expect(err.status).toBe(500);
    }
  });
});

describe("Network error handling", () => {
  it("throws descriptive network error for analyzeInputs", async () => {
    mockFetch.mockRejectedValueOnce(new TypeError("Failed to fetch"));

    await expect(
      analyzeInputs(null, "test", "us-east-1"),
    ).rejects.toThrow(
      "Network error. Please check your connection and try again.",
    );
  });

  it("throws descriptive network error for getSessions", async () => {
    mockFetch.mockRejectedValueOnce(new TypeError("Failed to fetch"));

    await expect(getSessions()).rejects.toThrow(
      "Network error. Please check your connection and try again.",
    );
  });

  it("throws descriptive network error for getSession", async () => {
    mockFetch.mockRejectedValueOnce(new TypeError("Failed to fetch"));

    await expect(getSession("abc")).rejects.toThrow(
      "Network error. Please check your connection and try again.",
    );
  });

  it("throws descriptive network error for deleteSession", async () => {
    mockFetch.mockRejectedValueOnce(new TypeError("Failed to fetch"));

    await expect(deleteSession("abc")).rejects.toThrow(
      "Network error. Please check your connection and try again.",
    );
  });
});
