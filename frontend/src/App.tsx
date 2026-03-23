import { useCallback, useEffect, useState } from 'react'
import UploadPanel from './components/UploadPanel'
import PromptInput from './components/PromptInput'
import NfrDocUpload from './components/NfrDocUpload'
import SubmitButton from './components/SubmitButton'
import ProgressIndicator from './components/ProgressIndicator'
import ReportViewer from './components/ReportViewer'
import DownloadManager from './components/DownloadManager'
import SessionHistory from './components/SessionHistory'
import {
  analyzeInputs,
  getSessions,
  getSession,
  deleteSession,
  ApiClientError,
} from './api/client'
import type { AnalyzeResponse, SessionListItem } from './api/client'
import './App.css'

const AWS_REGIONS: { group: string; options: { value: string; label: string }[] }[] = [
  {
    group: '🌎 North America',
    options: [
      { value: 'us-east-1',    label: 'US East – N. Virginia' },
      { value: 'us-east-2',    label: 'US East – Ohio' },
      { value: 'us-west-1',    label: 'US West – N. California' },
      { value: 'us-west-2',    label: 'US West – Oregon' },
      { value: 'ca-central-1', label: 'Canada – Central' },
    ],
  },
  {
    group: '🌍 Europe',
    options: [
      { value: 'eu-west-1',    label: 'Europe – Ireland' },
      { value: 'eu-west-2',    label: 'Europe – London' },
      { value: 'eu-west-3',    label: 'Europe – Paris' },
      { value: 'eu-central-1', label: 'Europe – Frankfurt' },
      { value: 'eu-north-1',   label: 'Europe – Stockholm' },
      { value: 'eu-south-1',   label: 'Europe – Milan' },
    ],
  },
  {
    group: '🌏 Asia Pacific',
    options: [
      { value: 'ap-south-1',     label: 'Asia Pacific – Mumbai' },
      { value: 'ap-southeast-1', label: 'Asia Pacific – Singapore' },
      { value: 'ap-southeast-2', label: 'Asia Pacific – Sydney' },
      { value: 'ap-northeast-1', label: 'Asia Pacific – Tokyo' },
      { value: 'ap-northeast-2', label: 'Asia Pacific – Seoul' },
      { value: 'ap-east-1',      label: 'Asia Pacific – Hong Kong' },
    ],
  },
  {
    group: '🌎 South America',
    options: [
      { value: 'sa-east-1', label: 'South America – São Paulo' },
    ],
  },
  {
    group: '🌍 Middle East & Africa',
    options: [
      { value: 'me-south-1', label: 'Middle East – Bahrain' },
      { value: 'af-south-1', label: 'Africa – Cape Town' },
    ],
  },
]

function formatGeneratedAt(iso: string): string {
  try {
    return new Intl.DateTimeFormat(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZoneName: 'short',
    }).format(new Date(iso))
  } catch {
    return iso
  }
}

type AppView = 'input' | 'result'

