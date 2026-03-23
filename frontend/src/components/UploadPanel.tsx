import { useCallback, useEffect, useRef, useState } from 'react'

const ACCEPTED_EXTENSIONS = ['png', 'jpg', 'jpeg', 'webp']
const ACCEPTED_MIME_TYPES = 'image/png,image/jpeg,image/webp'
const MAX_FILE_SIZE = 20 * 1024 * 1024 // 20 MB

export interface UploadPanelProps {
  file: File | null
  onFileChange: (file: File | null) => void
  error?: string
}

function getExtension(filename: string): string {
  const parts = filename.split('.')
  return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : ''
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function validateFile(file: File): string | null {
  const ext = getExtension(file.name)
  if (!ACCEPTED_EXTENSIONS.includes(ext)) {
    return 'Unsupported format. Please upload PNG, JPG, JPEG, or WEBP.'
  }
  if (file.size > MAX_FILE_SIZE) {
    return 'File too large. Maximum size is 20 MB.'
  }
  return null
}

export default function UploadPanel({ file, onFileChange, error }: UploadPanelProps) {
  const [dragOver, setDragOver] = useState(false)
  const [validationError, setValidationError] = useState<string | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (file) {
      const url = URL.createObjectURL(file)
      setPreviewUrl(url)
      return () => URL.revokeObjectURL(url)
    }
    setPreviewUrl(null)
  }, [file])

  const handleFile = useCallback(
    (selected: File) => {
      setValidationError(null)
      const err = validateFile(selected)
      if (err) {
        setValidationError(err)
        onFileChange(null)
        if (inputRef.current) inputRef.current.value = ''
        return
      }
      onFileChange(selected)
    },
    [onFileChange],
  )

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragOver(false)
      const dropped = e.dataTransfer.files[0]
      if (dropped) handleFile(dropped)
    },
    [handleFile],
  )

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selected = e.target.files?.[0]
      if (selected) handleFile(selected)
    },
    [handleFile],
  )

  const handleRemove = useCallback(() => {
    onFileChange(null)
    setValidationError(null)
    if (inputRef.current) inputRef.current.value = ''
  }, [onFileChange])

  const displayError = validationError ?? error

  return (
    <div className="upload-panel">
      {!file ? (
        <div
          role="button"
          tabIndex={0}
          className={`upload-dropzone${dragOver ? ' upload-dropzone--active' : ''}`}
          onDragOver={(e) => {
            e.preventDefault()
            setDragOver(true)
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click()
          }}
          aria-label="Upload architecture diagram"
        >
          <p>Drag &amp; drop an architecture diagram here, or click to browse</p>
          <p className="upload-hint">PNG, JPG, JPEG, or WEBP — max 20 MB</p>
        </div>
      ) : (
        <div className="upload-preview">
          {previewUrl && (
            <img
              src={previewUrl}
              alt="Architecture diagram preview"
              className="upload-preview-image"
            />
          )}
          <div className="upload-file-info">
            <span className="upload-filename">{file.name}</span>
            <span className="upload-filesize">{formatFileSize(file.size)}</span>
          </div>
          <button type="button" className="upload-remove-btn" onClick={handleRemove}>
            Remove
          </button>
        </div>
      )}

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_MIME_TYPES}
        onChange={handleInputChange}
        hidden
        data-testid="file-input"
      />

      {displayError && (
        <p className="upload-error" role="alert">
          {displayError}
        </p>
      )}
    </div>
  )
}
