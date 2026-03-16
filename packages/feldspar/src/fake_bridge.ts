import { CommandSystem, CommandSystemDonate, CommandSystemExit, isCommandSystemDonate, isCommandSystemExit } from './framework/types/commands'
import { Bridge, ResponseSystemDonate } from './framework/types/modules'

// Updated to match the async Bridge interface introduced in eyra/feldspar PR #612
// (draft, feature/live_error_handling) and adopted by what-if-horizon in commit
// 0020453. handleDataSubmission now always returns a ResponseSystemDonate so that
// local dev/test runs behave consistently whether VITE_ASYNC_DONATIONS is set or not.
export default class FakeBridge implements Bridge {
  async send (command: CommandSystem): Promise<ResponseSystemDonate | void> {
    if (isCommandSystemDonate(command)) {
      return this.handleDataSubmission(command)
    } else if (isCommandSystemExit(command)) {
      this.handleExit(command)
    } else {
      console.log('[FakeBridge] received unknown command: ' + JSON.stringify(command))
    }
  }

  async handleDataSubmission (command: CommandSystemDonate): Promise<ResponseSystemDonate> {
    console.log(`[FakeBridge] received dataSubmission: ${command.key}=${command.json_string}`);
    try {
      const response = await fetch('/data-submission', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({key: command.key, data: command.json_string}),
      });

      if (!response.ok) {
        console.error(`[FakeBridge] Data submission failed with status: ${response.status}`);
        return { success: false, key: command.key, status: response.status, error: `HTTP ${response.status}` }
      } else {
        console.log(`[FakeBridge] Data submission succeeded with status: ${response.status}`);
        return { success: true, key: command.key, status: response.status }
      }
    } catch (error) {
      console.error(`[FakeBridge] Error during data submission:`, error);
      return { success: false, key: command.key, status: 0, error: String(error) }
    }
  }

  handleExit (command: CommandSystemExit): void {
    console.log(`[FakeBridge] received exit: ${command.code}=${command.info}`)
  }
}