export default function App() {
  const [file, setFile] = useState<File | null>(null)
  const [nfrDoc, setNfrDoc] = useState<File | null>(null)
  const [prompt, setPrompt] = useState('')
  const [region, setRegion] = useState('us-east-1')
  // sessionLoading: true only while fetching a past session from the API (quick)
  const [sessionLoading, setSessionLoading] = useState(false)
  // analysisInProgress: true while the background AI analysis HTTP call is running
  // (30-60 s). Does NOT block navigation — a floating toast is shown instead.
  const [analysisInProgress, setAnalysisInProgress] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [report, setReport] = useState<AnalyzeResponse | null>(null)
  const [sessions, setSessions] = useState<SessionListItem[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [view, setView] = useState<AppView>('input')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  const fetchSessions = useCallback(async () => {
    try {
      const data = await getSessions()
      setSessions(data.sessions)
    } catch {
      // silently ignore
    }
  }, [])

  useEffect(() => { void fetchSessions() }, [fetchSessions])

  const handleSubmit = useCallback(async () => {
    if (!prompt.trim() && !file && !nfrDoc) {
      setError('Please provide at least a diagram, NFR document, or text prompt.')
      return
    }
    setAnalysisInProgress(true)
    setError(null)
    try {
      const data = await analyzeInputs(file, prompt, region, nfrDoc)
      setReport(data)
      setActiveSessionId(data.session_id)
      setView('result')
      void fetchSessions()
    } catch (err) {
      if (err instanceof ApiClientError) {
        const details = err.details?.length ? ` ${err.details.join('. ')}` : ''
        setError(`${err.message}.${details}`)
      } else {
        setError('An unexpected error occurred.')
      }
    } finally {
      setAnalysisInProgress(false)
    }
  }, [file, nfrDoc, prompt, region, fetchSessions])

  const handleSelectSession = useCallback(async (id: string) => {
    setSessionLoading(true)
    setError(null)
    try {
      const data = await getSession(id)
      setReport(data)
      setActiveSessionId(id)
      setView('result')
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message)
      } else {
        setError('Failed to load session.')
      }
    } finally {
      setSessionLoading(false)
    }
  }, [])

  const handleDeleteSession = useCallback(async (id: string) => {
    try {
      await deleteSession(id)
      void fetchSessions()
      if (id === activeSessionId) {
        setReport(null)
        setActiveSessionId(null)
        setView('input')
      }
    } catch {
      // silently ignore
    }
  }, [activeSessionId, fetchSessions])

  const handleRetry = useCallback(() => { void handleSubmit() }, [handleSubmit])

  const handleBackToInput = useCallback(() => {
    setView('input')
    setError(null)
  }, [])

  const hasInput = file !== null || nfrDoc !== null || prompt.trim().length > 0

  const activeSession = sessions.find(s => s.id === activeSessionId) ?? null

  return (
    <div className={`app-layout${sidebarCollapsed ? ' sidebar-collapsed' : ''}`}>
      {/* ── Sidebar ── */}
      <aside className="app-sidebar slide-in-left">
        <div className="sidebar-toggle-row">
          {!sidebarCollapsed && (
            <span className="sidebar-label">Past Sessions</span>
          )}
          <button
            className="sidebar-toggle-btn"
            onClick={() => setSidebarCollapsed(c => !c)}
            aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            title={sidebarCollapsed ? 'Expand' : 'Collapse'}
          >
            {sidebarCollapsed ? (
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M6 3l5 5-5 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            )}
          </button>
        </div>

        {!sidebarCollapsed && (
          <SessionHistory
            sessions={sessions}
            onSelectSession={(id) => void handleSelectSession(id)}
            onDeleteSession={(id) => void handleDeleteSession(id)}
            activeSessionId={activeSessionId}
          />
        )}

        {sidebarCollapsed && sessions.length > 0 && (
          <div className="sidebar-collapsed-items">
            {sessions.slice(0, 12).map(s => (
              <button
                key={s.id}
                className={`sidebar-collapsed-dot${s.id === activeSessionId ? ' active' : ''}`}
                onClick={() => void handleSelectSession(s.id)}
                title={s.prompt_snippet || s.created_at}
                aria-label={`Load session`}
              />
            ))}
          </div>
        )}
      </aside>

      {/* ── Main Content ── */}
      <div className="app-content-wrapper">
        {/* Top nav */}
        <header className="app-topnav fade-in-down">
          <button
            className="app-logo-btn"
            onClick={handleBackToInput}
            aria-label="Go to home"
            title="Back to home"
          >
            <div className="app-logo">
              <svg width="34" height="34" viewBox="0 0 34 34" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect width="34" height="34" rx="8" fill="#F97316"/>
                <path d="M17 7L8 12v10l9 5 9-5V12L17 7Z" stroke="#fff" strokeWidth="1.8" strokeLinejoin="round" fill="rgba(255,255,255,0.15)"/>
                <path d="M17 7v15M8 12l9 5 9-5" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <div className="app-nav-brand">
              <h1 className="app-title">AWS Infrastructure Sizing Tool</h1>
              <p className="app-subtitle">Upload diagrams &amp; NFRs — get AI-generated sizing and cost estimates</p>
            </div>
          </button>
          {view === 'result' && report && (
            <div className="topnav-actions">
              <button className="btn-back" onClick={handleBackToInput}>
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <path d="M9 2L4 7l5 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                New Analysis
              </button>
            </div>
          )}
        </header>

        {/* Loading indicator for session loads and errors */}
        <ProgressIndicator loading={sessionLoading} error={error} onRetry={handleRetry} />

        {view === 'input' ? (
          /* ═══════════════════════════════════════
             INPUT VIEW
             ═══════════════════════════════════════ */
          <main className="app-main fade-in-up">
            <div className="view-heading">
              <h2 className="view-title">Analyze Infrastructure</h2>
              <p className="view-desc">Provide an architecture diagram, NFR document, or describe your requirements below.</p>
            </div>

            <section className="app-inputs" aria-label="Analysis inputs">
              <div className="input-grid">
                {/* Diagram upload */}
                <div className="input-card">
                  <div className="input-card-header">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                      <path d="M14 10v2.5A1.5 1.5 0 0112.5 14h-9A1.5 1.5 0 012 12.5V10M11 5L8 2M8 2L5 5M8 2v8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                    <span>Architecture Diagram</span>
                    <span className="input-optional">optional</span>
                  </div>
                  <div className="input-card-body">
                    <UploadPanel file={file} onFileChange={setFile} />
                  </div>
                </div>

                {/* NFR upload */}
                <div className="input-card">
                  <div className="input-card-header">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                      <path d="M9.5 1.5h-6A1.5 1.5 0 002 3v10a1.5 1.5 0 001.5 1.5h9A1.5 1.5 0 0014 13V5.5L9.5 1.5z" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                      <path d="M9.5 1.5V5.5H14M11 9H5M11 11.5H5M6.5 6.5H5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                    <span>NFR Document</span>
                    <span className="input-optional">optional</span>
                  </div>
                  <div className="input-card-body">
                    <NfrDocUpload file={nfrDoc} onFileChange={setNfrDoc} />
                  </div>
                </div>
              </div>

              {/* Prompt */}
              <div className="input-card">
                <div className="input-card-header">
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                    <path d="M14 10.5a1 1 0 01-1 1H4.5L2 14V2.5a1 1 0 011-1h10a1 1 0 011 1v8Z" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                  <span>Requirements &amp; Details</span>
                  <span className="input-optional">optional</span>
                </div>
                <div className="input-card-body">
                  <PromptInput value={prompt} onChange={setPrompt} disabled={sessionLoading} />
                </div>
              </div>

              {/* Region + Submit row */}
              <div className="input-action-row">
                <div className="region-selector">
                  <label htmlFor="region-select">
                    <svg width="13" height="13" viewBox="0 0 13 13" fill="none" style={{display:'inline',verticalAlign:'middle',marginRight:'5px'}}>
                      <circle cx="6.5" cy="6.5" r="5.5" stroke="currentColor" strokeWidth="1.3"/>
                      <path d="M6.5 1C6.5 1 4.5 3.5 4.5 6.5s2 5.5 2 5.5M6.5 1c0 0 2 2.5 2 5.5S6.5 12 6.5 12M1 6.5h11" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round"/>
                    </svg>
                    AWS Region
                  </label>
                  <select
                    id="region-select"
                    value={region}
                    onChange={(e) => setRegion(e.target.value)}
                    disabled={sessionLoading}
                  >
                    {AWS_REGIONS.map(g => (
                      <optgroup key={g.group} label={g.group}>
                        {g.options.map(o => (
                          <option key={o.value} value={o.value}>{o.label}</option>
                        ))}
                      </optgroup>
                    ))}
                  </select>
                </div>

                <SubmitButton
                  hasFile={file !== null}
                  hasPrompt={hasInput}
                  loading={analysisInProgress}
                  onClick={() => void handleSubmit()}
                />
              </div>

              {!hasInput && (
                <p className="input-hint">Provide at least one input: a diagram, NFR document, or text prompt</p>
              )}
            </section>
          </main>

        ) : (
          /* ═══════════════════════════════════════
             RESULT VIEW
             ═══════════════════════════════════════ */
          <main className="app-main result-view fade-in-up">
            {report && (
              <>
                {/* Result header bar */}
                <div className="result-header">
                  <div className="result-header-left">
                    <h2 className="result-title">Report</h2>
                    {report.generated_at && (
                      <span className="result-generated-at">
                        Generated {formatGeneratedAt(report.generated_at)}
                      </span>
                    )}
                    {activeSession && (
                      <span className="result-region-badge">{activeSession.region}</span>
                    )}
                  </div>
                  <div className="result-header-right">
                    <DownloadManager
                      sizingReportMd={report.sizing_report_md}
                      bomMd={report.bom_md}
                      htmlReport={report.html_report}
                      generatedAt={report.generated_at}
                    />
                  </div>
                </div>

                {/* Full-width report viewer */}
                <ReportViewer
                  sizingReportMd={report.sizing_report_md}
                  bomMd={report.bom_md}
                  htmlReport={report.html_report}
                />
              </>
            )}
          </main>
        )}

        <footer className="app-footer">
          <p>&copy; {new Date().getFullYear()} AWS Infrastructure Sizing Tool by Vikas.</p>
        </footer>
      </div>

      {/* ── Analysis-in-progress floating toast ─────────────────────────────
           Shown at bottom-right while the AI analysis HTTP call is running.
           Non-blocking: user can freely browse sessions, view reports, etc.
           The toast disappears and the result view opens when the call finishes.
           ────────────────────────────────────────────────────────────────── */}
      {analysisInProgress && (
        <div className="analysis-toast" role="status" aria-live="polite">
          <div className="analysis-toast-spinner" aria-hidden="true" />
          <div className="analysis-toast-body">
            <span className="analysis-toast-title">Analyzing your infrastructure…</span>
            <span className="analysis-toast-sub">Feel free to browse past sessions. Results will open automatically when ready.</span>
          </div>
        </div>
      )}
    </div>
  )
}
