import { existsSync } from 'node:fs';
import { readFile, readdir } from 'node:fs/promises';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { Marked } from 'marked';
import GithubSlugger from 'github-slugger';
import sanitizeHtml from 'sanitize-html';
import { sitePath } from './site-path';

// Build modules are relocated by Astro; resolve this checkout through Git, not
// import.meta.url (which points into dist during prerendering).
const repository = execFileSync('git', ['rev-parse', '--show-toplevel'], { encoding: 'utf8' }).trim();
const docsRoot = path.join(repository, 'docs');
export const sourceRevision = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: repository, encoding: 'utf8' }).trim();
const publicSource = `https://github.com/DarkArty07/Aether-Agents/blob/${sourceRevision}/`;

export const DOC_GROUPS = [
  { label: 'Start here', description: 'Orientación inicial y el ejercicio seguro de este build.' },
  { label: 'Core concepts', description: 'Modelo de producto, roles y vocabulario.' },
  { label: 'Working with Aether', description: 'Guías para preparar y ejecutar objetivos.' },
  { label: 'Operations and safety', description: 'Observación, límites, política y recuperación.' },
  { label: 'Reference', description: 'Interfaces exactas, herramientas y trazabilidad.' },
] as const;

export type DocGroup = (typeof DOC_GROUPS)[number]['label'];
export type NavigationKind = 'home' | 'article';

export interface DocManifestEntry {
  source: string;
  slug: string;
  route: string;
  group: DocGroup;
  order: number;
  title: string;
  description: string;
  search: string[];
  navigation: {
    kind: NavigationKind;
    label: string;
    position: number;
  };
}

const routeForSlug = (slug: string): string => slug === 'index' ? '/docs/' : `/docs/${slug}/`;

