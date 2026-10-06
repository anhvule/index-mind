/// <reference types="vite/client" />

import type { IndexMindBridge } from '../../shared/bridge'

declare global {
  interface Window {
    indexmind: IndexMindBridge
  }
}
