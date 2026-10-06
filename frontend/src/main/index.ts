import { app, BrowserWindow, ipcMain, shell } from 'electron'
import { mkdirSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { Channels } from '../shared/bridge'
import { Backend } from './backend'

const docsDir = process.env['INDEXMIND_DOCS_DIR'] ?? join(app.getPath('documents'), 'IndexMind')

const backend = new Backend({
  // In development the app path is the frontend folder; the backend sits next to it.
  backendDir: process.env['INDEXMIND_BACKEND_DIR'] ?? resolve(app.getAppPath(), '../backend'),
  docsDir,
  dataDir: join(app.getPath('userData'), 'index'),
})

function createWindow(): BrowserWindow {
  const window = new BrowserWindow({
    width: 1100,
    height: 760,
    minWidth: 720,
    minHeight: 480,
    title: 'IndexMind',
    show: false,
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      sandbox: true,
    },
  })

  window.once('ready-to-show', () => window.show())

  // Links (e.g. in answers) open in the user's browser, never inside the app.
  window.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('https://') || url.startsWith('http://')) void shell.openExternal(url)
    return { action: 'deny' }
  })

  if (process.env['ELECTRON_RENDERER_URL']) {
    void window.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    void window.loadFile(join(__dirname, '../renderer/index.html'))
  }
  return window
}

ipcMain.handle(Channels.backend, () => backend.start())
ipcMain.handle(Channels.openDocsFolder, async () => {
  mkdirSync(docsDir, { recursive: true })
  await shell.openPath(docsDir)
})

app.whenReady().then(() => {
  mkdirSync(docsDir, { recursive: true })
  void backend.start()
  createWindow()
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('will-quit', () => backend.stop())
