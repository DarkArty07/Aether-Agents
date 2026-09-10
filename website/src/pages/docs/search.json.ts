import { DOC_GROUPS, loadDocs } from '../../lib/docs';

export async function GET() {
  const docs = await loadDocs();
  const groupDescriptions = new Map(DOC_GROUPS.map(group => [group.label, group.description]));
  const records = docs.map(({ html, ...doc }) => ({
    ...doc,
    groupDescription: groupDescriptions.get(doc.group),
  }));
  return new Response(JSON.stringify(records), {
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'public, max-age=0, must-revalidate',
    },
  });
}
