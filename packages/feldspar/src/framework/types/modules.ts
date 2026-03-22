import { Command, CommandSystem, Response } from './commands'
import { LogEntry } from '../logging'

// Structured result returned by the host after processing a CommandSystemDonate.
// Introduced by eyra/mono commit f1395c378 (Jan 20 2026) / eyra/feldspar PR #612
// (draft, feature/live_error_handling). Adopted by what-if-horizon in commit
// 0020453 "wait for donation result (based on PR 612)".
export interface ResponseSystemDonate {
  success: boolean
  key: string
  status: number
  error?: string
}

// Bridge.send is now async: returns ResponseSystemDonate when VITE_ASYNC_DONATIONS=true
// (Eyra's mono responds via MessageChannel), or void for fire-and-forget mode
// (D3I's mono, backwards-compatible default). Pattern from eyra/feldspar PR #612.
export interface Bridge {
  send: (command: CommandSystem) => Promise<ResponseSystemDonate | void>
  sendLogs: (entries: LogEntry[]) => void
}

export interface CommandHandler {
  onCommand: (command: Command) => Promise<Response>
}
