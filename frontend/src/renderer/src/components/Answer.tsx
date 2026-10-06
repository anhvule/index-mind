import { Fragment, useState } from 'react'
import type { Source } from '../lib/api'

export function sourceLabel(source: Source): string {
  const parts = [source.path]
  if (source.page !== null) parts.push(`p. ${source.page}`)
  if (source.heading) parts.push(source.heading)
  return parts.join(' · ')
}

interface AnswerProps {
  text: string
  sources: Source[]
  cited: number[] | null
}

export function Answer({ text, sources, cited }: AnswerProps) {
  const [open, setOpen] = useState<number | null>(null)
  const known = new Set(sources.map((s) => s.id))
  // Until the answer finishes, show every retrieved source; afterwards only the cited ones.
  const shown = cited === null ? sources : sources.filter((s) => cited.includes(s.id))

  return (
    <div className="answer">
      <p className="answer-text">
        {text.split(/(\[\d+\])/).map((part, i) => {
          const match = /^\[(\d+)\]$/.exec(part)
          const id = match ? Number(match[1]) : null
          if (id === null || !known.has(id)) return <Fragment key={i}>{part}</Fragment>
          return (
            <button key={i} className="cite" onClick={() => setOpen(open === id ? null : id)}>
              {id}
            </button>
          )
        })}
      </p>
      {shown.length > 0 && (
        <ul className="sources">
          {shown.map((source) => (
            <li key={source.id} className={open === source.id ? 'open' : undefined}>
              <button onClick={() => setOpen(open === source.id ? null : source.id)}>
                <span className="cite">{source.id}</span>
                {sourceLabel(source)}
              </button>
              {open === source.id && <blockquote>{source.excerpt}</blockquote>}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
