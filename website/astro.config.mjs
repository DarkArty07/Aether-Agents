import { defineConfig } from 'astro/config';

const githubPages = process.env.AETHER_PAGES === '1';

export default defineConfig({
  output: 'static',
  site: githubPages ? 'https://darkarty07.github.io' : undefined,
  base: githubPages ? '/Aether-Agents/' : '/',
  trailingSlash: 'always',
  devToolbar: { enabled: false },
});
