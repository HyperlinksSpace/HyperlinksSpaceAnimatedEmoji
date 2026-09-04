/**
 * Telegram video-avatar: sign N + living emerald background.
 * Spec: 800×800 MP4 H.264 yuv420p, no audio, ≤10s, ≤2MB, faststart.
 */
import { chromium } from 'playwright';
import { spawn } from 'child_process';
import { createServer } from 'http';
import { readFileSync, existsSync, mkdirSync, rmSync, writeFileSync, statSync, copyFileSync } from 'fs';
import { extname, join, dirname } from 'path';
import { fileURLToPath } from 'url';

const ROOT = dirname(fileURLToPath(import.meta.url));
const FRAMES = join(ROOT, 'render_frames_sign_avatar');
const VARIANT = join(ROOT, 'variant_sign_avatar');
const TOTAL = Number(process.env.HL_FRAMES || 90);
const SIZE = 800;
const OUT_MP4 = 'hyperlinks-space-avatar-sign.mp4';
const OUT_PREV = 'preview_sign_avatar.gif';
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

async function encodeAvatarMp4() {
  const out = join(ROOT, OUT_MP4);
  if (existsSync(out)) rmSync(out);
  await run(FFMPEG, [
    '-y',
    '-framerate', '30',
    '-start_number', '1',
    '-i', join(FRAMES, 'frame_%04d.png'),
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
  console.log(`${OUT_MP4}: ${kb.toFixed(1)} KB ${bytes <= limit ? 'OK' : 'OVER'} (limit 2048KB, ${SIZE}² H.264)`);
  if (bytes > limit) throw new Error(`${OUT_MP4} exceeds Telegram avatar 2MB limit`);
}

async function encodePreviewGif() {
  const out = join(ROOT, OUT_PREV);
  if (existsSync(out)) rmSync(out);
  await run(FFMPEG, [
    '-y',
    '-framerate', '30',
    '-start_number', '1',
    '-i', join(FRAMES, 'frame_%04d.png'),
    '-frames:v', String(TOTAL),
    '-vf', 'scale=256:256:flags=lanczos',
    '-r', '30',
    out,
  ]);
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
    viewport: { width: SIZE, height: SIZE },
    deviceScaleFactor: 1,
  });

  page.on('console', (msg) => console.log('[page]', msg.text()));
  await page.goto(`http://127.0.0.1:${port}/scene_volumetric3d.html?avatarBg=1&v=${Date.now()}`, {
    waitUntil: 'networkidle',
  });
  await page.waitForFunction(() => window.ready === true, null, { timeout: 90000 });

  console.log(`Capturing sign-avatar ${TOTAL} frames @ ${SIZE}²...`);
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
  /* Bit-exact loop join: last frame is a copy of the frozen first frame. */
  copyFileSync(
    join(FRAMES, 'frame_0001.png'),
    join(FRAMES, `frame_${String(TOTAL).padStart(4, '0')}.png`),
  );

  await browser.close();
  server.close();

  await encodeAvatarMp4();
  await encodePreviewGif();

  copyFileSync(join(ROOT, OUT_MP4), join(VARIANT, OUT_MP4));
  writeFileSync(join(VARIANT, 'README.md'), `# Sign video avatar (Telegram)

Living emerald field behind the green 3D **N** — aurora ribbons, orbiting bokeh, soft circular vignette.

## Spec (Telegram profile video)
- \`${OUT_MP4}\` — **800×800**, H.264, yuv420p, no audio, faststart, 3s loop @ 30fps, ≤2 MB

\`\`\`bash
HL_FRAMES=90 node capture_sign_avatar.mjs
\`\`\`

Set as profile photo → video in Telegram. Circular crop is intentional.
`);
  console.log('Done (sign video avatar)');
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
