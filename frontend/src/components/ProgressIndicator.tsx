export interface ProgressIndicatorProps {
  loading: boolean
  error?: string | null
  onRetry?: () => void
}

export default function ProgressIndicator({ loading, error, onRetry }: ProgressIndicatorProps) {
  if (loading) {
    return (
      <div className="progress-indicator" role="status">
        <div className="progress-spinner" aria-hidden="true" />
        <p>Analyzing your architecture...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="progress-indicator progress-indicator--error" role="alert">
        <p className="progress-error-message">{error}</p>
        {onRetry && (
          <button type="button" className="progress-retry-btn" onClick={onRetry}>
            Retry
          </button>
        )}
      </div>
    )
  }

  return null
}
