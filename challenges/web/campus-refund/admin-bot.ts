// Admin-bot handler for Bursary (campus-refund.challs.ingeniums.club).
//
// The platform's admin-bot worker runs this code on a fresh Chrome context
// every time a participant submits a link. This source is PUBLIC (GET
// /api/v2/integrations/challs/:id/admin-bot/config), so it never contains a
// secret: the bursar signs in with her password exactly once per job, and
// that password is the team's flag, which the platform attaches to the job
// (ctx.job.flags) — a participant already holding the flag is at the end of
// the challenge anyway.
import { sleep } from 'bun'
import { Challenge, type ChallengeContext } from '../src/types'

const VICTIM = 'bursar'

export const challenge = new Challenge({
  timeoutMilliseconds: 30_000,
  browser: 'chrome',

  // The only thing worth opening is a sandbox page: 12 hex chars, our sha512
  // …12-char page id (app.py). Input values are capped at 1024 chars by rCTF.
  inputs: {
    url: {
      pattern:
        '^https?://campus-refund\\.challs\\.ingeniums\\.club(:9[0-9]+)?/sandbox/[0-9a-f]{12}/?$',
    },
  },

  // Allowlist the challenge host, deny everything else. PAC rules match on
  // strings and never resolve DNS; the catch-all deny stops 127.0.0.1.nip.io
  // style aliases reaching anything inside the VMs.
  restrictDomains: {
    host: {
      allowRegex: [{ pattern: '^campus-refund\\.challs\\.ingeniums\\.club$' }],
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
      ctx.output.info('challenge', 'signing the bursar in', { base })
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
        ctx.output.fatal('challenge', 'the bursar did not sign in')
        return
      }

      ctx.output.info('challenge', 'bursar opens your link', {
        url: ctx.input.url,
      })
      await page.goto(ctx.input.url, { waitUntil: 'networkidle' })
    } catch (err) {
      ctx.output.fatal('challenge', `failed: ${err}`)
      return
    }
    // Her browser sits on the sandbox page a moment: plenty for the
    // auto-submitting form to have posted the refund.
    await sleep(8_000)
  },
})
