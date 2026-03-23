import type { SessionListItem } from '../api/client'

export interface SessionHistoryProps {
  sessions: SessionListItem[];
  onSelectSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void;
  activeSessionId?: string | null;
  /** When true, all session clicks and deletes are disabled (e.g. during analysis). */
  disabled?: boolean;
}

function formatDate(isoString: string): string {
  try {
    const date = new Date(isoString)
    return date.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return isoString
  }
}

function formatCost(cost: number | null): string {
  if (cost === null || cost === undefined) return 'N/A'
  return `$${cost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function truncate(text: string, maxLength = 80): string {
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength) + '…'
}

export default function SessionHistory({
  sessions,
  onSelectSession,
  onDeleteSession,
  activeSessionId,
  disabled = false,
}: SessionHistoryProps) {
  if (sessions.length === 0) {
    return (
      <aside className="session-history" aria-label="Session history">
        <h2 className="session-history__title">Past Sessions</h2>
        <p className="session-history__empty">No past sessions</p>
      </aside>
    )
  }

  return (
    <aside className={`session-history${disabled ? ' session-history--disabled' : ''}`} aria-label="Session history">
      <h2 className="session-history__title">Past Sessions</h2>
      <ul className="session-history__list" role="list">
        {sessions.map((session) => {
          const isActive = session.id === activeSessionId
          return (
            <li
              key={session.id}
              className={`session-history__item${isActive ? ' session-history__item--active' : ''}`}
            >
              <button
                className="session-history__select-btn"
                onClick={() => onSelectSession(session.id)}
                aria-current={isActive ? 'true' : undefined}
                aria-label={`Load session from ${formatDate(session.created_at)}`}
                disabled={disabled}
                title={disabled ? 'Analysis in progress — please wait' : undefined}
              >
                <span className="session-history__date">
                  {formatDate(session.created_at)}
                </span>
                <span className="session-history__prompt">
                  {truncate(session.prompt_snippet)}
                </span>
                <span className="session-history__meta">
                  <span className="session-history__region">{session.region}</span>
                  {session.had_diagram && (
                    <span className="session-history__diagram-badge" aria-label="Includes diagram">
                      📎
                    </span>
                  )}
                  <span className="session-history__cost">
                    {formatCost(session.total_monthly_cost)}
                  </span>
                </span>
              </button>
              <button
                className="session-history__delete-btn"
                onClick={(e) => {
                  e.stopPropagation()
                  onDeleteSession(session.id)
                }}
                aria-label={`Delete session from ${formatDate(session.created_at)}`}
                disabled={disabled}
              >
                ✕
              </button>
            </li>
          )
        })}
      </ul>
    </aside>
  )
}
