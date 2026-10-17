/**
 * Telegram VP9+alpha encode — maximize visual quality under sticker/emoji size caps.
 * Sticker ≤256KB @ 512² · custom emoji ≤64KB @ 100².
 */
import { spawn } from 'child_process';
import { existsSync, rmSync, statSync } from 'fs';
import { join } from 'path';

const DEFAULT_FFMPEG =
  String.raw`C:\Users\ASUS\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-full_build\bin\ffmpeg.exe`;

function run(cmd, args) {
  return new Promise((resolve, reject) => {
    const p = spawn(cmd, args, { stdio: 'inherit' });
    p.on('exit', (code) => (code === 0 ? resolve() : reject(new Error(`ffmpeg exit ${code}`))));
  });
}

/** Quality ladders: try best first, step down only if over Telegram limit. */
function ladderFor(size) {
  if (size <= 100) {
    return [
      { crf: 28, br: '62k' },
      { crf: 32, br: '58k' },
      { crf: 36, br: '54k' },
      { crf: 40, br: '50k' },
      { crf: 44, br: '46k' },
      { crf: 48, br: '42k' },
    ];
  }
  return [
    { crf: 34, br: '240k' },
    { crf: 38, br: '220k' },
    { crf: 42, br: '200k' },
    { crf: 46, br: '180k' },
    { crf: 50, br: '160k' },
    { crf: 54, br: '140k' },
  ];
}

function scaleFilter(size) {
  /* Mild sharpen after downscale — emoji needs more punch at 100². */
  const sharp = size <= 100
    ? ',unsharp=5:5:1.5:5:5:0.55'
    : ',unsharp=3:3:0.55:3:3:0.0';
  return `scale=${size}:${size}:flags=lanczos${sharp},format=yuva420p`;
}

/**
 * @param {object} opts
 * @param {string} opts.root
 * @param {string} opts.framesDir
 * @param {number} opts.total
 * @param {number} opts.size
 * @param {string} opts.name  output filename in root
 * @param {number} [opts.maxBytes]
 * @param {string} [opts.ffmpeg]
 * @param {string} [opts.passLog]
 */
export async function encodeTelegramVp9(opts) {
  const {
    root,
    framesDir,
    total,
    size,
    name,
    maxBytes = size <= 100 ? 64 * 1024 : 256 * 1024,
    ffmpeg = process.env.FFMPEG || DEFAULT_FFMPEG,
    passLog = join(root, `vp9pass-${size}-${name.replace(/\W+/g, '_')}`),
  } = opts;

  const out = join(root, name);
  const ladder = ladderFor(size);
  let lastErr = null;

  for (const { crf, br } of ladder) {
    if (existsSync(out)) rmSync(out);
    const common = [
      '-framerate', '30',
      '-start_number', '1',
      '-i', join(framesDir, 'frame_%04d.png'),
      '-frames:v', String(total),
      '-vf', scaleFilter(size),
      '-c:v', 'libvpx-vp9',
      '-pix_fmt', 'yuva420p',
      '-auto-alt-ref', '0',
      '-metadata:s:v:0', 'alpha_mode=1',
      '-b:v', br,
      '-crf', String(crf),
      '-an',
      '-r', '30',
      '-row-mt', '1',
      '-deadline', 'best',
      /* cpu-used 1: near-max quality, much faster than 0 for 90-frame batches */
      '-cpu-used', '1',
      '-lag-in-frames', '25',
      '-tile-columns', '1',
      '-frame-parallel', '0',
      '-passlogfile', passLog,
    ];
    try {
      await run(ffmpeg, ['-y', ...common, '-pass', '1', '-f', 'null', process.platform === 'win32' ? 'NUL' : '/dev/null']);
      await run(ffmpeg, ['-y', ...common, '-pass', '2', out]);
    } catch (e) {
      lastErr = e;
      continue;
    }
    const bytes = statSync(out).size;
    const kb = bytes / 1024;
    const ok = bytes <= maxBytes;
    console.log(`${name}: ${kb.toFixed(1)} KB ${ok ? 'OK' : 'OVER'} (crf=${crf} br=${br}, limit ${(maxBytes / 1024).toFixed(0)}KB)`);
    if (ok) return { bytes, crf, br };
    lastErr = new Error(`${name} exceeds Telegram limit at crf=${crf}`);
  }
  throw lastErr || new Error(`${name}: could not fit under ${(maxBytes / 1024).toFixed(0)}KB`);
}
