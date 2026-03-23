import { useState } from 'react'

export interface SubmitButtonProps {
  hasFile: boolean
  hasPrompt: boolean
  loading: boolean
  onClick: () => void
}

export default function SubmitButton({ hasFile, hasPrompt, loading, onClick }: SubmitButtonProps) {
  const [validationMsg, setValidationMsg] = useState<string | null>(null)

  const hasInput = hasFile || hasPrompt
  const disabled = loading || !hasInput

  function handleClick() {
    if (!hasInput) {
      setValidationMsg('Please provide at least an architecture diagram or a text prompt.')
      return
    }
    setValidationMsg(null)
    onClick()
  }

  return (
    <div className="submit-button-wrapper">
      <button
        type="button"
        className="submit-button"
        disabled={disabled}
        onClick={handleClick}
        aria-label={loading ? 'Analyzing' : 'Analyze'}
      >
        {loading ? 'Analyzing...' : 'Analyze'}
      </button>
      {validationMsg && (
        <p className="submit-validation-error" role="alert">
          {validationMsg}
        </p>
      )}
    </div>
  )
}
