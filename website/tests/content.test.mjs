import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, readdir, stat } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { parseHTML } from 'linkedom';

const output = path.resolve('dist');
const normalize = s => s.replace(/\s+/g, ' ').trim();
const doc = file => readFile(path.join(output,file),'utf8').then(s => parseHTML(s).document);
const text = node => node.nodeType === 3 ? node.textContent : node.tagName === 'SCRIPT' || node.tagName === 'STYLE' || node.getAttribute?.('aria-hidden') === 'true' ? '' : ` ${[...node.childNodes].map(text).join(' ')} `;
const homepage = await doc('index.html');
const proposal = await readFile('COPY_REFINEMENT_MX.md','utf8');

test('eight ordered sections and only the owner-selected opening, graph decoration and finale images', () => {
  const sections = [...homepage.querySelectorAll('main section[data-section]')];
  assert.deepEqual(sections.map(s=>s.dataset.section),['00','01','02','03','04','05','06','07']);
  assert.equal(homepage.querySelectorAll('main img').length,3);
  assert.equal(homepage.querySelectorAll('#origen img').length,1);
  assert.equal(homepage.querySelectorAll('#conocimiento img').length,1);
  assert.equal(homepage.querySelectorAll('#autoria img').length,1);
  assert.equal(homepage.querySelector('#autoria img').getAttribute('src'),'/images/aether-ether-finale-1672.webp');
  assert.match(normalize(text(sections[7])),/Christopher Hernández Jiménez/);
  assert.doesNotMatch(normalize(text(sections[7])),/Aether 1\.0|EN CALIFICACIÓN|ESTADO/);
});

