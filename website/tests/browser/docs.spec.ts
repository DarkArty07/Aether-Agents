import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const docsRoutes = [
  '/docs/',
  '/docs/start-here/',
  '/docs/guides/first-objective/',
  '/docs/reference/capabilities/',
];

async function searchRecordCount(page: Page): Promise<number> {
  const response = await page.request.get('/docs/search.json');
  expect(response.ok()).toBeTruthy();
  return (await response.json()).length;
}

test.describe('grouped documentation UX', () => {
  test('index exposes the five ordered groups and complete navigation', async ({ page }) => {
    await page.goto('/docs/');
    const recordCount = await searchRecordCount(page);
    await expect(page.locator('.docs-index-group')).toHaveCount(5);
    await expect(page.locator('.docs-index-group').evaluateAll(groups => groups.map(group => group.getAttribute('data-doc-group')))).resolves.toEqual([
      'Start here', 'Core concepts', 'Working with Aether', 'Operations and safety', 'Reference',
    ]);
    await expect(page.locator('.docs-index-list article[data-document]')).toHaveCount(recordCount);
    await expect(page.locator('.docs-index-list article[data-doc-route="/docs/"]')).toHaveCount(1);
    await expect(page.locator('.docs-navigation').first().locator('[data-document]')).toHaveCount(recordCount);
    await expect(page.locator('.docs-navigation').first().locator('[aria-current="page"]')).toHaveAttribute('href', '/docs/');
    await expect(page.locator('a[href="/docs/index/"]')).toHaveCount(0);
    await expect(page.locator('html')).toHaveAttribute('lang', 'es-MX');
    await expect(page.locator('[data-doc-content]')).toHaveAttribute('lang', 'en');
    expect(await page.locator('.docs-index-group h2').evaluateAll(headings => headings.map(heading => heading.getAttribute('lang')))).toEqual(Array(5).fill('en'));
    expect(await page.locator('.docs-group-header > p').evaluateAll(descriptions => descriptions.map(description => description.getAttribute('lang')))).toEqual(Array(5).fill('es-MX'));
    expect(await page.locator('.docs-index-list article[data-document] h3, .docs-index-list article[data-document] > p:not(.docs-card-meta)').evaluateAll(metadata => metadata.map(element => element.getAttribute('lang')))).toEqual(Array(recordCount * 2).fill('en'));
  });

  test('article context identifies group/current page, headings and within-group adjacency', async ({ page }) => {
    await page.goto('/docs/guides/first-objective/');
    await expect(page.locator('[data-doc-page]')).toHaveAttribute('data-doc-group', 'Working with Aether');
    await expect(page.locator('.docs-position')).toHaveText('CHAPTER 3 OF 6');
    await expect(page.locator('.docs-sidebar a[aria-current="page"]')).toHaveText('First objective');
    await expect(page.locator('.docs-menu-mobile .docs-navigation a[aria-current="page"]')).toHaveText('First objective');
    await expect(page.locator('.docs-article-actions a[href="/docs/#documentation-search"]')).toBeVisible();
    await expect(page.locator('.docs-status-notice')).toContainText('Canonical English manual');
    await expect(page.locator('.docs-status-notice')).toContainText('stabilization build');
    await expect(page.locator('.prose h1[id][tabindex="-1"]')).toHaveCount(1);
    await expect(page.locator('.docs-toc a')).toHaveCount(12);
    await expect(page.locator('[data-adjacent="previous"]')).toHaveAttribute('href', '/docs/guides/objective-contracts/');
    await expect(page.locator('[data-adjacent="next"]')).toHaveAttribute('href', '/docs/guides/execution/');
  });

  test('English and Mexican-Spanish orientation terms search title, group metadata and body', async ({ page }) => {
    await page.goto('/docs/');
    await page.locator('#docs-search').fill('conocimiento');
    await expect(page.locator('#search-status')).toContainText(/resultados? encontrados?/);
    await expect(page.locator('.docs-index-list article:not([hidden])')).toHaveCount(1);
    await expect(page.locator('.docs-index-list article:not([hidden])')).toHaveAttribute('data-document', 'guides/project-knowledge');
    await page.locator('#docs-search').fill('worktree');
    await expect(page.locator('#search-status')).toContainText(/resultados? encontrados?/);
    await expect(page.locator('.docs-index-list article[data-document="guides/execution"]')).toBeVisible();
    await page.locator('#docs-search').fill('zzznomatchzzz');
    await expect(page.locator('#search-status')).toContainText('No hay resultados');
    await expect(page.locator('#no-results')).toBeVisible();
    await expect(page.locator('#search-count')).toContainText('0 documentos');
  });

  test('search reports a failed index while preserving the grouped index', async ({ page }) => {
    await page.route('**/docs/search.json', route => route.abort());
    await page.goto('/docs/');
    const recordCount = await page.locator('.docs-index-list article[data-document]').count();
    await page.locator('#docs-search').fill('Graphify');
    await expect(page.locator('#search-status')).toContainText('No se pudo cargar');
    await expect(page.locator('.docs-index-list article')).toHaveCount(recordCount);
    await expect(page.locator('.docs-index-group')).toHaveCount(5);
  });

  test('direct heading fragments land below sticky chrome and remain keyboard reachable', async ({ page }) => {
    await page.goto('/docs/guides/first-objective/');
    const heading = page.locator('.prose h2').nth(1);
    const id = await heading.getAttribute('id');
    expect(id).toBeTruthy();
    await page.goto(`/docs/guides/first-objective/#${encodeURIComponent(id!)}`);
    await expect(heading).toBeVisible();
    const [headingBox, headerBox] = await Promise.all([heading.boundingBox(), page.locator('.site-header').boundingBox()]);
    expect(headingBox).not.toBeNull();
    expect(headerBox).not.toBeNull();
    expect(headingBox!.y).toBeGreaterThanOrEqual(headerBox!.height - 2);
    await page.locator('.docs-toc a').first().focus();
    await expect(page.locator(':focus')).toHaveAttribute('href', /^#/);
  });

  test('representative docs have no page overflow and keep code/table scrolling local', async ({ page }) => {
    for (const route of docsRoutes) {
      await page.goto(route);
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy();
    }
    await page.goto('/docs/start-here/');
    const regions = await page.locator('[data-doc-content] pre, [data-doc-content] .table-wrap').evaluateAll(elements => elements.map(element => ({
      tabIndex: (element as HTMLElement).tabIndex,
      overflowX: getComputedStyle(element).overflowX,
      contained: element.scrollWidth >= element.clientWidth,
    })));
    expect(regions.length).toBeGreaterThanOrEqual(2);
    expect(regions.every(region => region.tabIndex === 0 && ['auto', 'scroll'].includes(region.overflowX) && region.contained)).toBeTruthy();
  });

  test('mobile documentation navigation opens and keeps current semantics', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'mobile', 'mobile-only navigation check');
    await page.goto('/docs/guides/first-objective/');
    await page.locator('.docs-menu-mobile summary').click();
    await expect(page.locator('.docs-menu-mobile .docs-navigation')).toBeVisible();
    await expect(page.locator('.docs-menu-mobile a[aria-current="page"]')).toHaveText('First objective');
    await page.locator('.docs-menu-mobile a[href="/docs/guides/execution/"]').click();
    await expect(page).toHaveURL(/\/docs\/guides\/execution\/$/);
    await expect(page.locator('[data-doc-page]')).toHaveAttribute('data-doc-group', 'Working with Aether');
  });

  test('essential article and grouped index content survive without JavaScript', async ({ browser }, testInfo) => {
    const context = await browser.newContext({
      javaScriptEnabled: false,
      viewport: testInfo.project.name === 'mobile' ? { width: 390, height: 844 } : { width: 1440, height: 1000 },
    });
    const page = await context.newPage();
    await page.goto('http://127.0.0.1:4321/docs/');
    const indexRecordCount = await page.locator('.docs-index-list article[data-document]').count();
    await expect(page.locator('.docs-index-group')).toHaveCount(5);
    await expect(page.locator('.docs-index-list article[data-document]')).toHaveCount(indexRecordCount);
    await expect(page.locator('.docs-search')).not.toBeVisible();
    await expect(page.locator('.docs-search-unavailable')).toBeVisible();
    await page.goto('http://127.0.0.1:4321/docs/guides/first-objective/');
    await expect(page.locator('.prose h1')).toBeVisible();
    await expect(page.locator('.docs-sidebar .docs-navigation a')).toHaveCount(19);
    if (testInfo.project.name === 'mobile') {
      await page.locator('.docs-menu-mobile summary').click();
      await expect(page.locator('.docs-menu-mobile .docs-navigation a')).toHaveCount(19);
    }
    await context.close();
  });

  test('documentation representatives pass automated WCAG A and AA checks', async ({ page }) => {
    for (const route of docsRoutes) {
      await page.goto(route);
      await page.emulateMedia({ reducedMotion: 'reduce' });
      const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
      expect(results.violations.map(violation => ({ id: violation.id, impact: violation.impact, nodes: violation.nodes.map(node => node.target) }))).toEqual([]);
    }
  });

  test('documentation recovery keeps the manual and search route reachable', async ({ page }) => {
    await page.goto('/missing-document-route/');
    await expect(page.locator('[data-doc-recovery]')).toBeVisible();
    await expect(page.locator('[data-doc-recovery] a[href="/docs/"]')).toContainText('DOCUMENTACIÓN');
    await expect(page.locator('[data-doc-recovery] a[href="/docs/#documentation-search"]')).toBeVisible();
    await page.locator('[data-doc-recovery] a[href="/docs/"]').click();
    await expect(page).toHaveURL(/\/docs\/$/);
  });
});
