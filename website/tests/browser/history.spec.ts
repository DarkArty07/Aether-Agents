import { test, expect, type Page } from '@playwright/test';

// The ordinary Playwright launch disables bfcache. Use the installed full Chromium
// with that one flag removed so these tests prove a real history restoration, not
// just a new page load or a synthetic PageTransitionEvent.
test.use({
  channel: 'chromium',
  launchOptions: { ignoreDefaultArgs: ['--disable-back-forward-cache'] },
});

type HistoryProbe = { identity: string; restored: number };

async function observeHistory(page: Page) {
  await page.addInitScript(() => {
    const host = window as typeof window & { __aetherHistory: HistoryProbe };
    host.__aetherHistory = { identity: crypto.randomUUID(), restored: 0 };
    window.addEventListener('pageshow', event => {
      if (event.persisted) host.__aetherHistory.restored += 1;
    });
  });
}

async function historyState(page: Page): Promise<HistoryProbe> {
  return page.evaluate(() =>
    (window as typeof window & { __aetherHistory: HistoryProbe }).__aetherHistory,
  );
}

async function visitDocsAndReturn(page: Page, identity: string, count: number) {
  await page.goto('/docs/');
  await expect(page.locator('.docs-index-title')).toBeVisible();
  await page.goBack({ waitUntil: 'commit' });
  await expect.poll(() => historyState(page)).toEqual({ identity, restored: count });
  await expect(page.locator('[data-knowledge-graph]')).toHaveAttribute('data-ready', 'true');
}

test('actual back/forward cache restores graph controls and all motion without duplicate handlers', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await observeHistory(page);
  await page.goto('/#conocimiento');
  const initial = await historyState(page);
  const graph = page.locator('[data-knowledge-graph]');
  const node = page.locator('[data-knowledge-node="code"]');
  const positions = () => page.locator('[data-knowledge-packet]').evaluateAll(packets =>
    packets.map(packet => packet.getAttribute('transform')).join('|'),
  );

  for (let count = 1; count <= 3; count += 1) {
    // One click must select once, even after repeated listener reconstruction.
    await node.click();
    await expect(node).toHaveAttribute('aria-pressed', 'true');
    await expect(graph).toHaveAttribute('data-animating', 'false');
    await visitDocsAndReturn(page, initial.identity, count);
    await page.locator('.knowledge-stage').scrollIntoViewIfNeeded();
    await expect(graph).toHaveAttribute('data-selected', '');
    await expect(node).toHaveAttribute('aria-pressed', 'false');
    await expect(graph).toHaveAttribute('data-animating', 'true');
    const before = await positions();
    await expect.poll(positions).not.toBe(before);
    await page.locator('[data-motion-toggle]').click();
    await expect(page.locator('html')).toHaveAttribute('data-motion', 'paused');
    await expect(graph).toHaveAttribute('data-animating', 'false');
    await page.locator('[data-motion-toggle]').click();
    await expect(page.locator('html')).toHaveAttribute('data-motion', 'running');
  }

  for (const id of ['origen', 'autoria']) {
    await page.locator(`#${id}`).scrollIntoViewIfNeeded();
    await expect(page.locator(`#${id}`)).toHaveAttribute('data-atmosphere-ready', 'true');
    await expect(page.locator(`#${id}`)).toHaveAttribute('data-atmosphere-running', 'true');
    const light = page.locator(`#${id} [data-ether-light]`).first();
    const before = await light.getAttribute('style');
    await expect.poll(() => light.getAttribute('style')).not.toBe(before);
  }
  await page.locator('[data-scene="team"]').scrollIntoViewIfNeeded();
  const packet = page.locator('[data-scene="team"] [data-packet="0"]');
  const before = await packet.getAttribute('transform');
  await expect.poll(() => packet.getAttribute('transform')).not.toBe(before);
  expect(errors).toEqual([]);
});

test('history restoration never resumes paused or reduced motion', async ({ page }) => {
  await observeHistory(page);
  await page.goto('/#conocimiento');
  const initial = await historyState(page);
  await page.locator('.knowledge-stage').scrollIntoViewIfNeeded();
  await expect(page.locator('[data-knowledge-graph]')).toHaveAttribute('data-animating', 'true');
  await page.locator('[data-motion-toggle]').click();

  for (let count = 1; count <= 2; count += 1) {
    if (count === 2) await page.emulateMedia({ reducedMotion: 'reduce' });
    await visitDocsAndReturn(page, initial.identity, count);
    await page.locator('.knowledge-stage').scrollIntoViewIfNeeded();
    await expect(page.locator('html')).toHaveAttribute('data-motion', 'paused');
    const graph = page.locator('[data-knowledge-graph]');
    await expect(graph).toHaveAttribute('data-animating', 'false');
    const positions = () => page.locator('[data-knowledge-packet]').evaluateAll(packets =>
      packets.map(packet => packet.getAttribute('transform')).join('|'),
    );
    const before = await positions();
    await page.waitForTimeout(300);
    expect(await positions()).toBe(before);
    await page.locator('#autoria').scrollIntoViewIfNeeded();
    await expect(page.locator('#autoria')).toHaveAttribute('data-atmosphere-running', 'false');
    const light = page.locator('#autoria [data-ether-light]').first();
    const frozen = await light.getAttribute('style');
    await page.waitForTimeout(250);
    expect(await light.getAttribute('style')).toBe(frozen);
  }
});
