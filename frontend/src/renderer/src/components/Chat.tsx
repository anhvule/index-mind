import { type FormEvent, type KeyboardEvent, useEffect, useRef, useState } from 'react'
import { ask, type Source, type Turn } from '../lib/api'
import { Answer } from './Answer'

interface Message {
  id: number
  question: string
  answer: string
  sources: Source[]
  cited: number[] | null
  error: string | null
  pending: boolean
}

const HISTORY_TURNS = 6

export function Chat({ backendUrl }: { backendUrl: string }) {
  const [messages, setMessages] = useState<Message[]>([])
  const [draft, setDraft] = useState('')
  const abort = useRef<AbortController | null>(null)
  const bottom = useRef<HTMLDivElement>(null)
  const busy = messages.some((m) => m.pending)

  useEffect(() => {
    bottom.current?.scrollIntoView({ block: 'end' })
  }, [messages])

  const update = (id: number, change: (m: Message) => Partial<Message>) =>
    setMessages((all) => all.map((m) => (m.id === id ? { ...m, ...change(m) } : m)))

  async function submit(event?: FormEvent) {
    event?.preventDefault()
    const question = draft.trim()
    if (!question || busy) return

    const history: Turn[] = messages
      .filter((m) => !m.error && m.answer)
      .slice(-HISTORY_TURNS / 2)
      .flatMap((m) => [
        { role: 'user' as const, content: m.question },
        { role: 'assistant' as const, content: m.answer },
      ])
    const id = Date.now()
    setMessages((all) => [
      ...all,
      { id, question, answer: '', sources: [], cited: null, error: null, pending: true },
    ])
    setDraft('')

    const controller = new AbortController()
    abort.current = controller
    try {
      for await (const event of ask(backendUrl, question, history, controller.signal)) {
        if (event.type === 'sources') update(id, () => ({ sources: event.sources }))
        else if (event.type === 'token') update(id, (m) => ({ answer: m.answer + event.text }))
        else if (event.type === 'done') update(id, () => ({ cited: event.cited }))
        else update(id, () => ({ error: event.message }))
      }
    } catch (error) {
      if (!controller.signal.aborted) update(id, () => ({ error: String(error) }))
    } finally {
      update(id, () => ({ pending: false }))
      abort.current = null
    }
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      void submit()
    }
  }

  return (
    <section className="chat">
      <div className="messages">
        {messages.length === 0 && (
          <div className="empty">
            <h1>Ask your documents</h1>
            <p>Answers come only from the files in your folder, with sources you can check.</p>
          </div>
        )}
        {messages.map((m) => (
          <article key={m.id} className="exchange">
            <p className="question">{m.question}</p>
            {m.error ? (
              <p className="error">{m.error}</p>
            ) : m.answer ? (
              <Answer text={m.answer} sources={m.sources} cited={m.cited} />
            ) : (
              <p className="thinking">Searching your documents…</p>
            )}
          </article>
        ))}
        <div ref={bottom} />
      </div>
      <form className="composer" onSubmit={submit}>
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Ask a question…"
          rows={2}
          autoFocus
        />
        {busy ? (
          <button type="button" onClick={() => abort.current?.abort()}>
            Stop
          </button>
        ) : (
          <button type="submit" disabled={!draft.trim()}>
            Ask
          </button>
        )}
      </form>
    </section>
  )
}
