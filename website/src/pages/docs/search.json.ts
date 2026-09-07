import { loadDocs } from '../../lib/docs';
export async function GET() {
  const docs = await loadDocs();
  return new Response(JSON.stringify(docs.map(({slug,title,text,description}) => ({slug,title,text,description}))), {headers:{'Content-Type':'application/json; charset=utf-8'}});
}
