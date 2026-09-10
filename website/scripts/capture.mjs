import { chromium } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';

await mkdir('test-results/visual',{recursive:true});
const browser = await chromium.launch({headless:true});
const findings=[];
try {
  for (const width of [360,390,768,1024,1440,1920]) {
    const page=await browser.newPage({viewport:{width,height:1000},deviceScaleFactor:1,reducedMotion:'reduce'});
    await page.goto('http://127.0.0.1:4321/',{waitUntil:'networkidle'});
    await page.evaluate(()=>document.fonts.ready);
    const overflow=await page.evaluate(()=>[...document.querySelectorAll('main *')].filter(el=>{
      const r=el.getBoundingClientRect();
      let left=r.left, right=r.right;
      // A graph can intentionally crop its SVG drawing without overflowing the page.
      // Measure the painted region through ancestor clipping, not off-canvas geometry.
      for (let parent=el.parentElement; parent; parent=parent.parentElement) {
        if (['hidden','clip','auto','scroll'].includes(getComputedStyle(parent).overflowX)) {
          const clip=parent.getBoundingClientRect(); left=Math.max(left,clip.left); right=Math.min(right,clip.right);
        }
      }
      return r.width>0 && right>left && (right>innerWidth+2 || left < -2) && getComputedStyle(el).position !== 'absolute';
    }).map(el=>({tag:el.tagName,cls:el.getAttribute('class')})));
    findings.push({width,documentWidth:await page.evaluate(()=>document.documentElement.scrollWidth),overflow});
    await page.screenshot({path:`test-results/visual/${width}-hero.png`});
    if(width===390 || width===1440) {
      for(const id of ['desarrollo','equipo','proceso','conocimiento','control','fundamentos','autoria']) {
        // Tall element captures resize the viewport. Hide fixed/sticky chrome only
        // in these evidence images to avoid duplicated overlays, not in the site.
        await page.locator(`#${id}`).screenshot({
          path:`test-results/visual/${width}-${id}.png`,
          style:'.site-header, .motion-toggle, .skip-link { visibility: hidden !important; }',
        });
      }
      for(const [slug, route] of [
        ['docs-index','/docs/'],
        ['docs-start','/docs/start-here/'],
        ['docs-walkthrough','/docs/guides/first-objective/'],
        ['docs-reference','/docs/reference/capabilities/'],
      ]) {
        await page.goto(`http://127.0.0.1:4321${route}`,{waitUntil:'networkidle'});
        await page.evaluate(()=>document.fonts.ready);
        const docsOverflow=await page.evaluate(()=>[...document.querySelectorAll('main *')].filter(el=>{
          const r=el.getBoundingClientRect();
          return r.width>0 && (r.right>innerWidth+2 || r.left < -2) && getComputedStyle(el).position !== 'absolute';
        }).map(el=>({tag:el.tagName,cls:el.getAttribute('class')})));
        findings.push({width,surface:slug,route,documentWidth:await page.evaluate(()=>document.documentElement.scrollWidth),overflow:docsOverflow});
        await page.screenshot({path:`test-results/visual/${width}-${slug}.png`,fullPage:true});
      }
    }
    await page.close();
  }
  await writeFile('test-results/visual/layout.json',JSON.stringify(findings,null,2)+'\n');
  console.log(JSON.stringify(findings,null,2));
  if(findings.some(item=>item.documentWidth>item.width+1 || item.overflow.length)) throw new Error('Responsive overflow detected');
} finally { await browser.close(); }
