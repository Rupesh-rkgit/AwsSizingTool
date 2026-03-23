import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import SessionHistory from '../SessionHistory'
import type { SessionListItem } from '../../api/client'

function makeSession(overrides: Partial<SessionListItem> = {}): SessionListItem {
  return {
    id: 'sess-1',
    created_at: '2025-01-15T10:30:00Z',
    prompt_snippet: 'Analyze my EKS architecture for high availability',
    region: 'us-east-1',
    had_diagram: false,
    total_monthly_cost: 1538.93,
    ...overrides,
  }
}

describe('SessionHistory', () => {
  const noop = () => {}

  it('renders empty state when no sessions', () => {
    render(
      <SessionHistory
        sessions={[]}
        onSelectSession={noop}
        onDeleteSession={noop}
      />
    )
    expect(screen.getByText('No past sessions')).toBeInTheDocument()
  })

  it('renders a list of sessions', () => {
    const sessions = [
      makeSession({ id: 'a', prompt_snippet: 'First session' }),
      makeSession({ id: 'b', prompt_snippet: 'Second session' }),
    ]
    render(
      <SessionHistory
        sessions={sessions}
        onSelectSession={noop}
        onDeleteSession={noop}
      />
    )
    expect(screen.getByText('First session')).toBeInTheDocument()
    expect(screen.getByText('Second session')).toBeInTheDocument()
  })

  it('displays region and formatted cost', () => {
    render(
      <SessionHistory
        sessions={[makeSession({ total_monthly_cost: 2500.5 })]}
        onSelectSession={noop}
        onDeleteSession={noop}
      />
    )
    expect(screen.getByText('us-east-1')).toBeInTheDocument()
    expect(screen.getByText('$2,500.50')).toBeInTheDocument()
  })

  it('shows N/A when cost is null', () => {
    render(
      <SessionHistory
        sessions={[makeSession({ total_monthly_cost: null })]}
        onSelectSession={noop}
        onDeleteSession={noop}
      />
    )
    expect(screen.getByText('N/A')).toBeInTheDocument()
  })

  it('shows diagram badge when had_diagram is true', () => {
    render(
      <SessionHistory
        sessions={[makeSession({ had_diagram: true })]}
        onSelectSession={noop}
        onDeleteSession={noop}
      />
    )
    expect(screen.getByLabelText('Includes diagram')).toBeInTheDocument()
  })

  it('does not show diagram badge when had_diagram is false', () => {
    render(
      <SessionHistory
        sessions={[makeSession({ had_diagram: false })]}
        onSelectSession={noop}
        onDeleteSession={noop}
      />
    )
    expect(screen.queryByLabelText('Includes diagram')).not.toBeInTheDocument()
  })

  it('calls onSelectSession when a session is clicked', () => {
    const onSelect = vi.fn()
    render(
      <SessionHistory
        sessions={[makeSession({ id: 'click-me' })]}
        onSelectSession={onSelect}
        onDeleteSession={noop}
      />
    )
    const btn = screen.getByRole('button', { name: /load session/i })
    fireEvent.click(btn)
    expect(onSelect).toHaveBeenCalledWith('click-me')
  })

  it('calls onDeleteSession when delete button is clicked', () => {
    const onDelete = vi.fn()
    render(
      <SessionHistory
        sessions={[makeSession({ id: 'del-me' })]}
        onSelectSession={noop}
        onDeleteSession={onDelete}
      />
    )
    const btn = screen.getByRole('button', { name: /delete session/i })
    fireEvent.click(btn)
    expect(onDelete).toHaveBeenCalledWith('del-me')
  })

  it('highlights the active session', () => {
    const sessions = [
      makeSession({ id: 'a' }),
      makeSession({ id: 'b' }),
    ]
    const { container } = render(
      <SessionHistory
        sessions={sessions}
        onSelectSession={noop}
        onDeleteSession={noop}
        activeSessionId="b"
      />
    )
    const items = container.querySelectorAll('.session-history__item')
    expect(items[0]).not.toHaveClass('session-history__item--active')
    expect(items[1]).toHaveClass('session-history__item--active')
  })

  it('sets aria-current on the active session button', () => {
    render(
      <SessionHistory
        sessions={[makeSession({ id: 'active-one' })]}
        onSelectSession={noop}
        onDeleteSession={noop}
        activeSessionId="active-one"
      />
    )
    const btn = screen.getByRole('button', { name: /load session/i })
    expect(btn).toHaveAttribute('aria-current', 'true')
  })

  it('truncates long prompt snippets', () => {
    const longPrompt = 'A'.repeat(120)
    render(
      <SessionHistory
        sessions={[makeSession({ prompt_snippet: longPrompt })]}
        onSelectSession={noop}
        onDeleteSession={noop}
      />
    )
    expect(screen.getByText('A'.repeat(80) + '…')).toBeInTheDocument()
  })

  it('has proper list semantics', () => {
    render(
      <SessionHistory
        sessions={[makeSession()]}
        onSelectSession={noop}
        onDeleteSession={noop}
      />
    )
    expect(screen.getByRole('list')).toBeInTheDocument()
    expect(screen.getAllByRole('listitem')).toHaveLength(1)
  })
})
