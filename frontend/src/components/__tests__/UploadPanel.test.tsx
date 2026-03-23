import { render, screen, fireEvent } from '@testing-library/react'
import UploadPanel, { validateFile } from '../UploadPanel'

function makeFile(name: string, size: number, type: string): File {
  const buffer = new ArrayBuffer(size)
  return new File([buffer], name, { type })
}

describe('UploadPanel', () => {
  it('renders the upload dropzone when no file is selected', () => {
    render(<UploadPanel file={null} onFileChange={() => {}} />)
    expect(screen.getByRole('button', { name: /upload architecture diagram/i })).toBeInTheDocument()
    expect(screen.getByText(/drag & drop/i)).toBeInTheDocument()
  })

  it('shows error for invalid file type', () => {
    const onFileChange = vi.fn()
    render(<UploadPanel file={null} onFileChange={onFileChange} />)

    const input = screen.getByTestId('file-input') as HTMLInputElement
    const badFile = makeFile('doc.pdf', 1024, 'application/pdf')
    fireEvent.change(input, { target: { files: [badFile] } })

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Unsupported format. Please upload PNG, JPG, JPEG, or WEBP.',
    )
    expect(onFileChange).toHaveBeenCalledWith(null)
  })

  it('shows error for oversized file', () => {
    const onFileChange = vi.fn()
    render(<UploadPanel file={null} onFileChange={onFileChange} />)

    const input = screen.getByTestId('file-input') as HTMLInputElement
    const bigFile = makeFile('big.png', 21 * 1024 * 1024, 'image/png')
    fireEvent.change(input, { target: { files: [bigFile] } })

    expect(screen.getByRole('alert')).toHaveTextContent(
      'File too large. Maximum size is 20 MB.',
    )
    expect(onFileChange).toHaveBeenCalledWith(null)
  })

  it('calls onFileChange with valid file', () => {
    const onFileChange = vi.fn()
    render(<UploadPanel file={null} onFileChange={onFileChange} />)

    const input = screen.getByTestId('file-input') as HTMLInputElement
    const goodFile = makeFile('arch.png', 1024, 'image/png')
    fireEvent.change(input, { target: { files: [goodFile] } })

    expect(onFileChange).toHaveBeenCalledWith(goodFile)
  })

  it('shows preview, file info, and remove button when file is provided', () => {
    const file = makeFile('diagram.png', 2048, 'image/png')
    const onFileChange = vi.fn()
    render(<UploadPanel file={file} onFileChange={onFileChange} />)

    expect(screen.getByAltText('Architecture diagram preview')).toBeInTheDocument()
    expect(screen.getByText('diagram.png')).toBeInTheDocument()
    expect(screen.getByText('2.0 KB')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /remove/i })).toBeInTheDocument()
  })

  it('calls onFileChange(null) when remove button is clicked', () => {
    const file = makeFile('diagram.png', 2048, 'image/png')
    const onFileChange = vi.fn()
    render(<UploadPanel file={file} onFileChange={onFileChange} />)

    fireEvent.click(screen.getByRole('button', { name: /remove/i }))
    expect(onFileChange).toHaveBeenCalledWith(null)
  })

  it('displays external error prop', () => {
    render(<UploadPanel file={null} onFileChange={() => {}} error="Something went wrong" />)
    expect(screen.getByRole('alert')).toHaveTextContent('Something went wrong')
  })

  it('highlights dropzone on drag over', () => {
    render(<UploadPanel file={null} onFileChange={() => {}} />)
    const dropzone = screen.getByRole('button', { name: /upload architecture diagram/i })

    fireEvent.dragOver(dropzone, { dataTransfer: { files: [] } })
    expect(dropzone.className).toContain('upload-dropzone--active')

    fireEvent.dragLeave(dropzone)
    expect(dropzone.className).not.toContain('upload-dropzone--active')
  })
})

describe('validateFile', () => {
  it('accepts valid extensions', () => {
    for (const ext of ['png', 'jpg', 'jpeg', 'webp']) {
      const f = makeFile(`test.${ext}`, 1024, `image/${ext}`)
      expect(validateFile(f)).toBeNull()
    }
  })

  it('rejects unsupported extensions', () => {
    const f = makeFile('test.gif', 1024, 'image/gif')
    expect(validateFile(f)).toBe('Unsupported format. Please upload PNG, JPG, JPEG, or WEBP.')
  })

  it('rejects files over 20 MB', () => {
    const f = makeFile('test.png', 20 * 1024 * 1024 + 1, 'image/png')
    expect(validateFile(f)).toBe('File too large. Maximum size is 20 MB.')
  })

  it('accepts files exactly 20 MB', () => {
    const f = makeFile('test.png', 20 * 1024 * 1024, 'image/png')
    expect(validateFile(f)).toBeNull()
  })
})
