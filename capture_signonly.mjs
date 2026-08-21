/**
 * Sign-only variant: letter N centered & enlarged, no HYPERLINKS.SPACE text.
 * Keeps existing main / firebomb / shatter / layered deliverables untouched.
 */
import { chromium } from 'playwright';
import { spawn } from 'child_process';
import { createServer } from 'http';
import { readFileSync, existsSync, mkdirSync, rmSync, writeFileSync, statSync, copyFileSync } from 'fs';
import { extname, join, dirname } from 'path';
import { fileURLToPath } from 'url';

const ROOT = dirname(fileURLToPath(import.meta.url));
const FRAMES = join(ROOT, 'render_frames_sign');
const VARIANT = join(ROOT, 'variant_signonly');
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

function run(cmd, args) {
  return new Promise((resolve, reject) => {
    const p = spawn(cmd, args, { stdio: 'inherit' });
    p.on('exit', (code) => (code === 0 ? resolve() : reject(new Error(`exit ${code}`))));
  });
}

async function encode(size, name, crf, br, maxBytes) {
  const out = join(ROOT, name);
  if (existsSync(out)) rmSync(out);
  const common = [
    '-framerate', '30',
    '-start_number', '1',
    '-i', join(FRAMES, 'frame_%04d.png'),
    '-frames:v', String(TOTAL),
    '-vf', `scale=${size}:${size}:flags=lanczos,format=yuva420p`,
    '-c:v', 'libvpx-vp9', '-pix_fmt', 'yuva420p', '-auto-alt-ref', '0',
    '-metadata:s:v:0', 'alpha_mode=1',
    '-b:v', br, '-crf', String(crf), '-an', '-r', '30', '-row-mt', '1',
    '-deadline', 'good', '-cpu-used', '2',
  ];
  await run(FFMPEG, ['-y', ...common, '-pass', '1', '-f', 'null', process.platform === 'win32' ? 'NUL' : '/dev/null']);
  await run(FFMPEG, ['-y', ...common, '-pass', '2', out]);
  const bytes = statSync(out).size;
  const kb = bytes / 1024;
  const limit = maxBytes ?? 256 * 1024;
  console.log(`${name}: ${kb.toFixed(1)} KB ${bytes <= limit ? 'OK' : 'OVER'} (limit ${(limit / 1024).toFixed(0)}KB)`);
  if (bytes > limit) throw new Error(`${name} exceeds Telegram limit`);
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
  await page.goto(`http://127.0.0.1:${port}/scene_volumetric3d.html?signOnly=1&v=${Date.now()}`, {
    waitUntil: 'networkidle',
  });
  await page.waitForFunction(() => window.ready === true, null, { timeout: 60000 });

  console.log(`Capturing sign-only ${TOTAL} frames...`);
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

  await browser.close();
  server.close();

  await encode(512, 'hyperlinks-space-sticker-sign.webm', 60, '160k', 256 * 1024);
  await encode(100, 'hyperlinks-space-emoji-sign.webm', 58, '45k', 64 * 1024);

  copyFileSync(join(ROOT, 'hyperlinks-space-sticker-sign.webm'), join(VARIANT, 'hyperlinks-space-sticker-sign.webm'));
  copyFileSync(join(ROOT, 'hyperlinks-space-emoji-sign.webm'), join(VARIANT, 'hyperlinks-space-emoji-sign.webm'));
  console.log('Done (sign-only)');
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
