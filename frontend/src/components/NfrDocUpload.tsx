import { useCallback, useRef, useState } from 'react'

const ACCEPTED_EXTENSIONS = ['txt', 'md']
const MAX_FILE_SIZE = 5 * 1024 * 1024 // 5 MB

export interface NfrDocUploadProps {
  file: File | null
  onFileChange: (file: File | null) => void
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

export default function NfrDocUpload({ file, onFileChange }: NfrDocUploadProps) {
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFile = useCallback(
    (selected: File) => {
      setError(null)
      const ext = getExtension(selected.name)
      if (!ACCEPTED_EXTENSIONS.includes(ext)) {
        setError('Unsupported format. Please upload .txt or .md files.')
        onFileChange(null)
        return
      }
      if (selected.size > MAX_FILE_SIZE) {
        setError('File too large. Maximum size is 5 MB.')
        onFileChange(null)
        return
      }
      onFileChange(selected)
    },
    [onFileChange],
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
    setError(null)
    if (inputRef.current) inputRef.current.value = ''
  }, [onFileChange])

  return (
    <div className="nfr-doc-upload">
      <label className="nfr-doc-label">NFR / Volumetric Document</label>
      {!file ? (
        <button
          type="button"
          className="nfr-doc-browse-btn"
          onClick={() => inputRef.current?.click()}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M14 10v2.667A1.334 1.334 0 0112.667 14H3.333A1.334 1.334 0 012 12.667V10M11.333 5.333L8 2M8 2L4.667 5.333M8 2v8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Upload .txt or .md file
        </button>
      ) : (
        <div className="nfr-doc-file">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M9.333 1.333H4A1.333 1.333 0 002.667 2.667v10.666A1.333 1.333 0 004 14.667h8a1.333 1.333 0 001.333-1.334V5.333l-4-4z" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M9.333 1.333v4h4M10.667 8.667H5.333M10.667 11.333H5.333M6.667 6H5.333" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <span className="nfr-doc-name">{file.name}</span>
          <span className="nfr-doc-size">{formatFileSize(file.size)}</span>
          <button type="button" className="nfr-doc-remove" onClick={handleRemove}>✕</button>
        </div>
      )}
      <input
        ref={inputRef}
        type="file"
        accept=".txt,.md"
        onChange={handleInputChange}
        hidden
      />
      {error && <p className="nfr-doc-error" role="alert">{error}</p>}
    </div>
  )
}
