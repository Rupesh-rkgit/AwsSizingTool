import { render, screen, fireEvent } from '@testing-library/react'
import ProgressIndicator from '../ProgressIndicator'

describe('ProgressIndicator', () => {
  it('shows spinner and loading text when loading', () => {
    render(<ProgressIndicator loading={true} />)
    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.getByText('Analyzing your architecture...')).toBeInTheDocument()
  })

  it('shows error message when error is provided', () => {
    render(<ProgressIndicator loading={false} error="Something went wrong" />)
    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
  })

  it('shows retry button when error and onRetry are provided', () => {
    const onRetry = vi.fn()
    render(<ProgressIndicator loading={false} error="Network error" onRetry={onRetry} />)
    const retryBtn = screen.getByRole('button', { name: /retry/i })
    expect(retryBtn).toBeInTheDocument()
    fireEvent.click(retryBtn)
    expect(onRetry).toHaveBeenCalledOnce()
  })

  it('does not show retry button when onRetry is not provided', () => {
    render(<ProgressIndicator loading={false} error="Network error" />)
    expect(screen.queryByRole('button', { name: /retry/i })).not.toBeInTheDocument()
  })

  it('renders nothing when not loading and no error', () => {
    const { container } = render(<ProgressIndicator loading={false} />)
    expect(container.innerHTML).toBe('')
  })

  it('renders nothing when error is null', () => {
    const { container } = render(<ProgressIndicator loading={false} error={null} />)
    expect(container.innerHTML).toBe('')
  })

  it('prioritizes loading state over error', () => {
    render(<ProgressIndicator loading={true} error="Some error" />)
    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.getByText('Analyzing your architecture...')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})
