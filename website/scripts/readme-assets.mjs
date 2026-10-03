// Render the README banner and the GitHub social-preview image from the approved
// website artwork, fonts and palette. Run from website/: `npm run readme-assets`.
// Everything is local (no network); outputs go to ../.github/assets/.
import { chromium } from '@playwright/test';
import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import sharp from 'sharp';

const website = path.resolve('.');
const out = path.resolve(website, '..', '.github', 'assets');
const fileUrl = p => pathToFileURL(path.resolve(website, p)).href;
const font = (family, weight) =>
  fileUrl(`node_modules/@fontsource/${family}/files/${family}-latin-${weight}-normal.woff2`);

const fontFaces = `
@font-face{font-family:'Barlow Condensed';font-weight:600;src:url(${font('barlow-condensed', 600)}) format('woff2')}
@font-face{font-family:'Barlow Condensed';font-weight:700;src:url(${font('barlow-condensed', 700)}) format('woff2')}
@font-face{font-family:'Space Grotesk';font-weight:400;src:url(${font('space-grotesk', 400)}) format('woff2')}
@font-face{font-family:'Space Grotesk';font-weight:500;src:url(${font('space-grotesk', 500)}) format('woff2')}
@font-face{font-family:'IBM Plex Mono';font-weight:400;src:url(${font('ibm-plex-mono', 400)}) format('woff2')}`;

// Catppuccin Mocha tokens shared with src/styles/global.css.
const page = ({ width, height, scale, footer }) => `<!doctype html><html><head><meta charset="utf-8"><style>
${fontFaces}
:root{--crust:#11111b;--surface:#313244;--subtext:#a6adc8;--text:#cdd6f4;--mauve:#cba6f7}
*{box-sizing:border-box;margin:0}
body{width:${width}px;height:${height}px;overflow:hidden;background:var(--crust);color:var(--text);font-family:'Space Grotesk',sans-serif;-webkit-font-smoothing:antialiased}
.art{position:absolute;top:0;right:0;height:100%;width:auto}
.shade{position:absolute;inset:0;background:
  linear-gradient(90deg,var(--crust) 0%,var(--crust) ${scale.solid}%,rgba(17,17,27,.78) ${scale.solid + 14}%,rgba(17,17,27,.2) ${scale.solid + 34}%,transparent ${scale.solid + 46}%),
  linear-gradient(0deg,rgba(17,17,27,.85),transparent 26%)}
.frame{position:absolute;inset:${scale.inset}px;border:1px solid var(--surface)}
.copy{position:absolute;left:${scale.left}px;top:${scale.top}px;max-width:${scale.copy}px}
.eyebrow{font-family:'IBM Plex Mono',monospace;font-size:${scale.eyebrow}px;letter-spacing:.22em;color:var(--mauve)}
.wordmark{font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:${scale.word}px;line-height:.8;letter-spacing:-.03em;margin-top:${scale.gap}px}
.agents{display:block;font-weight:600;font-size:.26em;letter-spacing:.62em;margin:${scale.gap * 0.7}px 0 0 4px}
.headline{font-size:${scale.headline}px;font-weight:500;margin-top:${scale.gap * 1.25}px;color:var(--text)}
.tagline{font-size:${scale.tagline}px;line-height:1.5;margin-top:${scale.gap * 0.5}px;color:var(--subtext)}
.footer{position:absolute;left:${scale.left}px;bottom:${scale.bottom}px;font-family:'IBM Plex Mono',monospace;font-size:${scale.eyebrow}px;letter-spacing:.16em;color:var(--subtext)}
.footer b{color:var(--mauve);font-weight:400}
</style></head><body>
<img class="art" src="${fileUrl('assets/images/aether-morfeo-hero.png')}" alt="">
<div class="shade"></div><div class="frame"></div>
<div class="copy">
  <p class="eyebrow">◇ STABLE RELEASE · v1.0.0</p>
  <h1 class="wordmark">AETHER<span class="agents">AGENTS</span></h1>
  <p class="headline">From aether to software.</p>
  <p class="tagline">A spec-driven software-engineering team of three AI roles, built on Hermes Agent.</p>
</div>
<p class="footer">${footer}</p>
</body></html>`;

const targets = [
  {
    name: 'banner.png',
    width: 1600,
    height: 560,
    footer: 'OPEN SOURCE <b>·</b> SPEC-DRIVEN <b>·</b> MIT',
    scale: { solid: 16, inset: 18, left: 88, top: 78, copy: 640, eyebrow: 15, word: 132, gap: 22, headline: 30, tagline: 19, bottom: 52 },
  },
  {
    name: 'social-preview.png',
    width: 1280,
    height: 640,
    footer: 'github.com/<b>DarkArty07</b>/Aether-Agents',
    scale: { solid: 8, inset: 16, left: 72, top: 92, copy: 560, eyebrow: 15, word: 138, gap: 24, headline: 32, tagline: 20, bottom: 56 },
  },
];

await mkdir(out, { recursive: true });
const work = await mkdtemp(path.join(tmpdir(), 'aether-readme-assets-'));
const browser = await chromium.launch({ headless: true });
try {
  for (const target of targets) {
    const html = path.join(work, `${target.name}.html`);
    await writeFile(html, page(target));
    const tab = await browser.newPage({ viewport: { width: target.width, height: target.height }, deviceScaleFactor: 1 });
    await tab.goto(pathToFileURL(html).href, { waitUntil: 'load' });
    await tab.evaluate(() => document.fonts.ready);
    const missing = await tab.evaluate(() => [...document.fonts].filter(f => f.status !== 'loaded').map(f => f.family));
    if (missing.length) throw new Error(`fonts not loaded: ${missing.join(', ')}`);
    // Lossless recompression keeps the social preview under GitHub's 1 MB limit.
    const shot = await tab.screenshot();
    await sharp(shot).png({ compressionLevel: 9, adaptiveFiltering: true, effort: 10 }).toFile(path.join(out, target.name));
    await tab.close();
    console.log(`wrote .github/assets/${target.name} (${target.width}x${target.height})`);
  }
} finally {
  await browser.close();
  await rm(work, { recursive: true, force: true });
}
