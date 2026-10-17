/**
 * Chat / bot / channel video avatars — full logo (N + HYPERLINKS.SPACE), stainless,
 * dark tinted space, white supernova. Does not replace emerald or profile-metal avatars.
 */
import { chromium } from 'playwright';
import { spawn } from 'child_process';
import { createServer } from 'http';
import { readFileSync, existsSync, mkdirSync, rmSync, writeFileSync, statSync, copyFileSync } from 'fs';
import { extname, join, dirname } from 'path';
import { fileURLToPath } from 'url';

const ROOT = dirname(fileURLToPath(import.meta.url));
const VARIANT = join(ROOT, 'variant_sign_avatar_metal');
const TOTAL = Number(process.env.HL_FRAMES || 90);
const SIZE = 800;
const KINDS = ['chat', 'bot', 'channel'];
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

async function encodeAvatarMp4(frames, outName) {
  const out = join(ROOT, outName);
  if (existsSync(out)) rmSync(out);
  await run(FFMPEG, [
    '-y',
    '-framerate', '30',
    '-start_number', '1',
    '-i', join(frames, 'frame_%04d.png'),
    '-frames:v', String(TOTAL),
    '-vf', `scale=${SIZE}:${SIZE}:flags=lanczos,format=yuv420p`,
    '-c:v', 'libx264',
    '-preset', 'medium',
    '-crf', '18',
    '-pix_fmt', 'yuv420p',
    '-profile:v', 'high',
    '-level', '4.0',
    '-an',
    '-movflags', '+faststart',
    out,
  ]);
  const bytes = statSync(out).size;
  const kb = bytes / 1024;
  const limit = 2 * 1024 * 1024;
  console.log(`${outName}: ${kb.toFixed(1)} KB ${bytes <= limit ? 'OK' : 'OVER'} (limit 2048KB)`);
  if (bytes > limit) throw new Error(`${outName} exceeds Telegram avatar 2MB limit`);
}

async function encodePreviewGif(frames, outName) {
  const out = join(ROOT, outName);
  if (existsSync(out)) rmSync(out);
  await run(FFMPEG, [
    '-y',
    '-framerate', '30',
    '-start_number', '1',
    '-i', join(frames, 'frame_%04d.png'),
    '-frames:v', String(TOTAL),
    '-vf', 'scale=256:256:flags=lanczos',
    '-r', '30',
    out,
  ]);
}

async function captureKind(page, port, kind) {
  const frames = join(ROOT, `render_frames_sign_avatar_metal_${kind}`);
  if (existsSync(frames)) rmSync(frames, { recursive: true, force: true });
  mkdirSync(frames, { recursive: true });

  await page.goto(
    `http://127.0.0.1:${port}/scene_volumetric3d.html?avatarFull=1&avatarKind=${kind}&v=${Date.now()}`,
    { waitUntil: 'networkidle' },
  );
  await page.waitForFunction(() => window.ready === true, null, { timeout: 90000 });

  console.log(`Capturing metal ${kind} avatar ${TOTAL} frames @ ${SIZE}²...`);
  for (let fr = 1; fr <= TOTAL; fr++) {
    await page.evaluate((f) => { window.setFrame(f); }, fr);
    await page.waitForTimeout(20);
    const b64 = await page.evaluate(() => {
      const c = document.querySelector('canvas');
      return c.toDataURL('image/png').split(',')[1];
    });
    writeFileSync(join(frames, `frame_${String(fr).padStart(4, '0')}.png`), Buffer.from(b64, 'base64'));
    if (fr % 15 === 0) console.log(`  ${kind} frame ${fr}/${TOTAL}`);
  }
  copyFileSync(
    join(frames, 'frame_0001.png'),
    join(frames, `frame_${String(TOTAL).padStart(4, '0')}.png`),
  );
  return frames;
}

async function main() {
  mkdirSync(VARIANT, { recursive: true });
  const { server, port } = await serve();
  const browser = await chromium.launch({
    headless: true,
    args: ['--use-angle=d3d11', '--ignore-gpu-blocklist'],
  });
  const page = await browser.newPage({
    viewport: { width: SIZE, height: SIZE },
    deviceScaleFactor: 1,
  });
  page.on('console', (msg) => console.log('[page]', msg.text()));

  for (const kind of KINDS) {
    const frames = await captureKind(page, port, kind);
    const mp4 = `hyperlinks-space-avatar-sign-metal-${kind}.mp4`;
    const gif = `preview_sign_avatar_metal_${kind}.gif`;
    await encodeAvatarMp4(frames, mp4);
    await encodePreviewGif(frames, gif);
    copyFileSync(join(ROOT, mp4), join(VARIANT, mp4));
  }

  await browser.close();
  server.close();
  console.log('Done (metal chat / bot / channel avatars)');
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
