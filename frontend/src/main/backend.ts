import { type ChildProcess, spawn } from 'node:child_process'
import { createServer } from 'node:net'
import type { BackendInfo } from '../shared/bridge'

export interface BackendOptions {
  backendDir: string
  docsDir: string
  dataDir: string
  startupTimeoutMs?: number
}

/** Starts the Python backend on a free loopback port and stops it when the app quits. */
export class Backend {
  private child: ChildProcess | null = null
  private info: BackendInfo = { state: 'starting' }
  private readonly log: string[] = []
  private ready: Promise<BackendInfo> | null = null

  constructor(private readonly options: BackendOptions) {}

  start(): Promise<BackendInfo> {
    this.ready ??= this.launch().then(
      (info) => (this.info = info),
      (error: Error) => (this.info = { state: 'failed', message: this.explain(error) }),
    )
    return this.ready
  }

  current(): BackendInfo {
    return this.info
  }

  stop(): void {
    this.child?.kill()
    this.child = null
  }

  private async launch(): Promise<BackendInfo> {
    const { backendDir, docsDir, dataDir, startupTimeoutMs = 60_000 } = this.options
    const port = await freePort()
    const child = spawn('uv', ['run', '--project', backendDir, 'indexmind', '--port', String(port)], {
      cwd: backendDir,
      env: { ...process.env, INDEXMIND_DOCS_DIR: docsDir, INDEXMIND_DATA_DIR: dataDir },
      stdio: ['ignore', 'pipe', 'pipe'],
    })
    this.child = child
    const remember = (chunk: Buffer) => {
      this.log.push(chunk.toString())
      if (this.log.length > 50) this.log.shift()
    }
    child.stdout?.on('data', remember)
    child.stderr?.on('data', remember)

    const exited = new Promise<never>((_, reject) => {
      child.once('error', reject)
      child.once('exit', (code) => reject(new Error(`backend exited with code ${code}`)))
    })
    const url = `http://127.0.0.1:${port}`
    await Promise.race([waitForHealth(url, startupTimeoutMs), exited])
    return { state: 'ready', url, docsDir }
  }

  private explain(error: Error & { code?: string }): string {
    if (error.code === 'ENOENT') {
      return 'Could not find "uv". Install it from https://docs.astral.sh/uv/ and restart IndexMind.'
    }
    const tail = this.log.join('').trim().split('\n').slice(-8).join('\n')
    return tail ? `${error.message}\n\n${tail}` : error.message
  }
}

function freePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = createServer()
    server.once('error', reject)
    server.listen(0, '127.0.0.1', () => {
      const address = server.address()
      server.close(() =>
        typeof address === 'object' && address ? resolve(address.port) : reject(new Error('no port')),
      )
    })
  })
}

async function waitForHealth(url: string, timeoutMs: number): Promise<void> {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${url}/health`)
      if (response.ok) return
    } catch {
      // not listening yet
    }
    await new Promise((resolve) => setTimeout(resolve, 250))
  }
  throw new Error(`backend did not respond within ${timeoutMs / 1000}s`)
}
