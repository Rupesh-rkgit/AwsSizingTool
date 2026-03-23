import { render, screen, fireEvent } from '@testing-library/react'
import PromptInput from '../PromptInput'

describe('PromptInput', () => {
  it('renders a textarea with placeholder text', () => {
    render(<PromptInput value="" onChange={() => {}} />)
    const textarea = screen.getByRole('textbox', { name: /nfr and volumetric details/i })
    expect(textarea).toBeInTheDocument()
    expect(textarea).toHaveAttribute('placeholder', expect.stringContaining('non-functional requirements'))
  })

  it('renders a visible label', () => {
    render(<PromptInput value="" onChange={() => {}} />)
    expect(screen.getByText(/nfr & volumetric details/i)).toBeInTheDocument()
  })

  it('displays the provided value', () => {
    render(<PromptInput value="My NFR text" onChange={() => {}} />)
    expect(screen.getByRole('textbox')).toHaveValue('My NFR text')
  })

  it('calls onChange when user types', () => {
    const onChange = vi.fn()
    render(<PromptInput value="" onChange={onChange} />)
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'new input' } })
    expect(onChange).toHaveBeenCalledWith('new input')
  })

  it('disables the textarea when disabled prop is true', () => {
    render(<PromptInput value="" onChange={() => {}} disabled />)
    expect(screen.getByRole('textbox')).toBeDisabled()
  })

  it('is enabled by default', () => {
    render(<PromptInput value="" onChange={() => {}} />)
    expect(screen.getByRole('textbox')).toBeEnabled()
  })
})
