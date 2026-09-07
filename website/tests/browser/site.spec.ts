import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('Spanish page, artwork, sections and no horizontal overflow',async ({page},testInfo)=>{
  const errors:string[]=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/');
  await page.evaluate(()=>document.fonts.ready);
  await expect(page.locator('[data-section]')).toHaveCount(8);
  await expect(page.locator('#origen h2')).toHaveText('Del éter al software.');
  await expect(page.locator('#autoria')).toContainText('Christopher');
  for(const id of ['origen','desarrollo','equipo','proceso','conocimiento','control','fundamentos','autoria']){
    await page.locator(`#${id}`).scrollIntoViewIfNeeded();
    await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
  }
  const images=await page.locator('main img').evaluateAll(imgs=>imgs.map(el=>({complete:(el as HTMLImageElement).complete,width:(el as HTMLImageElement).naturalWidth})));
  expect(images.every(i=>i.complete&&i.width>0)).toBeTruthy();
  expect(errors).toEqual([]);
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.evaluate(()=>window.scrollTo({top:0,behavior:'instant'}));
  await page.screenshot({path:`test-results/${testInfo.project.name}-hero.png`});
  await page.screenshot({path:`test-results/${testInfo.project.name}-full.png`,fullPage:true});
});

test('all copy remains visible with JavaScript disabled',async({browser},testInfo)=>{
  const context=await browser.newContext({javaScriptEnabled:false,viewport:testInfo.project.name==='mobile'?{width:390,height:844}:{width:1440,height:1000}});
  const page=await context.newPage(); await page.goto('http://127.0.0.1:4321/');
  await expect(page.locator('#origen h2')).toBeVisible();
  for(const id of ['desarrollo','equipo','proceso','conocimiento','control','fundamentos','autoria']){
    await expect(page.locator(`#${id} h2`)).toBeVisible();
  }
  await context.close();
});

test('motion advances, pauses, persists and honors reduced motion',async({page})=>{
  await page.goto('/');
  await page.locator('#equipo').scrollIntoViewIfNeeded();
  const moving=page.locator('[data-scene="team"] [data-packet="0"]');
  const before=await moving.getAttribute('transform');
  await expect.poll(()=>moving.getAttribute('transform')).not.toBe(before);
  await page.locator('[data-motion-toggle]').click();
  await expect(page.locator('html')).toHaveAttribute('data-motion','paused');
  const frozen=await moving.getAttribute('transform');
  await page.waitForTimeout(250);
  expect(await moving.getAttribute('transform')).toBe(frozen);
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-motion','paused');
  await page.locator('[data-motion-toggle]').click();
  await expect(page.locator('html')).toHaveAttribute('data-motion','running');
  await page.emulateMedia({reducedMotion:'reduce'});
  await expect(page.locator('html')).toHaveAttribute('data-motion','paused');
});

test('illustrations contain branching, reverse and rework phases',async({page})=>{
  test.setTimeout(90000);
  await page.goto('/');
  // Observe the real requestAnimationFrame clock and visibility handling. Installing
  // a synthetic clock after page load invalidates the animation's existing origin.
  await page.locator('[data-scene="team"]').scrollIntoViewIfNeeded();
  await expect(page.locator('[data-scene="team"]')).toHaveAttribute('data-phase','2',{timeout:15000});
  await expect(page.locator('[data-scene="team"] [data-packet][opacity="1"]')).toHaveCount(3);
  await expect(page.locator('[data-scene="team"]')).toHaveAttribute('data-phase','5',{timeout:20000});
  await page.locator('[data-scene="process"]').scrollIntoViewIfNeeded();
  await expect(page.locator('[data-scene="process"]')).toHaveAttribute('data-stage','4',{timeout:20000});
  await expect(page.locator('[data-scene="process"]')).toHaveAttribute('data-stage','3',{timeout:7000});
});

test('language switch preserves section; mobile menu works',async({page},testInfo)=>{
  await page.goto('/#equipo');
  if(testInfo.project.name==='mobile'){
    await page.locator('.mobile-nav summary').click();
    await expect(page.locator('.mobile-nav nav')).toBeVisible();
    await page.locator('.mobile-nav a[href="/#proceso"]').click();
    await expect(page.locator('.mobile-nav')).not.toHaveAttribute('open','');
    await expect(page).toHaveURL(/#proceso$/);
  }
  await page.locator('[data-language][lang="en"]').click();
  await expect(page.locator('html')).toHaveAttribute('lang','en');
  await expect(page).toHaveURL(/\/en\/#(equipo|proceso)$/);
  await expect(page.locator('#origen h2')).toHaveText('From aether to software.');
});

test('documentation search, navigation and safe rendering',async({page})=>{
  const errors:string[]=[]; page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/docs/');
  await page.locator('#docs-search').fill('Graphify');
  await expect(page.locator('[data-document="guides/project-knowledge"]')).toBeVisible();
  await page.locator('#docs-search').fill('zzznomatchzzz');
  await expect(page.locator('#no-results')).toBeVisible();
  await page.locator('#docs-search').fill('');
  await expect(page.locator('.docs-index-list article:visible')).toHaveCount(16);
  await page.locator('.docs-index-list [href="/docs/guides/project-knowledge/"]').click();
  await expect(page.locator('.prose h1')).toContainText('Project knowledge');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
  expect(errors).toEqual([]);
});

test('landing and documentation automated accessibility',async({page})=>{
  for(const route of ['/','/en/','/docs/','/docs/guides/project-knowledge/']){
    await page.goto(route);
    await page.emulateMedia({reducedMotion:'reduce'});
    const results=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']).analyze();
    expect(results.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>n.target)}))).toEqual([]);
  }
});

test('keyboard skip link and all network requests stay local',async({page})=>{
  const requests:string[]=[];
  page.on('request',r=>requests.push(r.url()));
  await page.goto('/');
  await page.keyboard.press('Tab');
  await expect(page.locator('.skip-link')).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/#main$/);
  expect(requests.filter(url=>!url.startsWith('http://127.0.0.1:4321/'))).toEqual([]);
});
