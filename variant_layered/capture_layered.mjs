/**
 * Capture true-3D Three.js scene frames via Playwright, then encode WEBM.
 */
import { chromium } from 'playwright';
import { spawn } from 'child_process';
import { createServer } from 'http';
import { readFileSync, existsSync, mkdirSync, rmSync, writeFileSync, statSync } from 'fs';
import { extname, join, dirname } from 'path';
import { fileURLToPath } from 'url';

const ROOT = dirname(fileURLToPath(import.meta.url));
const FRAMES = join(ROOT, 'render_frames');
const TOTAL = Number(process.env.HL_FRAMES || 90);
const FFMPEG = process.env.FFMPEG ||
  String.raw`C:\Users\ASUS\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin\ffmpeg.exe`;

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
      if (url === '/') url = '/scene_true3d.html';
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

async function encode(size, name, crf, br) {
  const out = join(ROOT, name);
  if (existsSync(out)) rmSync(out);
  const frames = [...Array(TOTAL)].map((_, i) =>
    join(FRAMES, `frame_${String(i + 1).padStart(4, '0')}.png`));
  for (const f of frames) {
    if (!existsSync(f)) throw new Error(`Missing frame ${f}`);
  }
  await run(FFMPEG, [
    '-y', '-framerate', '30',
    '-start_number', '1',
    '-i', join(FRAMES, 'frame_%04d.png'),
    '-frames:v', String(TOTAL),
    '-vf', `scale=${size}:${size}:flags=lanczos`,
    '-c:v', 'libvpx-vp9', '-pix_fmt', 'yuva420p', '-auto-alt-ref', '0',
    '-b:v', br, '-crf', String(crf), '-an', '-r', '30', '-row-mt', '1',
    out,
  ]);
  const kb = statSync(out).size / 1024;
  console.log(`${name}: ${kb.toFixed(1)} KB ${statSync(out).size <= 256 * 1024 ? 'OK' : 'OVER'}`);
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
  await page.goto(`http://127.0.0.1:${port}/scene_true3d.html?v=${Date.now()}`, {
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

  await encode(512, 'hyperlinks-space-sticker.webm', 54, '100k');
  await encode(100, 'hyperlinks-space-emoji.webm', 42, '75k');
  console.log('Done');
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
