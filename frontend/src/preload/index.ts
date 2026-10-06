import { contextBridge, ipcRenderer } from 'electron'
import { Channels, type IndexMindBridge } from '../shared/bridge'

const bridge: IndexMindBridge = {
  backend: () => ipcRenderer.invoke(Channels.backend),
  openDocsFolder: () => ipcRenderer.invoke(Channels.openDocsFolder),
}

contextBridge.exposeInMainWorld('indexmind', bridge)
