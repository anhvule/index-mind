/** The API the preload script exposes to the renderer as `window.indexmind`. */
export type BackendInfo =
  | { state: 'starting' }
  | { state: 'ready'; url: string; docsDir: string }
  | { state: 'failed'; message: string }

export interface IndexMindBridge {
  backend(): Promise<BackendInfo>
  openDocsFolder(): Promise<void>
}

export const Channels = {
  backend: 'indexmind:backend',
  openDocsFolder: 'indexmind:open-docs-folder',
} as const
