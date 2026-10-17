/**
 * Metallic sign-only sticker + emoji (stainless N, white supernova).
 * Does not touch hyperlinks-space-*-sign.webm (emerald).
 */
import { chromium } from 'playwright';
import { createServer } from 'http';
import { readFileSync, existsSync, mkdirSync, rmSync, writeFileSync, copyFileSync } from 'fs';
import { extname, join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { encodeTelegramVp9 } from './vp9_telegram_encode.mjs';

const ROOT = dirname(fileURLToPath(import.meta.url));
const FRAMES = join(ROOT, 'render_frames_sign_metal');
const VARIANT = join(ROOT, 'variant_signonly_metal');
const TOTAL = Number(process.env.HL_FRAMES || 90);

const MIME = {
  '.html': 'text/html',
  '.js': 'text/javascript',
  '.mjs': 'text/javascript',
  '.css': 'text/css',
  '.svg': 'image/svg+xml',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
};

function serve() {
  return new Promise((resolve) => {
    const server = createServer((req, res) => {
      let url = decodeURIComponent(req.url.split('?')[0]);
      if (url === '/') url = '/scene_volumetric3d.html';
      const path = join(ROOT, url.replace(/^\//, ''));
      if (!path.startsWith(ROOT) || !existsSync(path)) {
        res.writeHead(404); res.end('missing'); return;
      }
      const ext = extname(path);
      res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
      res.end(readFileSync(path));
    });
    server.listen(0, '127.0.0.1', () => {
      const { port } = server.address();
      resolve({ server, port });
    });
  });
}

async function main() {
  if (existsSync(FRAMES)) rmSync(FRAMES, { recursive: true, force: true });
  mkdirSync(FRAMES, { recursive: true });
  mkdirSync(VARIANT, { recursive: true });

  const { server, port } = await serve();
  const browser = await chromium.launch({
    headless: true,
    args: ['--use-angle=d3d11', '--ignore-gpu-blocklist'],
  });
  const page = await browser.newPage({
    viewport: { width: 512, height: 512 },
    deviceScaleFactor: 1,
  });

  page.on('console', (msg) => console.log('[page]', msg.text()));
  await page.goto(`http://127.0.0.1:${port}/scene_volumetric3d.html?signMetal=1&v=${Date.now()}`, {
    waitUntil: 'networkidle',
  });
  await page.waitForFunction(() => window.ready === true, null, { timeout: 90000 });

  console.log(`Capturing sign-metal ${TOTAL} frames @ 512² (transparent)...`);
  for (let fr = 1; fr <= TOTAL; fr++) {
    await page.evaluate((f) => { window.setFrame(f); }, fr);
    await page.waitForTimeout(20);
    const b64 = await page.evaluate(() => {
      const c = document.querySelector('canvas');
      return c.toDataURL('image/png').split(',')[1];
    });
    writeFileSync(join(FRAMES, `frame_${String(fr).padStart(4, '0')}.png`), Buffer.from(b64, 'base64'));
    if (fr % 15 === 0) console.log(`  frame ${fr}/${TOTAL}`);
  }
  copyFileSync(
    join(FRAMES, 'frame_0001.png'),
    join(FRAMES, `frame_${String(TOTAL).padStart(4, '0')}.png`),
  );

  await browser.close();
  server.close();

  await encodeTelegramVp9({
    root: ROOT, framesDir: FRAMES, total: TOTAL, size: 512,
    name: 'hyperlinks-space-sticker-sign-metal.webm',
  });
  await encodeTelegramVp9({
    root: ROOT, framesDir: FRAMES, total: TOTAL, size: 100,
    name: 'hyperlinks-space-emoji-sign-metal.webm',
  });

  copyFileSync(join(ROOT, 'hyperlinks-space-sticker-sign-metal.webm'), join(VARIANT, 'hyperlinks-space-sticker-sign-metal.webm'));
  copyFileSync(join(ROOT, 'hyperlinks-space-emoji-sign-metal.webm'), join(VARIANT, 'hyperlinks-space-emoji-sign-metal.webm'));
  writeFileSync(join(VARIANT, 'README.md'), `# Sign-only metal sticker + emoji

Stainless **N** (same chrome as lighter I/S) + white supernova on a **transparent** canvas.

Does **not** replace \`hyperlinks-space-*-sign.webm\`.

\`\`\`bash
HL_FRAMES=90 node capture_signonly_metal.mjs
\`\`\`

## Outputs
- \`hyperlinks-space-sticker-sign-metal.webm\` — 512² VP9+alpha, ≤256 KB
- \`hyperlinks-space-emoji-sign-metal.webm\` — 100² VP9+alpha, ≤64 KB

Preview: \`../preview_sign_metal.html\`
`);
  console.log('Done (sign-metal sticker + emoji)');
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
