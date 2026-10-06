import { readEvents } from './sse'

export interface Source {
  id: number
  path: string
  page: number | null
  heading: string | null
  excerpt: string
}

export interface Turn {
  role: 'user' | 'assistant'
  content: string
}

export type AskEvent =
  | { type: 'sources'; sources: Source[] }
  | { type: 'token'; text: string }
  | { type: 'done'; cited: number[]; abstained: boolean }
  | { type: 'error'; message: string }

export async function* ask(
  baseUrl: string,
  question: string,
  history: Turn[],
  signal?: AbortSignal,
): AsyncGenerator<AskEvent> {
  const response = await fetch(`${baseUrl}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, history }),
    signal,
  })
  if (!response.ok || !response.body) {
    yield { type: 'error', message: `The backend returned ${response.status}.` }
    return
  }
  for await (const { event, data } of readEvents(response.body)) {
    const payload = JSON.parse(data)
    switch (event) {
      case 'sources':
        yield { type: 'sources', sources: payload.sources }
        break
      case 'token':
        yield { type: 'token', text: payload.text }
        break
      case 'done':
        yield { type: 'done', cited: payload.cited, abstained: payload.abstained }
        break
      case 'error':
        yield { type: 'error', message: payload.message }
        break
    }
  }
}
