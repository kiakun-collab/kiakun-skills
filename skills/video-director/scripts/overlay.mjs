// 把遵守渲染契约的页面逐帧渲染成透明 PNG（<out>/####.png，帧号 = 秒 × fps），
// 用来叠在 Blender 等外部渲染器的画面上。页面要把 html/body 背景设为 transparent。
// 用法（在项目文件夹里运行，Playwright 从当前文件夹加载）：
//   node overlay.mjs src/overlay.html [--out overlay] [--frames 36,225,564]
import { createRequire } from 'module';
import { mkdirSync } from 'fs';
import { join, resolve } from 'path';
import { pathToFileURL } from 'url';
const { chromium } = createRequire(join(process.cwd(), 'package.json'))('playwright');

const args = process.argv.slice(2), opt = (k, d) => { const i = args.indexOf(`--${k}`); return i >= 0 ? args[i + 1] : d; };
const page_ = args[0];
if (!page_ || page_.startsWith('--')) { console.error('usage: node overlay.mjs page.html [--out dir] [--frames a,b,c] [--size 1080x1920]'); process.exit(1); }
const [W, H] = opt('size', '1080x1920').split('x').map(Number);
const OUT = resolve(opt('out', 'overlay')); mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
page.on('pageerror', e => console.error('[page error]', e.message));
await page.goto(pathToFileURL(resolve(page_)).href, { waitUntil: 'networkidle' });
await page.waitForFunction(() => typeof window.__renderFrame === 'function');
const total = await page.evaluate(() => Math.round(window.__duration * window.__fps));
const frames = opt('frames') ? opt('frames').split(',').map(Number) : [...Array(total).keys()];
for (const f of frames) {
  await page.evaluate(f => window.__renderFrame(f / window.__fps), f);
  await page.screenshot({ path: join(OUT, `${String(f).padStart(4, '0')}.png`), omitBackground: true });
}
await browser.close();
console.log(`overlay frames: ${frames.length}`);
