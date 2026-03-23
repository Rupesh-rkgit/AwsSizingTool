import JSZip from 'jszip'
import { saveAs } from 'file-saver'

export interface DownloadManagerProps {
  sizingReportMd: string
  bomMd: string
  htmlReport: string
  generatedAt: string // ISO 8601 timestamp
}

export function generateFilename(baseName: string, date: string, extension: string): string {
  return `${baseName}_${date}.${extension}`
}

export async function createReportZip(
  sizingMd: string,
  bomMd: string,
  htmlReport: string,
  date: string
): Promise<Blob> {
  const zip = new JSZip()
  zip.file(generateFilename('AWS_Infrastructure_Sizing', date, 'md'), sizingMd)
  zip.file(generateFilename('AWS_Bill_of_Materials', date, 'md'), bomMd)
  zip.file(generateFilename('AWS_InfraSizing_Report', date, 'html'), htmlReport)
  return zip.generateAsync({ type: 'blob' })
}

function extractDate(isoTimestamp: string): string {
  return isoTimestamp.slice(0, 10)
}

function downloadBlob(content: string, filename: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType })
  saveAs(blob, filename)
}

export default function DownloadManager({
  sizingReportMd,
  bomMd,
  htmlReport,
  generatedAt,
}: DownloadManagerProps) {
  const date = extractDate(generatedAt)

  const handleDownloadSizing = () => {
    downloadBlob(sizingReportMd, generateFilename('AWS_Infrastructure_Sizing', date, 'md'), 'text/markdown')
  }

  const handleDownloadBom = () => {
    downloadBlob(bomMd, generateFilename('AWS_Bill_of_Materials', date, 'md'), 'text/markdown')
  }

  const handleDownloadHtml = () => {
    downloadBlob(htmlReport, generateFilename('AWS_InfraSizing_Report', date, 'html'), 'text/html')
  }

  const handleDownloadAll = async () => {
    const zipBlob = await createReportZip(sizingReportMd, bomMd, htmlReport, date)
    saveAs(zipBlob, generateFilename('AWS_InfraSizing_Reports', date, 'zip'))
  }

  return (
    <div className="download-manager">
      <div className="download-buttons">
        <button onClick={handleDownloadSizing} aria-label="Download Sizing Report">
          Download Sizing Report
        </button>
        <button onClick={handleDownloadBom} aria-label="Download BOM">
          Download BOM
        </button>
        <button onClick={handleDownloadHtml} aria-label="Download HTML Report">
          Download HTML Report
        </button>
      </div>
      <button onClick={handleDownloadAll} className="download-all-btn" aria-label="Download All">
        Download All
      </button>
    </div>
  )
}
