import { contextBridge } from 'electron'

contextBridge.exposeInMainWorld('indexmind', {
  platform: process.platform,
})
