import { render, screen, fireEvent } from '@testing-library/react'
import SubmitButton from '../SubmitButton'

describe('SubmitButton', () => {
  it('renders with "Analyze" text when idle', () => {
    render(<SubmitButton hasFile={true} hasPrompt={false} loading={false} onClick={() => {}} />)
    expect(screen.getByRole('button', { name: /analyze/i })).toHaveTextContent('Analyze')
  })

  it('is disabled when both hasFile and hasPrompt are false', () => {
    render(<SubmitButton hasFile={false} hasPrompt={false} loading={false} onClick={() => {}} />)
    expect(screen.getByRole('button')).toBeDisabled()
  })

  it('is disabled when loading is true', () => {
    render(<SubmitButton hasFile={true} hasPrompt={true} loading={true} onClick={() => {}} />)
    expect(screen.getByRole('button')).toBeDisabled()
  })

  it('shows "Analyzing..." text when loading', () => {
    render(<SubmitButton hasFile={true} hasPrompt={false} loading={true} onClick={() => {}} />)
    expect(screen.getByRole('button')).toHaveTextContent('Analyzing...')
  })

  it('is enabled when hasFile is true', () => {
    render(<SubmitButton hasFile={true} hasPrompt={false} loading={false} onClick={() => {}} />)
    expect(screen.getByRole('button')).toBeEnabled()
  })

  it('is enabled when hasPrompt is true', () => {
    render(<SubmitButton hasFile={false} hasPrompt={true} loading={false} onClick={() => {}} />)
    expect(screen.getByRole('button')).toBeEnabled()
  })

  it('calls onClick when clicked with valid inputs', () => {
    const onClick = vi.fn()
    render(<SubmitButton hasFile={true} hasPrompt={false} loading={false} onClick={onClick} />)
    fireEvent.click(screen.getByRole('button'))
    expect(onClick).toHaveBeenCalledOnce()
  })

  it('does not show validation message when inputs are present', () => {
    render(<SubmitButton hasFile={true} hasPrompt={false} loading={false} onClick={() => {}} />)
    fireEvent.click(screen.getByRole('button'))
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})