// This is intentionally explicit. Filesystem order and a fallback title are not
// documentation IA: a new tracked Markdown page must be classified here first.
export const DOC_MANIFEST: readonly DocManifestEntry[] = [
  {
    source: 'docs/index.md', slug: 'index', route: '/docs/', group: 'Start here', order: 0,
    title: 'Aether Agents documentation',
    description: 'The canonical English manual, grouped for a beginner-first path through Aether Agents.',
    search: ['documentation', 'documentación', 'manual', 'inicio', 'start', 'home'],
    navigation: { kind: 'home', label: 'Documentation home', position: 0 },
  },
  {
    source: 'docs/start-here.md', slug: 'start-here', route: '/docs/start-here/', group: 'Start here', order: 1,
    title: 'Start here',
    description: 'A zero-context mental model, route choice and safe provider-free first exercise.',
    search: ['inicio', 'empezar', 'comenzar', 'primeros pasos', 'ruta', 'objetivo', 'beginner', 'orientation'],
    navigation: { kind: 'article', label: 'Start here', position: 1 },
  },
  {
    source: 'docs/getting-started.md', slug: 'getting-started', route: '/docs/getting-started/', group: 'Start here', order: 2,
    title: 'Getting started',
    description: 'Prerequisites, source inspection, expected observations and the initialization boundary.',
    search: ['primeros pasos', 'requisitos', 'instalar', 'inicio', 'source checkout', 'provider-free', 'begin'],
    navigation: { kind: 'article', label: 'Getting started', position: 2 },
  },
  {
    source: 'docs/product-boundary.md', slug: 'product-boundary', route: '/docs/product-boundary/', group: 'Core concepts', order: 1,
    title: 'Aether and Hermes product boundary',
    description: 'What Aether adds to Hermes and what it deliberately does not own.',
    search: ['conceptos', 'producto', 'límites', 'boundary', 'hermes', 'ownership', 'qué es'],
    navigation: { kind: 'article', label: 'Product boundary', position: 1 },
  },
  {
    source: 'docs/roles-and-authority.md', slug: 'roles-and-authority', route: '/docs/roles-and-authority/', group: 'Core concepts', order: 2,
    title: 'Roles and authority',
    description: 'Owner, Morfeo, Supervisor and Implementer responsibilities and decision limits.',
    search: ['conceptos', 'roles', 'autoridad', 'owner', 'morfeo', 'supervisor', 'implementer', 'responsabilidades'],
    navigation: { kind: 'article', label: 'Roles and authority', position: 2 },
  },
  {
    source: 'docs/authority.md', slug: 'authority', route: '/docs/authority/', group: 'Core concepts', order: 3,
    title: 'Authority and artifact ownership',
    description: 'Where design intent, current behavior, status, runtime state and evidence belong.',
    search: ['conceptos', 'autoridad', 'fuentes', 'artifacts', 'ownership', 'status', 'evidence'],
    navigation: { kind: 'article', label: 'Artifact ownership', position: 3 },
  },
  {
    source: 'docs/reference/glossary.md', slug: 'reference/glossary', route: '/docs/reference/glossary/', group: 'Core concepts', order: 4,
    title: 'Aether glossary',
    description: 'Concise definitions for Aether-specific terms and current-status language.',
    search: ['conceptos', 'glosario', 'vocabulario', 'terms', 'definitions', 'meaning'],
    navigation: { kind: 'article', label: 'Glossary', position: 4 },
  },
  {
    source: 'docs/guides/project-initialization.md', slug: 'guides/project-initialization', route: '/docs/guides/project-initialization/', group: 'Working with Aether', order: 1,
    title: 'Project initialization',
    description: 'The existing-Git-root and exact native Hermes Project prerequisites.',
    search: ['trabajar', 'proyecto', 'inicializar', 'repositorio', 'git', 'hermes project', 'project setup'],
    navigation: { kind: 'article', label: 'Project initialization', position: 1 },
  },
  {
    source: 'docs/guides/objective-contracts.md', slug: 'guides/objective-contracts', route: '/docs/guides/objective-contracts/', group: 'Working with Aether', order: 2,
    title: 'Objective Contracts and handoff',
    description: 'Scope, acceptance, immutability and handoff for substantial objectives.',
    search: ['trabajar', 'contrato', 'objetivo', 'alcance', 'aceptación', 'handoff', 'contract'],
    navigation: { kind: 'article', label: 'Objective Contracts', position: 2 },
  },
  {
    source: 'docs/guides/first-objective.md', slug: 'guides/first-objective', route: '/docs/guides/first-objective/', group: 'Working with Aether', order: 3,
    title: 'First objective: an illustrative pipeline walkthrough',
    description: 'A clearly illustrative, non-normative walkthrough of a substantial pipeline objective.',
    search: ['trabajar', 'primer objetivo', 'ejemplo', 'recorrido', 'pipeline', 'walkthrough', 'illustrative'],
    navigation: { kind: 'article', label: 'First objective', position: 3 },
  },
  {
    source: 'docs/guides/execution.md', slug: 'guides/execution', route: '/docs/guides/execution/', group: 'Working with Aether', order: 4,
    title: 'Execution: boards, sessions, worktrees, and review',
    description: 'Boards, sessions, isolated worktrees, review and unit evidence.',
    search: ['trabajar', 'ejecución', 'tablero', 'board', 'sesiones', 'worktree', 'review', 'revisión'],
    navigation: { kind: 'article', label: 'Execution', position: 4 },
  },
  {
    source: 'docs/guides/lifecycle.md', slug: 'guides/lifecycle', route: '/docs/guides/lifecycle/', group: 'Working with Aether', order: 5,
    title: 'Lifecycle',
    description: 'Direct and pipeline routes, recovery and the GitHub-backed terminal sequence.',
    search: ['trabajar', 'ciclo', 'flujo', 'lifecycle', 'pipeline', 'direct route', 'closeout'],
    navigation: { kind: 'article', label: 'Lifecycle', position: 5 },
  },
  {
    source: 'docs/guides/project-knowledge.md', slug: 'guides/project-knowledge', route: '/docs/guides/project-knowledge/', group: 'Working with Aether', order: 6,
    title: 'Project knowledge and role work memory',
    description: 'Optional technical graph context and separate role experiences.',
    search: ['trabajar', 'conocimiento', 'memoria', 'graphify', 'mapa', 'experiencia', 'project knowledge'],
    navigation: { kind: 'article', label: 'Project knowledge', position: 6 },
  },
  {
    source: 'docs/guides/observation.md', slug: 'guides/observation', route: '/docs/guides/observation/', group: 'Operations and safety', order: 1,
    title: 'Observation',
    description: 'Provider-free, read-only contract observation and its bounded outcomes.',
    search: ['operaciones', 'seguridad', 'observación', 'leer', 'read-only', 'observer', 'evidence'],
    navigation: { kind: 'article', label: 'Observation', position: 1 },
  },
  {
    source: 'docs/guides/policy-and-recovery.md', slug: 'guides/policy-and-recovery', route: '/docs/guides/policy-and-recovery/', group: 'Operations and safety', order: 2,
    title: 'Policy and recovery',
    description: 'Protected edges, reversibility-first local work and rollback-first recovery.',
    search: ['operaciones', 'seguridad', 'política', 'recuperación', 'rollback', 'safety', 'protected'],
    navigation: { kind: 'article', label: 'Policy and recovery', position: 2 },
  },
  {
    source: 'docs/reference/limitations-and-troubleshooting.md', slug: 'reference/limitations-and-troubleshooting', route: '/docs/reference/limitations-and-troubleshooting/', group: 'Operations and safety', order: 3,
    title: 'Limitations and troubleshooting',
    description: 'Current boundaries, safe diagnostics and explicit non-success conditions.',
    search: ['operaciones', 'seguridad', 'limitaciones', 'diagnóstico', 'troubleshooting', 'limits', 'failure'],
    navigation: { kind: 'article', label: 'Limitations and troubleshooting', position: 3 },
  },
  {
    source: 'docs/reference/cli.md', slug: 'reference/cli', route: '/docs/reference/cli/', group: 'Reference', order: 1,
    title: 'CLI reference',
    description: 'Parser commands, options, output and exit behavior in this build.',
    search: ['referencia', 'comandos', 'terminal', 'cli', 'command line', 'options', 'help'],
    navigation: { kind: 'article', label: 'CLI reference', position: 1 },
  },
  {
    source: 'docs/reference/plugins-and-tools.md', slug: 'reference/plugins-and-tools', route: '/docs/reference/plugins-and-tools/', group: 'Reference', order: 2,
    title: 'Plugins and tools',
    description: "Aether's registered Hermes plugin surfaces and action boundaries.",
    search: ['referencia', 'plugins', 'herramientas', 'tools', 'actions', 'hermes', 'schemas'],
    navigation: { kind: 'article', label: 'Plugins and tools', position: 2 },
  },
  {
    source: 'docs/reference/capabilities.md', slug: 'reference/capabilities', route: '/docs/reference/capabilities/', group: 'Reference', order: 3,
    title: 'Capability coverage',
    description: 'Generated current-status and traceability reference; do not edit it directly.',
    search: ['referencia', 'capacidades', 'estado', 'status', 'traceability', 'implemented', 'partial'],
    navigation: { kind: 'article', label: 'Capability coverage', position: 3 },
  },
];

