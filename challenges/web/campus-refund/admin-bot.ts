import { sleep } from 'bun'
import { Challenge, type ChallengeContext } from '../src/types'

const VICTIM = 'bursar'

export const challenge = new Challenge({
  timeoutMilliseconds: 30_000,
  browser: 'chrome',

  inputs: {
    url: {
      pattern:
        '^https?://campus-refund\\.challs\\.ingeniums\\.club(:9[0-9]+)?(/.*)?$',
    },
  },

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
      ctx.output.info('challenge', 'signing the minha officer in', { base })
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
        ctx.output.fatal('challenge', 'the minha officer did not sign in')
        return
      }

      ctx.output.info('challenge', 'the minha officer opens your link', {
        url: ctx.input.url,
      })
      await page.goto(ctx.input.url, { waitUntil: 'networkidle2' })
    } catch (err) {
      ctx.output.fatal('challenge', `failed: ${err}`)
      return
    }
    await sleep(8_000)
  },
})
