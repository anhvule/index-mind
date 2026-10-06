import { describe, expect, it } from 'vitest'
import { readEvents } from '../src/renderer/src/lib/sse'

function streamOf(...chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder()
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk))
      controller.close()
    },
  })
}

async function collect(stream: ReadableStream<Uint8Array>) {
  const events = []
  for await (const event of readEvents(stream)) events.push(event)
  return events
}

describe('readEvents', () => {
  it('parses named events', async () => {
    const events = await collect(streamOf('event: token\ndata: {"text":"hi"}\n\n'))

    expect(events).toEqual([{ event: 'token', data: '{"text":"hi"}' }])
  })

  it('reassembles events split across chunks', async () => {
    const events = await collect(streamOf('event: to', 'ken\ndata: {"a"', ':1}\n', '\nevent: done\ndata: {}\n\n'))

    expect(events.map((e) => e.event)).toEqual(['token', 'done'])
    expect(events[0]?.data).toBe('{"a":1}')
  })

  it('joins multi-line data and ignores comments', async () => {
    const events = await collect(streamOf(': keep-alive\ndata: one\ndata: two\n\n'))

    expect(events).toEqual([{ event: 'message', data: 'one\ntwo' }])
  })

  it('handles CRLF line endings and a trailing event without a blank line', async () => {
    const events = await collect(streamOf('event: a\r\ndata: 1\r\n\r\nevent: b\r\ndata: 2'))

    expect(events.map((e) => e.event)).toEqual(['a', 'b'])
  })
})