const groupPosition = new Map<DocGroup, number>(DOC_GROUPS.map((group, index) => [group.label, index]));

/** Validate the complete manifest against the tracked Markdown corpus. */
export function validateManifest(trackedSources: readonly string[], entries: readonly DocManifestEntry[] = DOC_MANIFEST): void {
  const normalizedSources = trackedSources.map(source => source.replaceAll('\\', '/')).filter(source => source.endsWith('.md'));
  const tracked = new Set(normalizedSources);
  if (tracked.size !== normalizedSources.length) throw new Error('Tracked documentation corpus contains duplicate sources');
  const seenSources = new Set<string>();
  const seenSlugs = new Set<string>();
  const seenRoutes = new Set<string>();
  const positions = new Map<DocGroup, Set<number>>();

  for (const entry of entries) {
    if (!entry || typeof entry !== 'object') throw new Error('Documentation manifest record must be an object');
    if (typeof entry.source !== 'string' || !entry.source.startsWith('docs/') || !entry.source.endsWith('.md')) {
      throw new Error(`Documentation manifest source must be tracked Markdown: ${entry.source}`);
    }
    if (!tracked.has(entry.source)) throw new Error(`Documentation manifest entry has no tracked source: ${entry.source}`);
    if (typeof entry.slug !== 'string' || !entry.slug || entry.slug.startsWith('/') || entry.slug.endsWith('/') || entry.slug.split('/').some(segment => !/^[a-z0-9][a-z0-9-]*$/.test(segment))) {
      throw new Error(`Invalid documentation slug: ${entry.slug}`);
    }
    if (typeof entry.route !== 'string' || !entry.route) throw new Error(`Missing documentation route: ${entry.source}`);
    if (seenSources.has(entry.source)) throw new Error(`Duplicate documentation manifest source: ${entry.source}`);
    if (seenSlugs.has(entry.slug)) throw new Error(`Duplicate documentation slug: ${entry.slug}`);
    if (seenRoutes.has(entry.route)) throw new Error(`Duplicate documentation route: ${entry.route}`);
    if (!groupPosition.has(entry.group)) throw new Error(`Unknown documentation group: ${entry.group}`);
    if (entry.route !== routeForSlug(entry.slug)) throw new Error(`Route does not match slug for ${entry.source}: ${entry.route}`);
    if (entry.slug === 'index' && entry.route !== '/docs/') throw new Error('docs/index.md must map only to /docs/');
    if (entry.route === '/docs/index/') throw new Error('The /docs/index/ route is forbidden');
    if (!Number.isInteger(entry.order) || entry.order < 0 || (entry.slug !== 'index' && entry.order === 0)) {
      throw new Error(`Invalid documentation order: ${entry.source}`);
    }
    if (entry.slug === 'index' && (entry.group !== 'Start here' || entry.order !== 0)) {
      throw new Error('docs/index.md must be the first Start here entry');
    }
    if (typeof entry.title !== 'string' || typeof entry.description !== 'string' || !entry.title.trim() || !entry.description.trim() || !Array.isArray(entry.search) || entry.search.length === 0 || entry.search.some(term => typeof term !== 'string' || !term.trim())) {
      throw new Error(`Incomplete documentation metadata: ${entry.source}`);
    }
    const expectedNavigationKind = entry.slug === 'index' ? 'home' : 'article';
    if (!entry.navigation || typeof entry.navigation !== 'object' || entry.navigation.kind !== expectedNavigationKind || typeof entry.navigation.label !== 'string' || !entry.navigation.label.trim() || !Number.isInteger(entry.navigation.position) || entry.navigation.position !== entry.order) {
      throw new Error(`Incomplete documentation navigation metadata: ${entry.source}`);
    }
    seenSources.add(entry.source);
    seenSlugs.add(entry.slug);
    seenRoutes.add(entry.route);
    const groupPositions = positions.get(entry.group) ?? new Set<number>();
    if (groupPositions.has(entry.order)) throw new Error(`Duplicate order ${entry.order} in ${entry.group}`);
    groupPositions.add(entry.order);
    positions.set(entry.group, groupPositions);
  }

  const missing = [...tracked].filter(source => !seenSources.has(source)).sort();
  const stale = [...seenSources].filter(source => !tracked.has(source)).sort();
  if (missing.length) throw new Error(`Unclassified tracked documentation page(s): ${missing.join(', ')}`);
  if (stale.length) throw new Error(`Documentation manifest entry has no tracked source: ${stale.join(', ')}`);
  if (seenSources.size !== tracked.size) throw new Error('Documentation manifest and tracked corpus cardinality differ');
  const emptyGroups = DOC_GROUPS.filter(group => !positions.has(group.label)).map(group => group.label);
  if (emptyGroups.length) throw new Error(`Documentation group has no manifest records: ${emptyGroups.join(', ')}`);
  for (const [group, groupOrders] of positions) {
    const expected = [...groupOrders].sort((a, b) => a - b).map((_, index) => group === 'Start here' ? index : index + 1);
    if (JSON.stringify([...groupOrders].sort((a, b) => a - b)) !== JSON.stringify(expected)) {
      throw new Error(`Documentation group order must be contiguous: ${group}`);
    }
  }

}

