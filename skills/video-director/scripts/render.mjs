// Deterministic frame renderer for pages that follow the video-director render contract:
// window.__duration, window.__fps, window.__renderFrame(t).
// Usage:
//   node render.mjs page.html [--size 1080x1920] [--from 0] [--to N] [--out out.mp4] [--audio a.mp3]
//   node render.mjs page.html --at 3.5 --out key.png
//   node render.mjs page.html --sheet 1,4,8,12 --out sheet.png
//   node render.mjs page.html --events 1 --out events.json   (dumps window.__events / __music for sfx.py)
//   add --fast to any mode for a quick preview without expensive effects
import { spawn } from 'node:child_process';
import { createRequire } from 'node:module';
import { mkdtempSync, rmSync, writeFileSync, mkdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve, dirname } from 'node:path';
import { pathToFileURL } from 'node:url';

// Playwright is installed in the user's project, not next to this script.
const { chromium } = createRequire(join(process.cwd(), 'package.json'))('playwright');

const args = process.argv.slice(2);
const page_ = args[0]?.startsWith('--') ? undefined : args[0];
const opt = (k, d) => { const i = args.indexOf(`--${k}`); return i >= 0 ? args[i + 1] : d; };
if (!page_) { console.error('usage: node render.mjs page.html [options]'); process.exit(1); }

const [W, H] = opt('size', '1080x1920').split('x').map(Number);
const out = resolve(opt('out', 'out.mp4'));
mkdirSync(dirname(out), { recursive: true });

function run(cmd, argv) {
  return new Promise((ok, fail) => {
    const p = spawn(cmd, argv, { stdio: ['ignore', 'ignore', 'inherit'] });
    p.on('close', c => (c === 0 ? ok() : fail(new Error(`${cmd} exited ${c}`))));
  });
}

const browser = await chromium.launch({ args: ['--use-gl=angle', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
page.on('pageerror', e => console.error('[page error]', e.message));
// --fast: pages can read window.__preview and skip expensive effects (SVG filters, blur) for quick iteration.
if (args.includes('--fast')) await page.addInitScript(() => { window.__preview = true; });
await page.goto(pathToFileURL(resolve(page_)).href, { waitUntil: 'networkidle' });
await page.waitForFunction(() => typeof window.__renderFrame === 'function');
await page.evaluate(() => document.fonts.ready);
const { duration, fps } = await page.evaluate(() => ({ duration: window.__duration, fps: window.__fps || 30 }));

const shoot = async (t, path) => {
  await page.evaluate(t => window.__renderFrame(t), t);
  await page.screenshot({ path });
};

const tmp = mkdtempSync(join(tmpdir(), 'vd-'));
try {
  if (opt('events')) {
    // Sound-effect cue list the page derives from its own timeline: window.__events = [{t, type, ...}].
    const { events, music } = await page.evaluate(() => ({ events: window.__events || [], music: window.__music || null }));
    writeFileSync(out, JSON.stringify({ duration, music, events }, null, 1));
  } else if (opt('at')) {
    await shoot(Number(opt('at')), out);
  } else if (opt('sheet')) {
    const ts = opt('sheet').split(',').map(Number);
    for (const [i, t] of ts.entries()) {
      await page.evaluate(t => window.__renderFrame(t), t);
      // Stamp the timestamp on top so the sheet can be scored per shot.
      await page.evaluate(t => {
        const d = document.createElement('div');
        d.id = '__vd_stamp'; d.textContent = `${t}s`;
        d.style.cssText = 'position:fixed;left:16px;top:16px;z-index:2147483647;font:bold 48px sans-serif;color:#fff;background:#000a;padding:4px 14px';
        document.body.appendChild(d);
      }, t);
      await page.screenshot({ path: join(tmp, `s${i}.png`) });
      await page.evaluate(() => document.getElementById('__vd_stamp')?.remove());
    }
    const cols = Math.min(ts.length, 3), rows = Math.ceil(ts.length / cols);
    await run('ffmpeg', ['-y', '-loglevel', 'error', '-framerate', '1', '-i', join(tmp, 's%d.png'),
      '-vf', `scale=${Math.round(W / 3)}:-2,tile=${cols}x${rows}:padding=8:color=black`, '-frames:v', '1', out]);
  } else {
    const from = Number(opt('from', 0)), to = Math.min(Number(opt('to', duration)), duration);
    const n = Math.round((to - from) * fps);
    const started = Date.now();
    for (let i = 0; i < n; i++) {
      await shoot(from + i / fps, join(tmp, `f${String(i).padStart(6, '0')}.png`));
      if (i % fps === 0) process.stderr.write(`\r${i}/${n} frames`);
    }
    process.stderr.write(`\r${n}/${n} frames in ${((Date.now() - started) / 1000).toFixed(1)}s\n`);
    const audio = opt('audio');
    await run('ffmpeg', ['-y', '-loglevel', 'error', '-framerate', String(fps), '-i', join(tmp, 'f%06d.png'),
      ...(audio ? ['-ss', String(from), '-i', resolve(audio), '-shortest', '-c:a', 'aac', '-b:a', '192k'] : []),
      '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-movflags', '+faststart', out]);
  }
  console.log(out);
} finally {
  await browser.close();
  rmSync(tmp, { recursive: true, force: true });
}
