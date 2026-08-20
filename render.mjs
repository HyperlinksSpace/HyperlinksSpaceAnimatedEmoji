import { chromium } from 'playwright';
import { mkdir, writeFile, rm } from 'fs/promises';
import { existsSync } from 'fs';
import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath, pathToFileURL } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FFMPEG =
  process.env.FFMPEG ||
  'C:/Users/ASUS/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-9.0-full_build/bin/ffmpeg.exe';

const DURATION = 3;
const FPS = 30;
const TOTAL = DURATION * FPS;

function run(cmd, args) {
  return new Promise((resolve, reject) => {
    const p = spawn(cmd, args, { stdio: 'inherit' });
    p.on('exit', (code) => (code === 0 ? resolve() : reject(new Error(`${cmd} exited ${code}`))));
  });
}

async function renderVariant({ size, outName, photo }) {
  const framesDir = path.join(__dirname, `.frames_${size}`);
  if (existsSync(framesDir)) await rm(framesDir, { recursive: true, force: true });
  await mkdir(framesDir, { recursive: true });

  const browser = await chromium.launch({
    headless: true,
    args: ['--use-gl=angle', '--enable-webgl', '--ignore-gpu-blocklist'],
  });
  const page = await browser.newPage({
    viewport: { width: size, height: size },
    deviceScaleFactor: 1,
  });

  const url =
    pathToFileURL(path.join(__dirname, 'scene.html')).href +
    `?size=${size}&photo=${photo ? '1' : '0'}`;
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.waitForFunction(() => window.__emoji && window.__emoji.ready);
  // Wait for texture if photo mode
  if (photo) {
    await page.waitForTimeout(400);
  }

  for (let i = 0; i < TOTAL; i++) {
    await page.evaluate((frame) => window.__emoji.setFrame(frame), i);
    const buf = await page.locator('canvas').screenshot({ type: 'png', omitBackground: true });
    const name = path.join(framesDir, `frame_${String(i).padStart(4, '0')}.png`);
    await writeFile(name, buf);
    if (i % 15 === 0) console.log(`[${size}] frame ${i}/${TOTAL}`);
  }

  await browser.close();

  const outPath = path.join(__dirname, outName);
  // Telegram VP9 WEBM, no audio, alpha via yuva420p when possible
  // For emoji: 100x100; sticker: 512x512. Target <=256KB.
  const crf = size <= 100 ? '38' : '34';
  const bitrate = size <= 100 ? '120k' : '400k';

  await run(FFMPEG, [
    '-y',
    '-framerate', String(FPS),
    '-i', path.join(framesDir, 'frame_%04d.png'),
    '-c:v', 'libvpx-vp9',
    '-pix_fmt', 'yuva420p',
    '-auto-alt-ref', '0',
    '-b:v', bitrate,
    '-crf', crf,
    '-an',
    '-t', String(DURATION),
    '-r', String(FPS),
    '-row-mt', '1',
    outPath,
  ]);

  await rm(framesDir, { recursive: true, force: true });
  console.log('Wrote', outPath);
  return outPath;
}

async function main() {
  // Photo-based (brand-accurate) + procedural spikes
  await renderVariant({ size: 512, outName: 'hyperlinks-space-sticker.webm', photo: true });
  await renderVariant({ size: 100, outName: 'hyperlinks-space-emoji.webm', photo: true });
  // Also procedural-only sticker for a fully 3D look
  await renderVariant({ size: 512, outName: 'hyperlinks-space-3d-sticker.webm', photo: false });
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
