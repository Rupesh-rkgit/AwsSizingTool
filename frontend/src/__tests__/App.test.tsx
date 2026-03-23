import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import App from '../App'
import type { AnalyzeResponse, SessionListResponse } from '../api/client'

vi.mock('../api/client', () => ({
  analyzeInputs: vi.fn(),
  getSessions: vi.fn(),
  getSession: vi.fn(),
  deleteSession: vi.fn(),
  ApiClientError: class ApiClientError extends Error {
    status: number
    details?: string[]
    constructor(message: string, status: number, details?: string[]) {
      super(message)
      this.name = 'ApiClientError'
      this.status = status
      this.details = details
    }
  },
}))

import { analyzeInputs, getSessions, getSession, ApiClientError } from '../api/client'

const mockAnalyze = vi.mocked(analyzeInputs)
const mockGetSessions = vi.mocked(getSessions)
const mockGetSession = vi.mocked(getSession)

const emptySessionsResponse: SessionListResponse = {
  sessions: [],
  total: 0,
  page: 1,
  per_page: 20,
}

const sampleReport: AnalyzeResponse = {
  session_id: 'sess-123',
  sizing_report_md: '# Sizing Report\nSample sizing content',
  bom_md: '# BOM\nSample BOM content',
  html_report: '<html><body>Report</body></html>',
  report_data_json: '{}',
  generated_at: '2025-01-15T10:00:00Z',
}

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetSessions.mockResolvedValue(emptySessionsResponse)
  })

  it('renders the main sections', async () => {
    render(<App />)

    expect(screen.getByText('AWS Infrastructure Sizing Tool')).toBeInTheDocument()
    expect(screen.getByLabelText('Upload architecture diagram')).toBeInTheDocument()
    expect(screen.getByLabelText('NFR and volumetric details')).toBeInTheDocument()
    expect(screen.getByLabelText('AWS Region')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Analyze' })).toBeInTheDocument()
    expect(screen.getByText('Past Sessions')).toBeInTheDocument()
  })

  it('fetches sessions on mount', async () => {
    render(<App />)

    await waitFor(() => {
      expect(mockGetSessions).toHaveBeenCalledOnce()
    })
  })

  it('submits analysis and shows report on success', async () => {
    mockAnalyze.mockResolvedValue(sampleReport)
    const user = userEvent.setup()

    render(<App />)

    // Type a prompt
    const textarea = screen.getByLabelText('NFR and volumetric details')
    await user.type(textarea, 'Test prompt')

    // Click analyze
    const submitBtn = screen.getByRole('button', { name: 'Analyze' })
    await user.click(submitBtn)

    await waitFor(() => {
      expect(mockAnalyze).toHaveBeenCalledWith(null, 'Test prompt', 'us-east-1', null)
    })

    // Report viewer section should be visible (tabs + content)
    await waitFor(() => {
      expect(screen.getByRole('tablist', { name: 'Report tabs' })).toBeInTheDocument()
    })
    expect(screen.getByText('Sample sizing content')).toBeInTheDocument()

    // Sessions should be refreshed
    expect(mockGetSessions).toHaveBeenCalledTimes(2) // mount + after submit
  })

  it('shows error on API failure', async () => {
    mockAnalyze.mockRejectedValue(
      new ApiClientError('Analysis timed out', 504, ['The Bedrock service took too long to respond.'])
    )
    const user = userEvent.setup()

    render(<App />)

    const textarea = screen.getByLabelText('NFR and volumetric details')
    await user.type(textarea, 'Test prompt')

    const submitBtn = screen.getByRole('button', { name: 'Analyze' })
    await user.click(submitBtn)

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Analysis timed out')
    })
  })

  it('shows retry button on error', async () => {
    mockAnalyze.mockRejectedValue(
      new ApiClientError('Network error', 0)
    )
    const user = userEvent.setup()

    render(<App />)

    const textarea = screen.getByLabelText('NFR and volumetric details')
    await user.type(textarea, 'Test prompt')

    await user.click(screen.getByRole('button', { name: 'Analyze' }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
    })
  })

  it('allows changing the AWS region', async () => {
    mockAnalyze.mockResolvedValue(sampleReport)
    const user = userEvent.setup()

    render(<App />)

    const regionSelect = screen.getByLabelText('AWS Region')
    await user.selectOptions(regionSelect, 'eu-west-1')

    const textarea = screen.getByLabelText('NFR and volumetric details')
    await user.type(textarea, 'Test')

    await user.click(screen.getByRole('button', { name: 'Analyze' }))

    await waitFor(() => {
      expect(mockAnalyze).toHaveBeenCalledWith(null, 'Test', 'eu-west-1', null)
    })
  })

  it('displays 400 validation error with details', async () => {
    mockAnalyze.mockRejectedValue(
      new ApiClientError('Invalid file format', 400, ['Supported formats: PNG, JPG, JPEG, WEBP'])
    )
    const user = userEvent.setup()

    render(<App />)

    const textarea = screen.getByLabelText('NFR and volumetric details')
    await user.type(textarea, 'Test prompt')
    await user.click(screen.getByRole('button', { name: 'Analyze' }))

    await waitFor(() => {
      const alert = screen.getByRole('alert')
      expect(alert).toHaveTextContent('Invalid file format')
      expect(alert).toHaveTextContent('Supported formats: PNG, JPG, JPEG, WEBP')
    })
  })

  it('displays 422 unprocessable error with details', async () => {
    mockAnalyze.mockRejectedValue(
      new ApiClientError('Could not generate report', 422, [
        'The AI response could not be parsed into a valid report. Please try rephrasing your prompt.',
      ])
    )
    const user = userEvent.setup()

    render(<App />)

    const textarea = screen.getByLabelText('NFR and volumetric details')
    await user.type(textarea, 'Test prompt')
    await user.click(screen.getByRole('button', { name: 'Analyze' }))

    await waitFor(() => {
      const alert = screen.getByRole('alert')
      expect(alert).toHaveTextContent('Could not generate report')
      expect(alert).toHaveTextContent('Please try rephrasing your prompt')
    })
  })

  it('displays 502 Bedrock unavailable error', async () => {
    mockAnalyze.mockRejectedValue(
      new ApiClientError('Bedrock service unavailable', 502, ['Rate limit exceeded'])
    )
    const user = userEvent.setup()

    render(<App />)

    const textarea = screen.getByLabelText('NFR and volumetric details')
    await user.type(textarea, 'Test prompt')
    await user.click(screen.getByRole('button', { name: 'Analyze' }))

    await waitFor(() => {
      const alert = screen.getByRole('alert')
      expect(alert).toHaveTextContent('Bedrock service unavailable')
      expect(alert).toHaveTextContent('Rate limit exceeded')
    })
  })

  it('displays 500 internal error', async () => {
    mockAnalyze.mockRejectedValue(
      new ApiClientError('Internal error', 500, ['An unexpected error occurred'])
    )
    const user = userEvent.setup()

    render(<App />)

    const textarea = screen.getByLabelText('NFR and volumetric details')
    await user.type(textarea, 'Test prompt')
    await user.click(screen.getByRole('button', { name: 'Analyze' }))

    await waitFor(() => {
      const alert = screen.getByRole('alert')
      expect(alert).toHaveTextContent('Internal error')
      expect(alert).toHaveTextContent('An unexpected error occurred')
    })
  })

  it('allows modifying inputs and resubmitting after error', async () => {
    // First call fails
    mockAnalyze.mockRejectedValueOnce(
      new ApiClientError('Analysis timed out', 504, ['The Bedrock service took too long to respond.'])
    )
    // Second call succeeds
    mockAnalyze.mockResolvedValueOnce(sampleReport)

    const user = userEvent.setup()
    render(<App />)

    // Submit with initial prompt
    const textarea = screen.getByLabelText('NFR and volumetric details')
    await user.type(textarea, 'Initial prompt')
    await user.click(screen.getByRole('button', { name: 'Analyze' }))

    // Wait for error to appear
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Analysis timed out')
    })

    // Inputs should still be editable — modify the prompt
    expect(textarea).not.toBeDisabled()
    await user.clear(textarea)
    await user.type(textarea, 'Revised prompt')

    // Submit button should be enabled again
    const submitBtn = screen.getByRole('button', { name: 'Analyze' })
    expect(submitBtn).not.toBeDisabled()
    await user.click(submitBtn)

    // Should succeed this time
    await waitFor(() => {
      expect(mockAnalyze).toHaveBeenCalledTimes(2)
      expect(mockAnalyze).toHaveBeenLastCalledWith(null, 'Revised prompt', 'us-east-1', null)
    })

    // Report should be displayed
    await waitFor(() => {
      expect(screen.getByRole('tablist', { name: 'Report tabs' })).toBeInTheDocument()
    })
    // Error should be cleared
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('loads a session when selected from history', async () => {
    mockGetSessions.mockResolvedValue({
      sessions: [
        {
          id: 'sess-abc',
          created_at: '2025-01-14T09:00:00Z',
          prompt_snippet: 'Previous analysis',
          region: 'us-east-1',
          had_diagram: false,
          total_monthly_cost: 1500,
        },
      ],
      total: 1,
      page: 1,
      per_page: 20,
    })
    mockGetSession.mockResolvedValue(sampleReport)
    const user = userEvent.setup()

    render(<App />)

    // Wait for session to appear
    await waitFor(() => {
      expect(screen.getByText('Previous analysis')).toBeInTheDocument()
    })

    // Click the session
    await user.click(screen.getByLabelText(/Load session from/))

    await waitFor(() => {
      expect(mockGetSession).toHaveBeenCalledWith('sess-abc')
    })

    // Report viewer section should be visible
    await waitFor(() => {
      expect(screen.getByRole('tablist', { name: 'Report tabs' })).toBeInTheDocument()
    })
    expect(screen.getByText('Sample sizing content')).toBeInTheDocument()
  })
})
