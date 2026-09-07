const configuredBase = import.meta.env.BASE_URL || '/';
const base = configuredBase.endsWith('/') ? configuredBase : `${configuredBase}/`;

/** Prefix a site-root path with Astro's configured base (GitHub Pages uses /Aether-Agents/). */
export function sitePath(pathname: string): string {
  if (!pathname.startsWith('/')) return pathname;
  if (pathname === '/') return base;
  return `${base}${pathname.slice(1)}`;
}

export const siteBase = base;
