import { readFile, readdir } from 'node:fs/promises';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { Marked } from 'marked';
import GithubSlugger from 'github-slugger';
import sanitizeHtml from 'sanitize-html';
import { sitePath } from './site-path';

// Build modules are relocated by Astro; resolve this checkout through Git, not
// import.meta.url (which points into dist during prerendering).
const repository = execFileSync('git', ['rev-parse', '--show-toplevel'], { encoding:'utf8' }).trim();
const docsRoot = path.join(repository, 'docs');
export const sourceRevision = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: repository, encoding: 'utf8' }).trim();
const publicSource = `https://github.com/DarkArty07/Aether-Agents/blob/${sourceRevision}/`;

const descriptions: Record<string, string> = {
  'index': 'Índice de la documentación canónica del proyecto.',
  'getting-started': 'Primeros pasos, requisitos y límites de la versión documentada.',
  'product-boundary': 'Qué aporta Aether y qué reutiliza de Hermes.',
  'roles-and-authority': 'Morfeo, Supervisor e Implementers: responsabilidades y autoridad.',
  'authority': 'Qué documento es responsable de cada decisión.',
  'guides/project-initialization': 'Identidad de proyecto y asociación con repositorios Git.',
  'guides/objective-contracts': 'Alcance, aceptación, contratos y entrega de objetivos.',
  'guides/execution': 'Unidades de trabajo, revisión e integración.',
  'guides/lifecycle': 'Recorrido completo del trabajo y su cierre.',
  'guides/project-knowledge': 'Graphify, mapa técnico compartido y experiencias por rol.',
  'guides/observation': 'Evidencia y lectura de la actividad del sistema.',
  'guides/policy-and-recovery': 'Política, límites y recuperación reversible.',
  'reference/cli': 'Comandos, opciones y salidas de la interfaz de terminal.',
  'reference/plugins-and-tools': 'Plugins y herramientas registradas por el producto.',
  'reference/capabilities': 'Estado de implementación y trazabilidad de las capacidades.',
  'reference/limitations-and-troubleshooting': 'Limitaciones documentadas y diagnóstico.',
};
const order = Object.keys(descriptions);
export interface Doc { slug: string; title: string; description: string; source: string; html: string; text: string; headings: {depth: number; id: string; text: string}[]; }

async function markdownPaths(dir: string): Promise<string[]> {
  const entries = await readdir(dir, { withFileTypes:true });
  const groups = await Promise.all(entries.map(e => e.isDirectory() ? markdownPaths(path.join(dir,e.name)) : e.isFile() && e.name.endsWith('.md') ? [path.join(dir,e.name)] : []));
  return groups.flat();
}

let cached: Promise<Doc[]> | undefined;
export function loadDocs(): Promise<Doc[]> {
  return cached ||= buildDocs();
}
async function buildDocs(): Promise<Doc[]> {
  // The tracked public corpus only; runtime directories never enter this build.
  const tracked = new Set(execFileSync('git',['ls-files','--','docs'],{cwd:repository,encoding:'utf8'}).trim().split('\n'));
  const files = (await markdownPaths(docsRoot)).filter(f => tracked.has(path.relative(repository,f).split(path.sep).join('/')));
  const localPages = new Set(files.map(f => path.resolve(f)));
  const results: Doc[] = [];
  for (const file of files) {
    const markdown = await readFile(file,'utf8');
    const slug = path.relative(docsRoot,file).replace(/\.md$/, '').split(path.sep).join('/');
    const title = markdown.match(/^#\s+(.+)$/m)?.[1] || slug;
    const headings: Doc['headings'] = [];
    const slugger = new GithubSlugger();
    const parser = new Marked({
      gfm:true,
      walkTokens(token) {
        if (token.type === 'link' || token.type === 'image') {
          if (/^(https?:|mailto:|#)/i.test(token.href)) return;
          const [rel, fragment] = token.href.split('#');
          const target = path.resolve(path.dirname(file), decodeURIComponent(rel));
          const suffix = fragment ? `#${fragment}` : '';
          if (localPages.has(target)) {
            token.href = `${sitePath(`/docs/${path.relative(docsRoot,target).replace(/\.md$/, '').split(path.sep).join('/')}/`)}${suffix}`;
          } else {
            const relative = path.relative(repository,target).split(path.sep).join('/');
            if (!relative.startsWith('../')) token.href = publicSource + relative + suffix;
          }
        }
      },
    });
    let html = await parser.parse(markdown);
    html = html.replace(/<h([1-6])>([\s\S]*?)<\/h\1>/g, (_, depth, body) => {
      const plain = sanitizeHtml(body,{allowedTags:[],allowedAttributes:{}});
      const id = slugger.slug(plain);
      headings.push({depth:Number(depth),id,text:plain});
      return `<h${depth} id="${id}">${body}</h${depth}>`;
    });
    html = sanitizeHtml(html, {
      allowedTags:[...sanitizeHtml.defaults.allowedTags,'details','summary','img'],
      allowedAttributes:{...sanitizeHtml.defaults.allowedAttributes, '*':['id'], 'code':['class'], 'img':['src','alt','width','height'], 'a':['href','title','id']},
      allowedSchemes:['http','https','mailto'],
    }).replace(/<pre>/g,'<pre tabindex="0">')
      .replace(/<table>/g,'<div class="table-wrap" tabindex="0" role="region" aria-label="Scrollable table"><table>')
      .replace(/<\/table>/g,'</table></div>');
    const text = sanitizeHtml(html,{allowedTags:[],allowedAttributes:{}}).replace(/\s+/g,' ').trim();
    results.push({slug,title,description:descriptions[slug] || title,source:publicSource+path.relative(repository,file).split(path.sep).join('/'),html,text,headings});
  }
  return results.sort((a,b) => order.indexOf(a.slug)-order.indexOf(b.slug));
}
