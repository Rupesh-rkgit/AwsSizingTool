import { render, screen, fireEvent } from '@testing-library/react'
import { vi } from 'vitest'
import DownloadManager, { generateFilename, createReportZip } from '../DownloadManager'

vi.mock('file-saver', () => ({
  saveAs: vi.fn(),
}))

import { saveAs } from 'file-saver'

const mockSaveAs = vi.mocked(saveAs)

const defaultProps = {
  sizingReportMd: '# Sizing Report\nContent here',
  bomMd: '# BOM\nCost breakdown',
  htmlReport: '<html><body>Report</body></html>',
  generatedAt: '2025-01-15T10:30:00Z',
}

describe('generateFilename', () => {
  it('produces correct filename with base, date, and extension', () => {
    expect(generateFilename('AWS_Infrastructure_Sizing', '2025-01-15', 'md'))
      .toBe('AWS_Infrastructure_Sizing_2025-01-15.md')
  })

  it('works with different extensions', () => {
    expect(generateFilename('AWS_InfraSizing_Report', '2025-06-01', 'html'))
      .toBe('AWS_InfraSizing_Report_2025-06-01.html')
  })
})

describe('createReportZip', () => {
  it('creates a ZIP blob with 3 files', async () => {
    const { default: JSZip } = await import('jszip')
    const blob = await createReportZip('sizing md', 'bom md', '<html></html>', '2025-01-15')

    expect(blob).toBeInstanceOf(Blob)

    const zip = await JSZip.loadAsync(blob)
    const filenames = Object.keys(zip.files)
    expect(filenames).toHaveLength(3)
    expect(filenames).toContain('AWS_Infrastructure_Sizing_2025-01-15.md')
    expect(filenames).toContain('AWS_Bill_of_Materials_2025-01-15.md')
    expect(filenames).toContain('AWS_InfraSizing_Report_2025-01-15.html')
  })

  it('preserves file content in the ZIP', async () => {
    const { default: JSZip } = await import('jszip')
    const blob = await createReportZip('sizing content', 'bom content', '<html>report</html>', '2025-03-20')

    const zip = await JSZip.loadAsync(blob)
    const sizingContent = await zip.file('AWS_Infrastructure_Sizing_2025-03-20.md')!.async('string')
    const bomContent = await zip.file('AWS_Bill_of_Materials_2025-03-20.md')!.async('string')
    const htmlContent = await zip.file('AWS_InfraSizing_Report_2025-03-20.html')!.async('string')

    expect(sizingContent).toBe('sizing content')
    expect(bomContent).toBe('bom content')
    expect(htmlContent).toBe('<html>report</html>')
  })
})

describe('DownloadManager', () => {
  beforeEach(() => {
    mockSaveAs.mockClear()
  })

  it('renders all individual download buttons', () => {
    render(<DownloadManager {...defaultProps} />)

    expect(screen.getByRole('button', { name: 'Download Sizing Report' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Download BOM' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Download HTML Report' })).toBeInTheDocument()
  })

  it('renders the Download All button', () => {
    render(<DownloadManager {...defaultProps} />)

    expect(screen.getByRole('button', { name: 'Download All' })).toBeInTheDocument()
  })

  it('calls saveAs with correct filename when downloading sizing report', () => {
    render(<DownloadManager {...defaultProps} />)

    fireEvent.click(screen.getByRole('button', { name: 'Download Sizing Report' }))

    expect(mockSaveAs).toHaveBeenCalledOnce()
    const [blob, filename] = mockSaveAs.mock.calls[0]
    expect(blob).toBeInstanceOf(Blob)
    expect(filename).toBe('AWS_Infrastructure_Sizing_2025-01-15.md')
  })

  it('calls saveAs with correct filename when downloading BOM', () => {
    render(<DownloadManager {...defaultProps} />)

    fireEvent.click(screen.getByRole('button', { name: 'Download BOM' }))

    expect(mockSaveAs).toHaveBeenCalledOnce()
    const [blob, filename] = mockSaveAs.mock.calls[0]
    expect(blob).toBeInstanceOf(Blob)
    expect(filename).toBe('AWS_Bill_of_Materials_2025-01-15.md')
  })

  it('calls saveAs with correct filename when downloading HTML report', () => {
    render(<DownloadManager {...defaultProps} />)

    fireEvent.click(screen.getByRole('button', { name: 'Download HTML Report' }))

    expect(mockSaveAs).toHaveBeenCalledOnce()
    const [blob, filename] = mockSaveAs.mock.calls[0]
    expect(blob).toBeInstanceOf(Blob)
    expect(filename).toBe('AWS_InfraSizing_Report_2025-01-15.html')
  })

  it('calls saveAs with ZIP filename when downloading all', async () => {
    render(<DownloadManager {...defaultProps} />)

    fireEvent.click(screen.getByRole('button', { name: 'Download All' }))

    // Wait for async ZIP creation
    await vi.waitFor(() => {
      expect(mockSaveAs).toHaveBeenCalledOnce()
    })

    const [blob, filename] = mockSaveAs.mock.calls[0]
    expect(blob).toBeInstanceOf(Blob)
    expect(filename).toBe('AWS_InfraSizing_Reports_2025-01-15.zip')
  })

  it('extracts date correctly from ISO timestamp', () => {
    render(<DownloadManager {...defaultProps} generatedAt="2024-12-25T23:59:59Z" />)

    fireEvent.click(screen.getByRole('button', { name: 'Download Sizing Report' }))

    const [, filename] = mockSaveAs.mock.calls[0]
    expect(filename).toBe('AWS_Infrastructure_Sizing_2024-12-25.md')
  })
})
