import { test, expect } from '@playwright/test';

test('finished labels and linked authorship', async ({page}) => {
  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('lang','es-MX');
  for (const label of await page.locator('.section-label').allTextContents()) {
    expect(label).not.toMatch(/\b0[0-7]\s*\//);
  }
  await expect(page.locator('#origen h2')).toHaveText('Del éter al software.');
  await expect(page.locator('.author-handle')).toHaveAttribute('href','https://github.com/DarkArty07');
  await expect(page.locator('.author-handle')).toContainText('@DarkArty07');
  await expect(page.locator('#desarrollo')).toContainText('Tú defines qué quieres crear');
  const teamCaption=page.locator('#equipo .instrument-caption');
  await expect(teamCaption).toContainText('El trabajo pasa entre etapas y agentes');
  await expect(teamCaption).not.toContainText('Trabajo que avanza y regresa');
});

test('autonomy instrument is legible as a 24-hour clock', async ({page}) => {
  await page.emulateMedia({reducedMotion:'no-preference'});
  await page.goto('/#desarrollo');
  const clock=page.locator('.astrolabe');
  await clock.scrollIntoViewIfNeeded();
  await expect(clock.locator('.clock-hour-label')).toHaveCount(24);
  await expect(clock.locator('.clock-hand')).toHaveCount(2);
  await expect(clock).toContainText('TRABAJO AUTÓNOMO');
  await expect(clock).toContainText('24 H');
  await expect(clock).not.toContainText('RELOJ CONCEPTUAL');
  await expect(clock).not.toContainText('No mide duración real');
  const labels=await clock.locator('.clock-hour-label').evaluateAll(nodes=>nodes.map(node=>{
    const r=node.getBoundingClientRect();
    return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height};
  }));
  for(let i=0;i<labels.length;i++) for(let j=i+1;j<labels.length;j++) {
    const a=labels[i], b=labels[j];
    const overlap=Math.min(a.right,b.right)-Math.max(a.left,b.left)>1 && Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>1;
    expect(overlap,`hour labels ${i} and ${j} overlap`).toBeFalsy();
  }
  const pivot=async(selector:string)=>clock.locator(selector).evaluate(el=>{
    const svg=(el as SVGGraphicsElement).ownerSVGElement!;
    const p=svg.createSVGPoint(); p.x=280; p.y=280;
    const out=p.matrixTransform((el as SVGGraphicsElement).getCTM()!);
    return {x:out.x,y:out.y};
  });
  const hourStart=await pivot('.clock-hand-hour');
  const minuteStart=await pivot('.clock-hand-minute');
  const orbitStart=await clock.locator('.orbit-one').getAttribute('transform');
  await page.waitForTimeout(650);
  const hourEnd=await pivot('.clock-hand-hour');
  const minuteEnd=await pivot('.clock-hand-minute');
  const orbitEnd=await clock.locator('.orbit-one').getAttribute('transform');
  expect(Math.hypot(hourEnd.x-hourStart.x,hourEnd.y-hourStart.y)).toBeLessThan(.25);
  expect(Math.hypot(minuteEnd.x-minuteStart.x,minuteEnd.y-minuteStart.y)).toBeLessThan(.25);
  expect(orbitEnd).not.toBe(orbitStart);
  const angle=(value:string|null)=>Number(value?.match(/rotate\(([-\d.]+)/)?.[1] || 0);
  expect(Math.abs(angle(orbitEnd)-angle(orbitStart))).toBeGreaterThan(4);
});

test('editorial metadata remains readable on desktop and mobile', async ({page}) => {
  await page.goto('/');
  const checks = [
    ['.foundations-strip',14],
    ['#desarrollo .section-label',14],
    ['#desarrollo .metadata',14],
    ['#equipo .figure-top',14],
    ['#equipo .diagram-side-labels',14],
    ['#proceso .process-top',14],
    ['.author-handle',14],
    ['.footer-meta',14],
  ] as const;
  for (const [selector,minimum] of checks) {
    const size=await page.locator(selector).first().evaluate(el=>parseFloat(getComputedStyle(el).fontSize));
    expect(size,`${selector} is too small`).toBeGreaterThanOrEqual(minimum);
  }
});

test('static and animated knowledge drawing remains clipped at narrow viewports', async ({page}) => {
  for (const width of [360,390,768,1024,1920]) {
    await page.setViewportSize({width,height:1000});
    await page.emulateMedia({reducedMotion:'reduce'});
    await page.goto('/#conocimiento');
    expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(width+1);
    await page.emulateMedia({reducedMotion:'no-preference'});
    await page.locator('.knowledge-stage').scrollIntoViewIfNeeded();
    await page.waitForTimeout(100);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(width+1);
  }
});

test('knowledge paths animate and return; pause, visibility and reduced motion stop them', async ({page}) => {
  const errors:string[]=[];
  page.on('pageerror', e=>errors.push(e.message));
  await page.goto('/');
  const graph=page.locator('[data-knowledge-graph]');
  await page.locator('.knowledge-stage').scrollIntoViewIfNeeded();
  await expect(graph).toHaveAttribute('data-ready','true');
  await expect(graph).toHaveAttribute('data-animating','true');
  const positions=()=>page.locator('[data-knowledge-packet]').evaluateAll(ps=>ps.map(p=>p.getAttribute('transform')).join('|'));
  const first=await positions();
  await expect.poll(positions).not.toBe(first);
  await expect(graph).toHaveAttribute('data-traversal',/:out$/,{timeout:7000});
  await page.locator('[data-motion-toggle]').click();
  await expect(graph).toHaveAttribute('data-animating','false');
  const paused=await positions(); await page.waitForTimeout(350);
  expect(await positions()).toBe(paused);
  await page.locator('[data-motion-toggle]').click();
  await expect(graph).toHaveAttribute('data-animating','true');
  await expect.poll(positions).not.toBe(paused);
  await page.locator('#autoria').scrollIntoViewIfNeeded();
  await expect(graph).toHaveAttribute('data-animating','false');
  const offscreen=await positions(); await page.waitForTimeout(350);
  expect(await positions()).toBe(offscreen);
  await page.locator('.knowledge-stage').scrollIntoViewIfNeeded();
  await page.emulateMedia({reducedMotion:'reduce'});
  await expect(graph).toHaveAttribute('data-animating','false');
  const reduced=await positions(); await page.waitForTimeout(350);
  expect(await positions()).toBe(reduced);
  expect(errors).toEqual([]);
});

test('knowledge exploration works by pointer or touch and keyboard', async ({page}, info) => {
  await page.goto('/#conocimiento');
  const graph=page.locator('[data-knowledge-graph]');
  const node=page.locator('[data-knowledge-node="tests"]');
  await expect(node).toBeEnabled();
  await node.scrollIntoViewIfNeeded();
  if (info.project.name==='mobile') await node.tap(); else await node.click();
  await expect(node).toHaveAttribute('aria-pressed','true');
  await expect(graph).toHaveAttribute('data-selected','tests');
  await expect(page.locator('[data-knowledge-title]')).toHaveText('Pruebas');
  await expect(page.locator('[data-knowledge-description]')).toContainText('no significa por sí sola');
  await expect(graph).toHaveAttribute('data-animating','false');
  await page.locator('[data-knowledge-reset]').click();
  await expect(node).toHaveAttribute('aria-pressed','false');
  await expect(graph).toHaveAttribute('data-selected','');
  await expect(node).toBeFocused();
  const code=page.locator('[data-knowledge-node="code"]');
  await code.focus(); await page.keyboard.press('Enter');
  await expect(page.locator('[data-knowledge-title]')).toHaveText('Código');
  await page.keyboard.press('Escape');
  await expect(page.locator('[data-knowledge-title]')).toHaveText('Explora cómo se conecta el proyecto.');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
});
