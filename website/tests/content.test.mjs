import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, readdir, rm, stat, writeFile, mkdtemp } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';
import path from 'node:path';
import { parseHTML } from 'linkedom';

const output = path.resolve('dist');
const normalize = s => s.replace(/\s+/g, ' ').trim();
const doc = file => readFile(path.join(output,file),'utf8').then(s => parseHTML(s).document);
const text = node => node.nodeType === 3 ? node.textContent : node.tagName === 'SCRIPT' || node.tagName === 'STYLE' || node.getAttribute?.('aria-hidden') === 'true' ? '' : ` ${[...node.childNodes].map(text).join(' ')} `;
const homepage = await doc('index.html');
const repository = execFileSync('git',['rev-parse','--show-toplevel'],{encoding:'utf8'}).trim();
const trackedDocs = execFileSync('git',['ls-files','--','docs'],{cwd:repository,encoding:'utf8'}).split('\n').filter(file => file.endsWith('.md'));

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

test('landing labels intended scope, current inspection and provider-free limits', () => {
  const development = normalize(text(homepage.querySelector('#desarrollo')));
  for (const phrase of [
    'Este checkout es una build de estabilización',
    'no un lanzamiento público',
    'inspeccionar el código fuente sin hacer llamadas a proveedores',
    'repositorio Git existente',
    'coincidencia exacta de ruta',
  ]) assert.ok(development.includes(phrase), `Missing current boundary copy: ${phrase}`);
  const process = normalize(text(homepage.querySelector('#proceso')));
  assert.match(process, /El flujo descrito para un objetivo sustancial/);
  assert.match(process, /no evidencia de una ejecución respaldada por un proveedor/);
  const foundations = normalize(text(homepage.querySelector('#fundamentos')));
  assert.match(foundations, /no configura proveedores ni prueba una ejecución respaldada/);
});

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

