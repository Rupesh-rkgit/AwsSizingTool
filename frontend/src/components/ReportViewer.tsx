import { useCallback, useMemo, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

/**
 * Preprocess report HTML before injecting into the iframe srcDoc:
 * - <base target="_blank"> makes all link navigations open in new tabs,
 *   preventing the iframe from navigating away to the React app.
 * - The injected script intercepts #hash anchor clicks and scrolls
 *   within the iframe instead (since preventDefault stops the base target).
 */
function preprocessHtml(html: string): string {
  const injected = [
    '<base target="_blank">',
    '<script>',
    'document.addEventListener("click", function(e) {',
    '  var a = e.target.closest("a");',
    '  if (!a) return;',
    '  var href = a.getAttribute("href");',
    '  if (href && href.startsWith("#")) {',
    '    e.preventDefault();',
    '    var id = href.slice(1);',
    '    var el = document.getElementById(id);',
    '    if (el) el.scrollIntoView({ behavior: "smooth" });',
    '  }',
    '}, true);',
    '<\/script>',
  ].join('\n')
  if (html.includes('<head>')) return html.replace('<head>', '<head>\n' + injected)
  if (html.includes('</head>')) return html.replace('</head>', injected + '\n</head>')
  return injected + '\n' + html
}

export interface ReportViewerProps {
  sizingReportMd: string
  bomMd: string
  htmlReport: string
}

const TABS = [
  { id: 'sizing', label: 'Sizing Report' },
  { id: 'bom',    label: 'Bill of Materials' },
  { id: 'html',   label: 'HTML Preview' },
] as const

type TabId = (typeof TABS)[number]['id']

function openFullScreen(htmlContent: string) {
  const blob = new Blob([htmlContent], { type: 'text/html' })
  const url = URL.createObjectURL(blob)
  const win = window.open(url, '_blank', 'noopener,noreferrer')
  // Revoke after a tick so the window has time to load
  if (win) {
    win.addEventListener('load', () => URL.revokeObjectURL(url), { once: true })
  }
}

export default function ReportViewer({ sizingReportMd, bomMd, htmlReport }: ReportViewerProps) {
  const [activeTab, setActiveTab] = useState<TabId>('sizing')
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const processedHtml = useMemo(() => preprocessHtml(htmlReport), [htmlReport])

  const handleFullScreen = useCallback(() => {
    openFullScreen(htmlReport)
  }, [htmlReport])

  return (
    <div className="report-viewer">
      {/* Tab bar */}
      <div className="report-tabs-bar">
        <div role="tablist" aria-label="Report tabs" className="report-tabs">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              role="tab"
              id={`tab-${tab.id}`}
              aria-selected={activeTab === tab.id}
              aria-controls={`tabpanel-${tab.id}`}
              className={`report-tab${activeTab === tab.id ? ' report-tab--active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Full-screen button shown only on HTML tab */}
        {activeTab === 'html' && (
          <button
            className="report-fullscreen-btn"
            onClick={handleFullScreen}
            title="Open in new tab for full interactivity"
            aria-label="Open HTML report in full screen"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M2 5V2h3M9 2h3v3M12 9v3H9M5 12H2V9" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Open Full Screen
          </button>
        )}
      </div>

      {/* Sizing Report */}
      {activeTab === 'sizing' && (
        <div
          role="tabpanel"
          id="tabpanel-sizing"
          aria-labelledby="tab-sizing"
          className="report-tabpanel"
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{sizingReportMd}</ReactMarkdown>
        </div>
      )}

      {/* BOM */}
      {activeTab === 'bom' && (
        <div
          role="tabpanel"
          id="tabpanel-bom"
          aria-labelledby="tab-bom"
          className="report-tabpanel"
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{bomMd}</ReactMarkdown>
        </div>
      )}

      {/* HTML Preview */}
      {activeTab === 'html' && (
        <div
          role="tabpanel"
          id="tabpanel-html"
          aria-labelledby="tab-html"
          className="report-iframe-wrapper"
        >
          <div className="report-iframe-notice">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <circle cx="7" cy="7" r="6" stroke="currentColor" strokeWidth="1.3"/>
              <path d="M7 4v3.5M7 9.5v.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
            Preview is read-only in the browser. Click <strong>Open Full Screen</strong> for full interactivity (clickable links, animations, etc.).
          </div>
          <iframe
            ref={iframeRef}
            srcDoc={processedHtml}
            title="HTML Report Preview"
            className="report-iframe"
            /*
             * allow-scripts: enables in-page JS (accordion toggles, etc.)
             * allow-popups: lets non-hash links open in new tabs
             * NOTE: allow-same-origin is intentionally omitted so iframe
             * scripts cannot access or navigate the parent window.
             */
            sandbox="allow-scripts allow-popups"
          />
        </div>
      )}
    </div>
  )
}