for (const section of ['00','01','02','03','04','05','06','07']) {
  test(`section ${section}: literal current Spanish review candidate`, () => {
    const sectionText = proposal.split(new RegExp(`### ${section}\\.`))[1]?.split(/\n### \d\d\./)[0];
    assert.ok(sectionText,`Missing approved section ${section}`);
    let blocks = [...sectionText.matchAll(/```text\n([\s\S]*?)\n```/g)].map(m=>m[1]);
    if (section === '01') blocks=blocks.slice(0,2); // The third block was optional metadata.
    const scope = section === '00' ? homepage.querySelector('main') : homepage.querySelector(`[data-section='${section}']`);
    const actual = normalize(text(scope));
    for (const block of blocks) {
      for (const paragraph of block.split(/\n\s*\n|\]\s*\[/)) {
        const expected = normalize(paragraph.replace(/^\[\s*|\s*\]$/g,''));
        assert.ok(actual.includes(expected),`Missing or changed copy: ${expected}`);
      }
    }
  });
}

test('knowledge distinguishes optional graph, role experience and owner preferences', () => {
  const actual = normalize(text(homepage.querySelector('#conocimiento')));
  for (const value of ['Contexto compartido.','Experiencia por rol.','MEMORIA DE MORFEO','Graphify es una integración opcional.','La fuente de verdad sigue siendo el código']) assert.ok(actual.includes(value));
  assert.ok(actual.includes('MAPA TÉCNICO COMPARTIDO · GRAPHIFY OPCIONAL'));
  assert.doesNotMatch(actual,/no muestra datos reales ni en vivo|ejemplo interactivo/i);
});

test('autonomy instrument reads as a finished 24-hour clock', () => {
  const clock = homepage.querySelector('.astrolabe');
  assert.ok(clock);
  const title = normalize(clock.querySelector('title').textContent);
  assert.match(title,/Reloj de 24 horas/);
  assert.doesNotMatch(title,/conceptual|duración real/i);
  const labels = [...clock.querySelectorAll('.clock-hour-label')].map(label => normalize(label.textContent));
  assert.deepEqual(labels,Array.from({length:24},(_,hour)=>String(hour).padStart(2,'0')));
  assert.equal(clock.querySelectorAll('.clock-hand').length,2);
  assert.match(normalize(text(clock)),/TRABAJO AUTÓNOMO/);
  assert.match(normalize(text(clock)),/24 H/);
  assert.equal(clock.querySelectorAll('figcaption').length,0);
  assert.doesNotMatch(normalize(text(clock)),/reloj conceptual|no mide duración real/i);
});

test('prototype-style explanatory labels are absent from the finished landing', () => {
  const actual = normalize(text(homepage.querySelector('main')));
  assert.doesNotMatch(actual,/recorrido ilustrativo|representación conceptual|no muestra datos reales ni en vivo|reloj conceptual|no mide duración real/i);
  assert.match(actual,/Flujo de trabajo/);
});

test('arrow and plus symbols follow interaction semantics', () => {
  assert.equal(homepage.querySelectorAll('.development-modes .mode-arrow').length,0);
  assert.equal(homepage.querySelectorAll('.control-items .control-symbol').length,0);
  assert.equal(homepage.querySelectorAll('.control-items button,.development-modes button').length,0);
  assert.doesNotMatch(normalize(text(homepage.querySelector('.development-modes'))),/↗/);
  assert.doesNotMatch(normalize(text(homepage.querySelector('.control-items'))),/\+/);
  const docsLink = homepage.querySelector('.desktop-nav a[href="/docs/"]');
  assert.ok(docsLink);
  assert.doesNotMatch(normalize(docsLink.textContent),/↗/);
  const internalFoundation = homepage.querySelector('.foundation-list a[href="/docs/roles-and-authority/"]');
  assert.equal(normalize(internalFoundation.querySelector('.foundation-arrow').textContent),'→');
  for (const link of homepage.querySelectorAll('.foundation-list a[href^="https://"]')) {
    assert.equal(normalize(link.querySelector('.foundation-arrow').textContent),'↗');
  }
});

test('sketch numbering is removed while stable anchors and headlines remain', async () => {
  for (const file of ['index.html','en/index.html']) {
    const d = await doc(file);
    const visible = normalize(text(d.querySelector('main')));
    assert.doesNotMatch(visible,/\b0[0-7]\s*\/|FIG\.\s*0[0-7]|01\s*\+\s*01/);
    assert.equal(d.querySelectorAll('.mode-number,.control-index,.foundation-number,.section-note').length,0);
    assert.equal(d.querySelector('.author-handle').getAttribute('href'),'https://github.com/DarkArty07');
    assert.match(d.querySelector('.author-handle').textContent,/@DarkArty07/);
    assert.equal(d.querySelectorAll('[data-knowledge-node]').length,6);
    assert.equal(d.querySelectorAll('[data-illuminate]').length,6);
    assert.ok(d.querySelector('.knowledge-svg'));
  }
});

test('full resolution hero has lossless encoding and original artwork is preserved', async () => {
  const sharp = (await import('sharp')).default;
  const manifest = JSON.parse(await readFile('public/images/manifest.json','utf8'));
  assert.equal(manifest.find(a=>a.name==='aether-morfeo-hero' && a.width===1672).lossless,true);
  const original = await sharp('assets/images/aether-morfeo-refined.png').ensureAlpha().raw().toBuffer();
  const encoded = await sharp('public/images/aether-morfeo-hero-1672.webp').ensureAlpha().raw().toBuffer();
  assert.ok(original.equals(encoded),'Full-size encoding must preserve every source pixel');
  const { createHash } = await import('node:crypto');
  const prior = await readFile('assets/images/aether-morfeo-hero.png');
  assert.equal(createHash('sha256').update(prior).digest('hex'),'260b2ec658b9feb8a0b53717fba610d0d08d8ae79f2971577858557b2117a682');
  const finale = await sharp('assets/images/aether-ether-finale.png').ensureAlpha().raw().toBuffer();
  assert.ok(finale.equals(await sharp('public/images/aether-ether-finale-1672.webp').ensureAlpha().raw().toBuffer()));
});

test('English landing has all sections and no empty translation links', async () => {
  const english = await doc('en/index.html');
  assert.equal(english.documentElement.lang,'en');
  assert.equal(english.querySelectorAll('[data-section]').length,8);
  assert.match(normalize(text(english.querySelector('#origen'))),/From aether to software\./);
  assert.match(normalize(text(english.querySelector('#autoria'))),/Christopher Hernández Jiménez/);
});

async function htmlFiles(dir) {
  const entries = await readdir(dir,{withFileTypes:true});
  return (await Promise.all(entries.map(e=>e.isDirectory()?htmlFiles(path.join(dir,e.name)):e.name.endsWith('.html')?[path.join(dir,e.name)]:[]))).flat();
}
test('all generated local links, resources and anchors resolve', async () => {
  const pages = await htmlFiles(output);
  const doms = new Map(await Promise.all(pages.map(async p=>[p,parseHTML(await readFile(p,'utf8')).document])));
  const failures=[];
  for (const [file,d] of doms) {
    const ids=[...d.querySelectorAll('[id]')].map(e=>e.id);
    assert.equal(ids.length,new Set(ids).size,`Duplicate ids in ${file}`);
    for (const el of d.querySelectorAll('a[href],img[src],script[src],link[href]')) {
      const href=el.getAttribute('href') || el.getAttribute('src');
      if (!href || /^(https?:|mailto:|data:)/.test(href)) continue;
      const base='http://local/'+path.relative(output,file).replace(/index\.html$/,'');
      const url=new URL(href,base);
      let target=path.join(output,decodeURIComponent(url.pathname));
      try {
        if ((await stat(target)).isDirectory()) target=path.join(target,'index.html');
        await stat(target);
        if (url.hash && doms.has(target)) {
          const id=decodeURIComponent(url.hash.slice(1));
          if (!doms.get(target).getElementById(id)) failures.push(`${path.relative(output,file)} -> ${href} (anchor)`);
        }
      } catch { failures.push(`${path.relative(output,file)} -> ${href} (file)`); }
    }
  }
  assert.deepEqual(failures,[]);
});

test('documentation is rendered, linked to revision and searchable', async () => {
  const index=JSON.parse(await readFile(path.join(output,'docs/search.json'),'utf8'));
  assert.equal(index.length,16);
  assert.ok(index.find(d=>d.slug==='guides/project-knowledge').text.includes('Graphify'));
  const manual=await doc('docs/guides/execution/index.html');
  assert.ok(manual.querySelector('.prose h1'));
  const revision=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();
  assert.ok(manual.querySelector(`a[href*="/blob/${revision}/"]`));
  assert.ok(manual.querySelector('.docs-sidebar'));
});

test('no remote script/font/image dependencies or runtime endpoints in the site', async () => {
  for (const file of await htmlFiles(output)) {
    const d=parseHTML(await readFile(file,'utf8')).document;
    for (const el of d.querySelectorAll('script[src],img[src],link[rel="stylesheet"]')) {
      const src=el.getAttribute('src')||el.getAttribute('href');
      assert.ok(!/^https?:/.test(src),`${file}: unexpected remote asset ${src}`);
    }
  }
});

test('font licensing accompanies the self-hosted font build', async () => {
  for (const family of ['barlow-condensed','space-grotesk','ibm-plex-mono']) {
    const source = await readFile(`node_modules/@fontsource/${family}/LICENSE`,'utf8');
    assert.equal(await readFile(path.join(output,`font-licenses/${family}.txt`),'utf8'), source);
  }
});