test('documentation manifest, grouped routes and revision-pinned sources cover the tracked corpus', async () => {
  const records=JSON.parse(await readFile(path.join(output,'docs/search.json'),'utf8'));
  const revision=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();
  const expectedGroups=['Start here','Core concepts','Working with Aether','Operations and safety','Reference'];
  assert.equal(records.length,trackedDocs.length);
  assert.deepEqual(new Set(records.map(record=>record.sourcePath)),new Set(trackedDocs));
  assert.equal(new Set(records.map(record=>record.slug)).size,records.length);
  assert.equal(new Set(records.map(record=>record.route)).size,records.length);
  for (const record of records) {
    assert.ok(expectedGroups.includes(record.group),`Unknown group: ${record.group}`);
    assert.equal(typeof record.order,'number');
    assert.ok(record.title && record.description);
    assert.ok(Array.isArray(record.search) && record.search.length > 0);
    assert.equal(record.navigation.position,record.order);
    assert.ok(record.navigation.label);
    assert.equal(record.sourceRevision,revision);
    assert.match(record.source,new RegExp(`/blob/${revision}/${record.sourcePath}$`));
    const generated=path.join(output,record.route.slice(1),'index.html');
    await stat(generated);
  }
  const indexPage=await doc('docs/index.html');
  assert.equal(indexPage.documentElement.getAttribute('lang'),'es-MX');
  assert.equal(indexPage.querySelector('[data-doc-content]').getAttribute('data-source-path'),'docs/index.md');
  assert.equal(indexPage.querySelector('[data-doc-content]').getAttribute('lang'),'en');
  assert.match(normalize(text(indexPage.querySelector('[data-doc-content]'))),/canonical English manual/);
  assert.ok(indexPage.querySelector('[data-doc-content] h1[id][tabindex="-1"]'));
  const groups=[...indexPage.querySelectorAll('.docs-index-group[data-doc-group]')];
  assert.deepEqual(groups.map(group=>group.dataset.docGroup),expectedGroups);
  const cards=[...indexPage.querySelectorAll('.docs-group-pages article[data-document]')];
  assert.equal(cards.length,records.length);
  assert.deepEqual(new Set(cards.map(card=>card.dataset.document)),new Set(records.map(record=>record.slug)));
  assert.equal(cards.filter(card=>card.dataset.docRoute==='/docs/').length,1);
  assert.deepEqual([...indexPage.querySelectorAll('.docs-index-group h2')].map(heading=>heading.getAttribute('lang')),Array(5).fill('en'));
  assert.deepEqual([...indexPage.querySelectorAll('.docs-group-header > p')].map(description=>description.getAttribute('lang')),Array(5).fill('es-MX'));
  assert.equal(indexPage.querySelectorAll('.docs-index-list article[data-document] h3[lang="en"]').length,records.length);
  assert.equal(indexPage.querySelectorAll('.docs-index-list article[data-document] > p[lang="en"]').length,records.length);
  assert.equal(indexPage.querySelectorAll('.docs-navigation').length,2);
  for (const navigation of indexPage.querySelectorAll('.docs-navigation')) {
    assert.equal(navigation.querySelectorAll('[data-document]').length,records.length);
    assert.deepEqual([...navigation.querySelectorAll('.docs-nav-group')].map(group=>group.dataset.docGroup),expectedGroups);
    for (const link of navigation.querySelectorAll('[data-document]')) assert.match(link.dataset.docSourceUrl, new RegExp(`/blob/${revision}/`));
  }
  assert.ok(indexPage.querySelector('#documentation-search'));
  assert.ok(indexPage.querySelector('.docs-status-notice'));
  assert.ok(indexPage.querySelector('.docs-search-status'));
  assert.ok(indexPage.querySelector('noscript .docs-search-unavailable'));
  await assert.rejects(stat(path.join(output,'docs/index/index.html')));

  const graphify=records.find(record=>record.slug==='guides/project-knowledge');
  assert.ok(graphify.text.includes('Graphify'));
  assert.ok(graphify.search.includes('conocimiento'));
  const manual=await doc('docs/guides/execution/index.html');
  assert.ok(manual.querySelector('.prose h1[id]'));
  assert.ok(manual.querySelector('.docs-toc'));
  assert.equal(manual.querySelectorAll('[data-adjacent]').length,2);
  assert.equal(manual.querySelector('[data-doc-group]').getAttribute('data-doc-group'),'Working with Aether');
  assert.ok(manual.querySelector('.docs-article-actions a[href*="#documentation-search"]'));
  assert.ok(manual.querySelector(`a[href*="/blob/${revision}/"]`));
  assert.ok(manual.querySelector('.docs-sidebar'));
});

