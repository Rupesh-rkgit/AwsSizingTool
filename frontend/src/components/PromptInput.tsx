export interface PromptInputProps {
  value: string
  onChange: (value: string) => void
  disabled?: boolean
}

export default function PromptInput({ value, onChange, disabled = false }: PromptInputProps) {
  return (
    <div className="prompt-input">
      <label htmlFor="nfr-prompt" className="prompt-label">
        NFR &amp; Volumetric Details
      </label>
      <textarea
        id="nfr-prompt"
        className="prompt-textarea"
        placeholder="Describe your non-functional requirements, volumetric details, and sizing instructions. For example: latency targets, throughput requirements, batch volumes, scheduling frequencies, expected user counts, data sizes…"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        rows={6}
        aria-label="NFR and volumetric details"
      />
    </div>
  )
}
