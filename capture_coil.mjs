/**
 * Capture the exotic coil sticker and emoji.
 * Isolated from sign / lighter / volumetric pipelines.
 */
import { chromium } from 'playwright';
import { spawn } from 'child_process';
import { createServer } from 'http';
import { readFileSync, existsSync, mkdirSync, rmSync, writeFileSync, copyFileSync } from 'fs';
import { extname, join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { encodeTelegramVp9 } from './vp9_telegram_encode.mjs';

const ROOT = dirname(fileURLToPath(import.meta.url));
const FRAMES = join(ROOT, 'render_frames_coil');
const VARIANT = join(ROOT, 'variant_coil');
const TOTAL = Number(process.env.HL_FRAMES || 90);
const PREVIEW = process.env.HL_PREVIEW === '1';
const FFMPEG = process.env.FFMPEG ||
  String.raw`C:\Users\ASUS\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-full_build\bin\ffmpeg.exe`;

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
      if (url === '/') url = '/scene_coil.html';
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

function run(cmd, args) {
  return new Promise((resolve, reject) => {
    const p = spawn(cmd, args, { stdio: 'inherit' });
    p.on('exit', (code) => (code === 0 ? resolve() : reject(new Error(`exit ${code}`))));
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
  await page.goto(`http://127.0.0.1:${port}/scene_coil.html?v=${Date.now()}`, {
    waitUntil: 'networkidle',
  });
  await page.waitForFunction(() => window.ready === true, null, { timeout: 90000 });

  const frames = PREVIEW
    ? [1, 20, 32, 40, 48, 58, 72, 82, 90]
    : [...Array(TOTAL)].map((_, i) => i + 1);
  console.log(`Capturing ${PREVIEW ? 'preview' : TOTAL} frames...`);
  for (const fr of frames) {
    await page.evaluate((f) => { window.setFrame(f); }, fr);
    await page.waitForTimeout(30);
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
    console.log('Preview frames written to render_frames_coil');
    return;
  }

  await encodeTelegramVp9({ root: ROOT, framesDir: FRAMES, total: TOTAL, size: 512, name: 'hyperlinks-space-sticker-coil.webm' });
  await encodeTelegramVp9({ root: ROOT, framesDir: FRAMES, total: TOTAL, size: 100, name: 'hyperlinks-space-emoji-coil.webm' });

  await run(FFMPEG, [
    '-y', '-framerate', '30',
    '-i', join(FRAMES, 'frame_%04d.png'),
    '-vf', 'scale=256:256:flags=lanczos',
    '-loop', '0',
    join(ROOT, 'preview_coil.gif'),
  ]);

  copyFileSync(join(ROOT, 'hyperlinks-space-sticker-coil.webm'), join(VARIANT, 'hyperlinks-space-sticker-coil.webm'));
  copyFileSync(join(ROOT, 'hyperlinks-space-emoji-coil.webm'), join(VARIANT, 'hyperlinks-space-emoji-coil.webm'));
  console.log('Done (coil sticker + emoji)');
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
