// Admin-bot handler for Open Ticket (helpdesk-thread.challs.ingeniums.club).
//
// The platform's admin-bot worker runs this code on a fresh Chrome context
// every time a participant submits a job. This source is PUBLIC (GET
// /api/v2/integrations/challs/:id/admin-bot/config), so it never contains a
// secret: the support agent signs in with her password exactly once per job,
// and that password is the team's flag, which the platform attaches to the
// job (ctx.job.flags). A participant already holding the flag is at the end
// of the challenge anyway.
import { sleep } from 'bun'
import { Challenge, type ChallengeContext } from '../src/types'

const VICTIM = 'agent'

export const challenge = new Challenge({
  timeoutMilliseconds: 30_000,
  browser: 'chrome',

  // Any path on the challenge host is accepted. The handler only needs the
  // origin: the desk view it opens is the ticket already in the thread.
  inputs: {
    url: {
      pattern:
        '^https?://helpdesk-thread\\.challs\\.ingeniums\\.club(:9[0-9]+)?(/.*)?$',
    },
  },

  // Allowlist the challenge host, deny everything else. PAC rules match on
  // strings and never resolve DNS; the catch-all deny stops 127.0.0.1.nip.io
  // style aliases reaching anything inside the VMs.
  restrictDomains: {
    host: {
      allowRegex: [{ pattern: '^helpdesk-thread\\.challs\\.ingeniums\\.club$' }],
      disallowRegex: [{ pattern: '.*' }],
    },
  },

  hooksConfig: {
    showConsoleLogs: true,
    showBrowserErrors: true,
    showNavigation: true,
    limitTabsNumber: 2,
  },

  handler: async (ctx: ChallengeContext): Promise<void> => {
    const base = new URL(ctx.input.url).origin
    const password = ctx.job.flags[0]?.flag
    if (!password) {
      ctx.output.fatal('challenge', 'the job arrived without the team flag')
      return
    }

    const page = await ctx.browserContext.newPage()
    try {
      ctx.output.info('challenge', 'signing the agent in', { base })
      await page.goto(`${base}/login`, { waitUntil: 'domcontentloaded' })
      const signedIn = await page.evaluate(
        async ({ username, password }) => {
          const response = await fetch('/login', {
            method: 'POST',
            headers: { 'content-type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ username, password }).toString(),
          })
          return response.ok
        },
        { username: VICTIM, password },
      )
      if (!signedIn) {
        ctx.output.fatal('challenge', 'the agent did not sign in')
        return
      }

      // Her desk view of the thread: what she sees there is the desk copy,
      // which renders whatever a customer wrote into the thread.
      ctx.output.info('challenge', 'agent opens the desk thread', {
        url: `${base}/agent/tickets/1`,
      })
      await page.goto(`${base}/agent/tickets/1`, { waitUntil: 'networkidle2' })
    } catch (err) {
      ctx.output.fatal('challenge', `failed: ${err}`)
      return
    }
    // The desk page keeps running while she reads: enough for the message
    // script to reach the ticket API and land the reply in the thread.
    await sleep(8_000)
  },
})
