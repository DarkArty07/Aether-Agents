import sharp from 'sharp';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';

const assets = [
  { name: 'aether-morfeo-hero', sourceName: 'aether-morfeo-refined', sha: '25a0d29e28dda00f2c1c598e1605d99dcfb858e7df9d5a5c1898a0c06118159d' },
  { name: 'aether-knowledge-graph', sha: '7ee001d6d6a2f8837a1088ce0b2293601f4d5d89c97dd1ec4ce22f271663ff70' },
  { name: 'aether-ether-finale', sha: '86d7df0e7c5452dbef3e699f9ffcaf492871ee811553832435e0507e46a0a93e' },
];
await mkdir('public/images', { recursive: true });
const manifest = [];
for (const { name, sourceName = name, sha } of assets) {
  const source = await readFile(`assets/images/${sourceName}.png`);
  if (createHash('sha256').update(source).digest('hex') !== sha) {
    throw new Error(`Approved artwork has changed: ${name}`);
  }
  const metadata = await sharp(source).metadata();
  for (const width of [800, 1280, 1672]) {
    const output = await sharp(source).resize({ width, withoutEnlargement: true })
      .webp(width === metadata.width ? { lossless: true, effort: 6 } : { quality: 95, smartSubsample:true, effort: 5 }).toBuffer();
    await writeFile(`public/images/${name}-${width}.webp`, output);
    manifest.push({ name, width, sourceWidth:metadata.width, sourceHeight:metadata.height, bytes: output.length, sourceSha256: sha, lossless:width === metadata.width });
  }
  if (name === 'aether-knowledge-graph') {
    // Retain the selected artwork's sculpture/column, not its baked-in graph or copy.
    // The graph, labels and lights are now live SVG/HTML, not enlarged raster details.
    const mask = stops => Buffer.from(`<svg width="${metadata.width}" height="${metadata.height}" xmlns="http://www.w3.org/2000/svg"><defs>${stops}</defs><rect width="100%" height="100%" fill="url(#mask)"/></svg>`);
    const horizontal = mask('<linearGradient id="mask"><stop stop-color="white" stop-opacity=".8"/><stop offset=".12" stop-color="white" stop-opacity=".8"/><stop offset=".23" stop-color="white" stop-opacity="0"/><stop offset=".82" stop-color="white" stop-opacity="0"/><stop offset=".86" stop-color="white" stop-opacity=".8"/><stop offset=".88" stop-color="white" stop-opacity=".8"/><stop offset=".915" stop-color="white" stop-opacity="0"/></linearGradient>');
    const vertical = mask('<linearGradient id="mask" x2="0" y2="1"><stop stop-color="white" stop-opacity="0"/><stop offset=".22" stop-color="white" stop-opacity="0"/><stop offset=".3" stop-color="white"/><stop offset=".74" stop-color="white"/><stop offset=".84" stop-color="white" stop-opacity="0"/></linearGradient>');
    const decor = await sharp(source).composite([{input:horizontal,blend:'dest-in'},{input:vertical,blend:'dest-in'}]).png().toBuffer();
    for (const width of [800,1672]) {
      const image = await sharp(decor).resize({width,withoutEnlargement:true}).webp({lossless:true,effort:6}).toBuffer();
      await writeFile(`public/images/aether-knowledge-architecture-${width}.webp`,image);
      manifest.push({name:'aether-knowledge-architecture',width,bytes:image.length,sourceSha256:sha,lossless:true});
    }
  }
  console.log(`${name}: approved PNG ${metadata.width} × ${metadata.height}`);
}
await writeFile('public/images/manifest.json', JSON.stringify(manifest, null, 2) + '\n');

// Preserve the original licenses alongside the self-hosted font build output.
await mkdir('public/font-licenses', { recursive: true });
for (const family of ['barlow-condensed', 'space-grotesk', 'ibm-plex-mono']) {
  const license = await readFile(`node_modules/@fontsource/${family}/LICENSE`, 'utf8');
  await writeFile(`public/font-licenses/${family}.txt`, license);
}