test('manifest validation fails closed for unknown, duplicate and stale records', async () => {
  const source = (await readFile(path.resolve('src/lib/docs.ts'),'utf8')).replace(
    "import { sitePath } from './site-path';",
    'const sitePath = pathname => pathname;',
  );
  const temp = await mkdtemp(path.resolve('tests/.aether-docs-manifest-'));
  const modulePath = path.join(temp,'docs.ts');
  await writeFile(modulePath,source);
  try {
    const manifest = await import(`${pathToFileURL(modulePath).href}?case=${Date.now()}`);
    assert.doesNotThrow(() => manifest.validateManifest(trackedDocs));
    assert.throws(() => manifest.validateManifest([...trackedDocs,'docs/unclassified.md']),/Unclassified tracked documentation/);
    assert.throws(() => manifest.validateManifest(trackedDocs.filter(file => file !== 'docs/index.md'),manifest.DOC_MANIFEST),/Unclassified tracked documentation|manifest entry has no tracked source/);
    const duplicate = [...manifest.DOC_MANIFEST].map(record => ({...record,navigation:{...record.navigation},search:[...record.search]}));
    duplicate[1] = {...duplicate[1],source:duplicate[0].source};
    assert.throws(() => manifest.validateManifest(trackedDocs,duplicate),/Duplicate documentation manifest source/);
    const duplicateSlug = [...manifest.DOC_MANIFEST].map(record => ({...record,navigation:{...record.navigation},search:[...record.search]}));
    duplicateSlug[1] = {...duplicateSlug[1],slug:duplicateSlug[0].slug,route:duplicateSlug[0].route};
    assert.throws(() => manifest.validateManifest(trackedDocs,duplicateSlug),/Duplicate documentation slug|Duplicate documentation route/);
    const duplicateRoute = [...manifest.DOC_MANIFEST].map(record => ({...record,navigation:{...record.navigation},search:[...record.search]}));
    duplicateRoute[1] = {...duplicateRoute[1],route:duplicateRoute[0].route};
    assert.throws(() => manifest.validateManifest(trackedDocs,duplicateRoute),/Duplicate documentation route/);
    const missingRoute = [...manifest.DOC_MANIFEST].map(record => ({...record,navigation:{...record.navigation},search:[...record.search]}));
    missingRoute[1] = {...missingRoute[1],route:''};
    assert.throws(() => manifest.validateManifest(trackedDocs,missingRoute),/Missing documentation route|Route does not match slug/);
    const wrongNavigationKind = [...manifest.DOC_MANIFEST].map(record => ({...record,navigation:{...record.navigation},search:[...record.search]}));
    wrongNavigationKind[1] = {...wrongNavigationKind[1],navigation:{...wrongNavigationKind[1].navigation,kind:'home'}};
    assert.throws(() => manifest.validateManifest(trackedDocs,wrongNavigationKind),/Incomplete documentation navigation metadata/);
    const invalidSlug = [...manifest.DOC_MANIFEST].map(record => ({...record,navigation:{...record.navigation},search:[...record.search]}));
    invalidSlug[1] = {...invalidSlug[1],slug:'guides/../unsafe',route:'/docs/guides/../unsafe/'};
    assert.throws(() => manifest.validateManifest(trackedDocs,invalidSlug),/Invalid documentation slug/);
    const skippedOrder = [...manifest.DOC_MANIFEST].map(record => ({...record,navigation:{...record.navigation},search:[...record.search]}));
    skippedOrder[2] = {...skippedOrder[2],order:4,navigation:{...skippedOrder[2].navigation,position:4}};
    assert.throws(() => manifest.validateManifest(trackedDocs,skippedOrder),/contiguous|Duplicate order/);
    const stale = [...manifest.DOC_MANIFEST].map(record => ({...record,navigation:{...record.navigation},search:[...record.search]}));
    stale[0] = {...stale[0],source:'docs/not-tracked.md',slug:'not-tracked',route:'/docs/not-tracked/',navigation:{...stale[0].navigation,label:'Not tracked'}};
    assert.throws(() => manifest.validateManifest(trackedDocs,stale),/Unclassified tracked documentation|manifest entry has no tracked source/);
    assert.throws(() => manifest.assertUniqueHeadingIds([{depth:2,id:'same',text:'One'},{depth:2,id:'same',text:'Two'}]),/Duplicate heading id/);
  } finally {
    await rm(temp,{recursive:true,force:true});
  }
});

test('no remote script/font/image dependencies or runtime endpoints in the site', async () => {
  for (const file of await htmlFiles(output)) {
    const d=parseHTML(await readFile(file,'utf8')).document;
    for (const el of d.querySelectorAll('script[src],img[src],link[rel="stylesheet"]')) {
      const src=el.getAttribute('src')||el.getAttribute('href');
      assert.ok(!/^https?:/.test(src),`${file}: unexpected remote asset ${src}`);
    }
    for (const link of d.querySelectorAll('a[href]')) assert.ok(!/^(?:javascript|data|vbscript|file):/i.test(link.getAttribute('href')),`${file}: unsafe link scheme`);
  }
});

test('font licensing accompanies the self-hosted font build', async () => {
  for (const family of ['barlow-condensed','space-grotesk','ibm-plex-mono']) {
    const source = await readFile(`node_modules/@fontsource/${family}/LICENSE`,'utf8');
    assert.equal(await readFile(path.join(output,`font-licenses/${family}.txt`),'utf8'), source);
  }
});