export interface Heading {
  depth: number;
  id: string;
  text: string;
}

export function assertUniqueHeadingIds(headings: readonly Heading[], source = 'documentation page'): void {
  const seen = new Set<string>();
  for (const heading of headings) {
    if (seen.has(heading.id)) throw new Error(`Duplicate heading id "${heading.id}" in ${source}`);
    seen.add(heading.id);
  }
}

export interface Doc {
  slug: string;
  route: string;
  title: string;
  description: string;
  group: DocGroup;
  order: number;
  navigation: DocManifestEntry['navigation'];
  search: string[];
  source: string;
  sourcePath: string;
  sourceRevision: string;
  html: string;
  text: string;
  headings: Heading[];
}

async function markdownPaths(dir: string): Promise<string[]> {
  const entries = await readdir(dir, { withFileTypes: true });
  const groups = await Promise.all(entries.map(entry =>
    entry.isDirectory()
      ? markdownPaths(path.join(dir, entry.name))
      : entry.isFile() && entry.name.endsWith('.md') ? [path.join(dir, entry.name)] : [],
  ));
  return groups.flat();
}

function trackedMarkdownSources(): string[] {
  const output = execFileSync('git', ['ls-files', '--', 'docs'], { cwd: repository, encoding: 'utf8' });
  return output.split('\n').map(source => source.trim()).filter(Boolean).filter(source => source.endsWith('.md'));
}

