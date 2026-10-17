/**
 * Capture true-3D Three.js scene frames via Playwright, then encode WEBM.
 */
import { chromium } from 'playwright';
import { createServer } from 'http';
import { readFileSync, existsSync, mkdirSync, rmSync, writeFileSync, copyFileSync } from 'fs';
import { extname, join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { encodeTelegramVp9 } from '../vp9_telegram_encode.mjs';

const ROOT = dirname(fileURLToPath(import.meta.url));
const PROJECT = join(ROOT, '..');
const FRAMES = join(ROOT, 'render_frames');
const TOTAL = Number(process.env.HL_FRAMES || 90);

const MIME = {
  '.html': 'text/html',
  '.js': 'text/javascript',
  '.mjs': 'text/javascript',
  '.css': 'text/css',
  '.svg': 'image/svg+xml',
  '.json': 'application/json',
};

function serve() {
  return new Promise((resolve) => {
    const server = createServer((req, res) => {
      let url = decodeURIComponent(req.url.split('?')[0]);
      if (url === '/') url = '/scene_shatter.html';
      const path = join(PROJECT, url.replace(/^\//, ''));
      if (!path.startsWith(PROJECT) || !existsSync(path)) {
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
  /* Hard wipe — no leftover frames / webms that could “overlay” */
  if (existsSync(FRAMES)) rmSync(FRAMES, { recursive: true, force: true });
  mkdirSync(FRAMES, { recursive: true });
  for (const n of ['hyperlinks-space-sticker.webm', 'hyperlinks-space-emoji.webm']) {
    const p = join(ROOT, n);
    if (existsSync(p)) rmSync(p);
  }

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
  await page.goto(`http://127.0.0.1:${port}/scene_shatter.html?v=${Date.now()}`, {
    waitUntil: 'networkidle',
  });
  await page.waitForFunction(() => window.ready === true, null, { timeout: 60000 });

  console.log(`Capturing ${TOTAL} frames...`);
  for (let fr = 1; fr <= TOTAL; fr++) {
    await page.evaluate((f) => {
      window.setFrame(f);
    }, fr);
    await page.waitForTimeout(20);
    const b64 = await page.evaluate(() => {
      const c = document.querySelector('canvas');
      return c.toDataURL('image/png').split(',')[1];
    });
    writeFileSync(join(FRAMES, `frame_${String(fr).padStart(4, '0')}.png`), Buffer.from(b64, 'base64'));
    if (fr % 15 === 0) console.log(`  frame ${fr}/${TOTAL}`);
  }

  await browser.close();
  server.close();

  await encodeTelegramVp9({ root: ROOT, framesDir: FRAMES, total: TOTAL, size: 512, name: 'hyperlinks-space-sticker.webm' });
  await encodeTelegramVp9({ root: ROOT, framesDir: FRAMES, total: TOTAL, size: 100, name: 'hyperlinks-space-emoji.webm' });

  for (const [src, dest] of [
    ['hyperlinks-space-sticker.webm', 'hyperlinks-space-sticker-shatter.webm'],
    ['hyperlinks-space-emoji.webm', 'hyperlinks-space-emoji-shatter.webm'],
  ]) {
    copyFileSync(join(ROOT, src), join(ROOT, dest));
    copyFileSync(join(ROOT, src), join(PROJECT, dest));
  }
  console.log('Done');
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
