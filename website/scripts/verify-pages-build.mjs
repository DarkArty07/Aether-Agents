import assert from 'node:assert/strict';
import { readFile, readdir, stat } from 'node:fs/promises';
import path from 'node:path';
import { parseHTML } from 'linkedom';

const output = path.resolve('dist');
const base = '/Aether-Agents/';

async function htmlFiles(dir) {
  const entries = await readdir(dir, { withFileTypes: true });
  return (await Promise.all(entries.map(entry => {
    const target = path.join(dir, entry.name);
    if (entry.isDirectory()) return htmlFiles(target);
    return entry.name.endsWith('.html') ? [target] : [];
  }))).flat();
}

async function assertTarget(url, from) {
  if (!url || /^(https?:|mailto:|data:|#)/.test(url)) return;
  assert.ok(url.startsWith(base), `${from}: root URL is missing GitHub Pages base: ${url}`);
  const parsed = new URL(url, 'https://darkarty07.github.io');
  const relative = decodeURIComponent(parsed.pathname.slice(base.length));
  let target = path.join(output, relative);
  const info = await stat(target).catch(() => undefined);
  if (info?.isDirectory()) target = path.join(target, 'index.html');
  await stat(target).catch(() => assert.fail(`${from}: unresolved Pages target ${url}`));
}

const pages = await htmlFiles(output);
assert.ok(pages.length >= 20, `Expected the full static site, found ${pages.length} HTML pages`);

for (const file of pages) {
  const relativeFile = path.relative(output, file);
  const document = parseHTML(await readFile(file, 'utf8')).document;
  for (const element of document.querySelectorAll('a[href],img[src],script[src],link[href]')) {
    await assertTarget(element.getAttribute('href') || element.getAttribute('src'), relativeFile);
  }
  for (const source of document.querySelectorAll('source[srcset]')) {
    for (const candidate of source.getAttribute('srcset').split(',')) {
      await assertTarget(candidate.trim().split(/\s+/)[0], relativeFile);
    }
  }
}

const landing = await readFile(path.join(output, 'index.html'), 'utf8');
assert.match(landing, /\/Aether-Agents\/images\/aether-morfeo-hero-1672\.webp/);
assert.match(landing, /href="\/Aether-Agents\/docs\/"/);

const docsIndex = await readFile(path.join(output, 'docs', 'index.html'), 'utf8');
assert.ok(docsIndex.includes('/Aether-Agents/docs/search.json'), 'Documentation search must use the Pages base path');

console.log(`GitHub Pages base-path verification passed for ${pages.length} HTML pages.`);