let cached: Promise<Doc[]> | undefined;
export function loadDocs(): Promise<Doc[]> {
  return cached ||= buildDocs();
}

async function buildDocs(): Promise<Doc[]> {
  const trackedSources = trackedMarkdownSources();
  validateManifest(trackedSources);
  const bySource = new Map(DOC_MANIFEST.map(entry => [entry.source, entry]));
  const trackedRepositoryPaths = new Set(execFileSync('git', ['ls-files', '--'], { cwd: repository, encoding: 'utf8' }).split('\n').map(source => source.trim()).filter(Boolean));
  const files = (await markdownPaths(docsRoot)).filter(file => bySource.has(path.relative(repository, file).split(path.sep).join('/')));
  const loadedSources = new Set(files.map(file => path.relative(repository, file).split(path.sep).join('/')));
  const missingFiles = trackedSources.filter(source => !loadedSources.has(source));
  if (missingFiles.length) throw new Error(`Tracked documentation source is missing from the checkout: ${missingFiles.join(', ')}`);
  const localPages = new Set(files.map(file => path.resolve(file)));
  const localReferences: { sourcePath: string; target: string; fragment: string }[] = [];

  const repositoryPathExists = (target: string): boolean => {
    const relative = path.relative(repository, target).split(path.sep).join('/');
    if (relative.startsWith('../') || relative === '..' || !existsSync(target)) return false;
    if (trackedRepositoryPaths.has(relative)) return true;
    const prefix = `${relative.replace(/\/$/, '')}/`;
    return [...trackedRepositoryPaths].some(source => source.startsWith(prefix));
  };

  const results: Doc[] = [];

  for (const file of files) {
    const sourcePath = path.relative(repository, file).split(path.sep).join('/');
    const metadata = bySource.get(sourcePath);
    if (!metadata) throw new Error(`No documentation manifest record for ${sourcePath}`);
    const markdown = await readFile(file, 'utf8');
    const sourceTitle = markdown.match(/^#\s+(.+)$/m)?.[1]?.trim();
    if (sourceTitle !== metadata.title) {
      throw new Error(`Manifest title mismatch for ${sourcePath}: expected "${metadata.title}", found "${sourceTitle ?? '<missing>'}"`);
    }
    const headings: Heading[] = [];
    const slugger = new GithubSlugger();
    const parser = new Marked({
      gfm: true,
      walkTokens(token) {
        if (token.type !== 'link' && token.type !== 'image') return;
        const href = token.href ?? '';
        if (!href || href.startsWith('//')) {
          if (href.startsWith('//')) throw new Error(`Unsafe documentation URL scheme in ${sourcePath}: ${href}`);
          return;
        }
        if (/^[a-z][a-z\d+.-]*:/i.test(href)) {
          if (/^(https?:|mailto:)/i.test(href)) return;
          throw new Error(`Unsafe documentation URL scheme in ${sourcePath}: ${href}`);
        }
        if (href.startsWith('/')) return;
        const hashAt = href.indexOf('#');
        const rel = hashAt === -1 ? href : href.slice(0, hashAt);
        const fragment = hashAt === -1 ? '' : href.slice(hashAt + 1);
        let decodedRelative: string;
        let decodedFragment: string;
        try {
          decodedRelative = decodeURIComponent(rel);
          decodedFragment = decodeURIComponent(fragment);
        } catch {
          throw new Error(`Malformed documentation URL in ${sourcePath}: ${href}`);
        }
        const target = rel ? path.resolve(path.dirname(file), decodedRelative) : path.resolve(file);
        const suffix = fragment ? `#${fragment}` : '';
        if (!repositoryPathExists(target)) {
          throw new Error(`Documentation source link does not resolve from ${sourcePath}: ${href}`);
        }
        if (localPages.has(target)) {
          const targetSource = path.relative(repository, target).split(path.sep).join('/');
          const targetMetadata = bySource.get(targetSource);
          if (!targetMetadata) throw new Error(`Documentation link targets an unclassified page from ${sourcePath}: ${href}`);
          localReferences.push({ sourcePath, target, fragment: decodedFragment });
          if (rel) token.href = `${sitePath(targetMetadata.route)}${suffix}`;
          return;
        }
        const relative = path.relative(repository, target).split(path.sep).join('/');
        if (relative.startsWith('../') || relative === '..') {
          throw new Error(`Documentation link escapes repository from ${sourcePath}: ${href}`);
        }
        token.href = publicSource + relative + suffix;
      },
    });
    let html = await parser.parse(markdown);
    html = html.replace(/<h([1-6])>([\s\S]*?)<\/h\1>/g, (_, depth, body) => {
      const plain = sanitizeHtml(body, { allowedTags: [], allowedAttributes: {} });
      const id = slugger.slug(plain);
      headings.push({ depth: Number(depth), id, text: plain });
      return `<h${depth} id="${id}" tabindex="-1">${body}</h${depth}>`;
    });
    assertUniqueHeadingIds(headings, sourcePath);
    html = sanitizeHtml(html, {
      allowedTags: [...sanitizeHtml.defaults.allowedTags, 'details', 'summary', 'img'],
      allowedAttributes: {
        ...sanitizeHtml.defaults.allowedAttributes,
        '*': ['id', 'tabindex', 'role', 'aria-label', 'aria-labelledby'],
        code: ['class'],
        img: ['src', 'alt', 'width', 'height'],
        a: ['href', 'title'],
      },
      allowedSchemes: ['http', 'https', 'mailto'],
      allowProtocolRelative: false,
    }).replace(/<pre>/g, '<pre tabindex="0">')
      .replace(/<table>/g, '<div class="table-wrap" tabindex="0" role="region" aria-label="Scrollable table"><table>')
      .replace(/<\/table>/g, '</table></div>');
    const text = sanitizeHtml(html, { allowedTags: [], allowedAttributes: {} }).replace(/\s+/g, ' ').trim();
    results.push({
      slug: metadata.slug,
      route: metadata.route,
      title: metadata.title,
      description: metadata.description,
      group: metadata.group,
      order: metadata.order,
      navigation: metadata.navigation,
      search: [...metadata.search],
      source: publicSource + sourcePath,
      sourcePath,
      sourceRevision,
      html,
      text,
      headings,
    });
  }

  const headingIdsByPath = new Map(results.map(doc => [path.resolve(repository, doc.sourcePath), new Set(doc.headings.map(heading => heading.id))]));
  for (const reference of localReferences) {
    if (reference.fragment && !headingIdsByPath.get(path.resolve(reference.target))?.has(reference.fragment)) {
      throw new Error(`Documentation fragment does not resolve from ${reference.sourcePath}: #${reference.fragment}`);
    }
  }

  return results.sort((a, b) => {
    const groupDelta = groupPosition.get(a.group)! - groupPosition.get(b.group)!;
    return groupDelta || a.order - b.order;
  });
}
