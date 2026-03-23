import { render, screen, fireEvent } from '@testing-library/react'
import ReportViewer from '../ReportViewer'

const sizingMd = '# Sizing Report\n\n| Service | Type |\n|---|---|\n| EKS | c6i.xlarge |'
const bomMd = '# Bill of Materials\n\nTotal: **$1,500/mo**'
const htmlReport = '<html><body><h1>Combined Report</h1></body></html>'

describe('ReportViewer', () => {
  it('renders all three tabs', () => {
    render(<ReportViewer sizingReportMd={sizingMd} bomMd={bomMd} htmlReport={htmlReport} />)

    expect(screen.getByRole('tab', { name: 'Sizing Report' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'BOM' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'HTML Report' })).toBeInTheDocument()
  })

  it('defaults to the Sizing Report tab', () => {
    render(<ReportViewer sizingReportMd={sizingMd} bomMd={bomMd} htmlReport={htmlReport} />)

    const sizingTab = screen.getByRole('tab', { name: 'Sizing Report' })
    expect(sizingTab).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('tabpanel')).toHaveAttribute('id', 'tabpanel-sizing')
    // Sizing Report text appears in both the tab and the rendered markdown heading
    expect(screen.getByRole('heading', { name: 'Sizing Report' })).toBeInTheDocument()
  })

  it('renders sizing markdown content with tables', () => {
    render(<ReportViewer sizingReportMd={sizingMd} bomMd={bomMd} htmlReport={htmlReport} />)

    expect(screen.getByRole('table')).toBeInTheDocument()
    expect(screen.getByText('EKS')).toBeInTheDocument()
    expect(screen.getByText('c6i.xlarge')).toBeInTheDocument()
  })

  it('switches to BOM tab and shows BOM content', () => {
    render(<ReportViewer sizingReportMd={sizingMd} bomMd={bomMd} htmlReport={htmlReport} />)

    fireEvent.click(screen.getByRole('tab', { name: 'BOM' }))

    const bomTab = screen.getByRole('tab', { name: 'BOM' })
    expect(bomTab).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('tabpanel')).toHaveAttribute('id', 'tabpanel-bom')
    expect(screen.getByText('Bill of Materials')).toBeInTheDocument()
    expect(screen.getByText('$1,500/mo')).toBeInTheDocument()
  })

  it('switches to HTML Report tab and shows iframe', () => {
    render(<ReportViewer sizingReportMd={sizingMd} bomMd={bomMd} htmlReport={htmlReport} />)

    fireEvent.click(screen.getByRole('tab', { name: 'HTML Report' }))

    const htmlTab = screen.getByRole('tab', { name: 'HTML Report' })
    expect(htmlTab).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('tabpanel')).toHaveAttribute('id', 'tabpanel-html')

    const iframe = screen.getByTitle('HTML Report')
    expect(iframe).toBeInTheDocument()
    expect(iframe.tagName).toBe('IFRAME')
    expect(iframe).toHaveAttribute('srcdoc', htmlReport)
  })

  it('uses proper ARIA attributes for accessibility', () => {
    render(<ReportViewer sizingReportMd={sizingMd} bomMd={bomMd} htmlReport={htmlReport} />)

    const tablist = screen.getByRole('tablist')
    expect(tablist).toHaveAttribute('aria-label', 'Report tabs')

    const sizingTab = screen.getByRole('tab', { name: 'Sizing Report' })
    expect(sizingTab).toHaveAttribute('aria-controls', 'tabpanel-sizing')
    expect(sizingTab).toHaveAttribute('id', 'tab-sizing')

    const panel = screen.getByRole('tabpanel')
    expect(panel).toHaveAttribute('aria-labelledby', 'tab-sizing')
  })

  it('only shows one tabpanel at a time', () => {
    render(<ReportViewer sizingReportMd={sizingMd} bomMd={bomMd} htmlReport={htmlReport} />)

    expect(screen.getAllByRole('tabpanel')).toHaveLength(1)

    fireEvent.click(screen.getByRole('tab', { name: 'BOM' }))
    expect(screen.getAllByRole('tabpanel')).toHaveLength(1)

    fireEvent.click(screen.getByRole('tab', { name: 'HTML Report' }))
    expect(screen.getAllByRole('tabpanel')).toHaveLength(1)
  })
})
