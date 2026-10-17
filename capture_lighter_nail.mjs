/**
 * Capture the lighter+nail sticker and emoji.
 * Isolated from the original lighter pipeline (own scene, frames, pass log, output).
 * Does not overwrite hyperlinks-space-sticker-lighter.webm / emoji / preview gif.
 */
import { chromium } from 'playwright';
import { createServer } from 'http';
import { readFileSync, existsSync, mkdirSync, rmSync, writeFileSync, copyFileSync } from 'fs';
import { extname, join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { encodeTelegramVp9 } from './vp9_telegram_encode.mjs';

const ROOT = dirname(fileURLToPath(import.meta.url));
const FRAMES = join(ROOT, 'render_frames_lighter_nail');
const VARIANT = join(ROOT, 'variant_lighter_nail');
const TOTAL = Number(process.env.HL_FRAMES || 90);
const PREVIEW = process.env.HL_PREVIEW === '1';

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
      if (url === '/') url = '/scene_lighter_nail.html';
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
  page.on('pageerror', (err) => console.error('[pageerror]', err));
  await page.goto(`http://127.0.0.1:${port}/scene_lighter_nail.html?v=${Date.now()}`, {
    waitUntil: 'networkidle',
  });
  await page.waitForFunction(() => window.ready === true, null, { timeout: 60000 });

  const frames = PREVIEW
    ? [1, 28, 32, 36, 42, 48, 55, 76, 82, 88, 90]
    : [...Array(TOTAL)].map((_, i) => i + 1);
  console.log(`Capturing ${PREVIEW ? 'preview' : TOTAL} frames...`);
  for (const fr of frames) {
    await page.evaluate((f) => { window.setFrame(f); }, fr);
    await page.waitForTimeout(20);
    const b64 = await page.evaluate(() => {
      const c = document.querySelector('canvas');
      return c.toDataURL('image/png').split(',')[1];
    });
    writeFileSync(join(FRAMES, `frame_${String(fr).padStart(4, '0')}.png`), Buffer.from(b64, 'base64'));
    if (!PREVIEW && fr % 15 === 0) console.log(`  frame ${fr}/${TOTAL}`);
  }

  await browser.close();
  server.close();

  if (PREVIEW) {
    console.log('Preview frames written to render_frames_lighter_nail');
    return;
  }

  await encodeTelegramVp9({ root: ROOT, framesDir: FRAMES, total: TOTAL, size: 512, name: 'hyperlinks-space-sticker-lighter-nail.webm' });
  await encodeTelegramVp9({ root: ROOT, framesDir: FRAMES, total: TOTAL, size: 100, name: 'hyperlinks-space-emoji-lighter-nail.webm' });

  copyFileSync(
    join(ROOT, 'hyperlinks-space-sticker-lighter-nail.webm'),
    join(VARIANT, 'hyperlinks-space-sticker-lighter-nail.webm'),
  );
  copyFileSync(
    join(ROOT, 'hyperlinks-space-emoji-lighter-nail.webm'),
    join(VARIANT, 'hyperlinks-space-emoji-lighter-nail.webm'),
  );
  console.log('Done (lighter nail sticker + emoji)');
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
