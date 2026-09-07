import { test, expect } from '@playwright/test';

test('opening and finale artwork loads at honest native resolution', async ({page}) => {
  await page.goto('/');
  for (const selector of ['.hero-art img','.finale-art img']) {
    const img=page.locator(selector);
    await img.scrollIntoViewIfNeeded();
    await expect.poll(()=>img.evaluate((el:HTMLImageElement)=>el.complete && el.naturalWidth>0)).toBeTruthy();
    expect(await img.evaluate((el:HTMLImageElement)=>el.naturalWidth)).toBeLessThanOrEqual(1672);
  }
  await expect(page.locator('#autoria')).toContainText('Christopher');
  await expect(page.locator('#autoria .author-handle')).toHaveAttribute('href','https://github.com/DarkArty07');
  await expect(page.locator('#autoria')).not.toContainText('EN CALIFICACIÓN');
});

test('ambient light moves only when visible and the shared controls permit it', async ({page}) => {
  const errors:string[]=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.emulateMedia({reducedMotion:'no-preference'});
  await page.goto('/');
  const hero=page.locator('#origen');
  const finale=page.locator('#autoria');
  await expect(hero).toHaveAttribute('data-atmosphere-running','true');
  const lights=()=>hero.locator('[data-ether-light]').evaluateAll(els=>els.map(el=>el.getAttribute('style')).join('|'));
  const start=await lights();
  await expect.poll(lights).not.toBe(start);
  await page.locator('[data-motion-toggle]').click();
  await expect(hero).toHaveAttribute('data-atmosphere-running','false');
  const frozen=await lights();
  await page.waitForTimeout(300);
  expect(await lights()).toBe(frozen);
  await page.locator('[data-motion-toggle]').click();
  await expect(hero).toHaveAttribute('data-atmosphere-running','true');
  await finale.scrollIntoViewIfNeeded();
  await expect(finale).toHaveAttribute('data-atmosphere-running','true');
  await expect(hero).toHaveAttribute('data-atmosphere-running','false');
  await page.emulateMedia({reducedMotion:'reduce'});
  await expect(finale).toHaveAttribute('data-atmosphere-running','false');
  const finalLights=()=>finale.locator('[data-ether-light]').evaluateAll(els=>els.map(el=>el.getAttribute('style')).join('|'));
  const reduced=await finalLights(); await page.waitForTimeout(300);
  expect(await finalLights()).toBe(reduced);
  expect(errors).toEqual([]);
});

test('artwork never makes essential copy dependent on JavaScript', async ({browser}) => {
  const context=await browser.newContext({javaScriptEnabled:false,viewport:{width:390,height:844}});
  const page=await context.newPage();
  await page.goto('http://127.0.0.1:4321/');
  await expect(page.locator('#origen h2')).toHaveText('Del éter al software.');
  await page.locator('#autoria').scrollIntoViewIfNeeded();
  await expect(page.locator('#autoria .author-handle')).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(391);
  await context.close();
});
