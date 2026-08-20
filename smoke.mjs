import { chromium } from 'playwright';
import { writeFile } from 'fs/promises';
import path from 'path';
import { pathToFileURL } from 'url';

const browser = await chromium.launch({
  headless: true,
  args: ['--use-gl=angle', '--enable-webgl', '--ignore-gpu-blocklist'],
});
const page = await browser.newPage({
  viewport: { width: 512, height: 512 },
  deviceScaleFactor: 1,
});
const url = pathToFileURL(path.resolve('scene.html')).href + '?size=512&photo=1';
console.log('goto', url);
await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
await page.waitForFunction(() => window.__emoji && window.__emoji.ready, { timeout: 30000 });
await page.evaluate((f) => window.__emoji.setFrame(f), 15);
const buf = await page.locator('canvas').screenshot({ type: 'png', omitBackground: true });
await writeFile('preview_frame.png', buf);
console.log('preview bytes', buf.length);
await browser.close();
