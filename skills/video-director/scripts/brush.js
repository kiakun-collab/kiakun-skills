// 毛笔书写模拟：按 KanjiVG 笔顺把字一笔一笔"写"出来。
// 笔画数据：KanjiVG (http://kanjivg.tagaini.net)，CC BY-SA 3.0。
// 确定性：画面只由 t 决定。噪声用 p5 的 noise（固定 noiseSeed），其余随机数用 hash；
//         写完的笔画缓存在离屏画布里，时间往回跳时整张重建，所以乱序渲染结果也一致。
//
// 用法：
//   const w = makeWriter({ text: '夏の残響', x: 800, y: 470, size: 200, vertical: true, t0: 1.46, dur: 1.5 });
//   w.draw(ctx, t, S)          // S = 画布缩放（预览分辨率用）
(function () {
  const P = new p5(p => { p.setup = () => p.noCanvas(); });
  P.noiseSeed(7);
  const noise = (a, b = 0) => P.noise(a, b);
  const hash = (a, b = 0, c = 0) => {
    let h = Math.imul(a | 0, 374761393) ^ Math.imul(b | 0, 668265263) ^ Math.imul(c | 0, 2246822519);
    h = Math.imul(h ^ (h >>> 13), 1274126177); h ^= h >>> 16; return (h >>> 0) / 4294967296;
  };
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const sstep = (a, b, x) => { const k = clamp((x - a) / (b - a)); return k * k * (3 - 2 * k); };

  // 撇、捺、提、钩这类笔画收笔要出锋（越写越细），其余是"止"（收笔略按再收圆）
  const SWEEP = /[㇒㇏㇀㇓㇚㇙㇟㇂㇁㇃㇇㇋㇉㇈㇌㇊㇄㇅]/;

  // 用 SVG 的 getPointAtLength 把路径采样成点列（KanjiVG 坐标，109×109）
  const svgNS = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(svgNS, 'svg');
  svg.style.cssText = 'position:absolute;width:0;height:0;visibility:hidden';
  document.documentElement.appendChild(svg);
  function sample(d, step = 0.5) {
    const el = document.createElementNS(svgNS, 'path'); el.setAttribute('d', d); svg.appendChild(el);
    const L = el.getTotalLength(), n = Math.max(2, Math.ceil(L / step)), pts = [];
    for (let i = 0; i <= n; i++) { const q = el.getPointAtLength(L * i / n); pts.push([q.x, q.y]); }
    svg.removeChild(el);
    return { pts, L };
  }

  window.makeWriter = function (o) {
    const opt = Object.assign({ size: 200, vertical: true, gap: 1.02, weight: 10.5, bristles: 26, dry: .9, wobble: 1, splash: .5, scales: null, tremble: 0, glow: null,
      ink: [247, 243, 234], seed: 1, lift: .35, boil: 1.2, shadow: true }, o);
    const chars = [...opt.text];
    // 笔画表：每笔带上字的序号、在字内的位置、采样点、长度
    const strokes = [];
    chars.forEach((ch, ci) => {
      const list = (window.STROKES || {})[ch];
      if (!list) throw new Error('KanjiVG 里没有这个字的笔画：' + ch);
      list.forEach((st, si) => { const s = sample(st.d); strokes.push({ ci, si, n: list.length, type: st.type, ...s }); });
    });
    // 时间分配：按笔画长度分，每次提笔加一段停顿（相当于 lift 个平均笔长）
    const avg = strokes.reduce((a, s) => a + s.L, 0) / strokes.length;
    const units = strokes.map(s => s.L + avg * opt.lift);
    const total = units.reduce((a, b) => a + b, 0);
    let acc = 0;
    strokes.forEach((s, i) => { s.t0 = opt.t0 + opt.dur * acc / total; acc += units[i]; s.t1 = opt.t0 + opt.dur * (acc - avg * opt.lift) / total; });
    const tEnd = opt.t0 + opt.dur;

    // 手写排布：每个字的大小、倾斜、错位都略有不同（假名默认小一号）
    const kana = ch => /[぀-ヿ]/.test(ch);
    const lay = chars.map((ch, ci) => ({
      sc: (opt.scales ? opt.scales[ci] : (kana(ch) ? .82 : 1)) * (1 + (hash(opt.seed, ci, 21) - .5) * .12 * opt.wobble),
      rot: (hash(opt.seed, ci, 22) - .5) * .12 * opt.wobble,
      off: (hash(opt.seed, ci, 23) - .5) * .14 * opt.wobble,
      n: ((window.STROKES || {})[ch] || []).length,
    }));
    // 字心位置：竖排按各字大小累加
    const centers = []; { let acc = 0; lay.forEach((l, ci) => {
      const h = opt.size * l.sc * opt.gap; acc += h / 2;
      centers.push(opt.vertical ? [opt.x + l.off * opt.size, opt.y + acc - opt.size / 2] : [opt.x + acc - opt.size / 2, opt.y + l.off * opt.size]);
      acc += h / 2; }); }

    // 一笔画到 u（0..1）：中间实心墨芯 + 两侧笔毛（飞白）+ 起笔顿点 + 收笔出锋或积墨
    function stroke(c, s, u, S, k) {
      const l = lay[s.ci], sc = opt.size * l.sc / 109 * S, [cx, cy] = centers[s.ci].map(v => v * S);
      const cr = Math.cos(l.rot), sr = Math.sin(l.rot);
      const P2 = ([x, y]) => { const u = (x - 54.5) * sc, v = (y - 54.5) * sc; return [cx + u * cr - v * sr, cy + u * sr + v * cr]; };
      const m = Math.max(2, Math.floor(s.pts.length * u));
      let pts = s.pts.slice(0, m);
      if (opt.tremble) pts = pts.map(([x, y], i) => [x + (noise(k * 1.7 + 50, i * .09) - .5) * opt.tremble, y + (noise(k * 1.7 + 80, i * .09) - .5) * opt.tremble]);
      pts = pts.map(P2);
      if (pts.length < 2) return;
      const sweep = SWEEP.test(s.type), Ls = s.L, W = opt.weight * sc * clamp(1.18 - l.n / 45, .7, 1.1);
      const seed = opt.seed * 97 + k * 13;
      // 宽度曲线（按弧长 a，单位 KanjiVG）：起笔重、行笔略细且有起伏、收笔出锋或按住
      const width = a => {
        let w = 1.18 - .22 * sstep(0, 6, a);
        w *= .9 + .2 * noise(seed * .37, a * .06);
        if (sweep) w *= 1 - .92 * sstep(Ls * .55, Ls, a);
        else w *= 1 + .12 * sstep(Ls - 7, Ls - 2, a) - .5 * sstep(Ls - 1.5, Ls, a);
        return Math.max(.04, w) * W;
      };
      const step = Ls / (s.pts.length - 1);
      const nrm = [], wid = [];
      for (let i = 0; i < pts.length; i++) {
        const a = pts[Math.max(0, i - 1)], b = pts[Math.min(pts.length - 1, i + 1)];
        const dx = b[0] - a[0], dy = b[1] - a[1], ll = Math.hypot(dx, dy) || 1;
        const vert = Math.abs(dy / ll);
        nrm.push([-dy / ll, dx / ll]); wid.push(width(i * step) * (.68 + .5 * vert));
      }
      const [r, g, bl] = opt.ink;
      // 墨芯：宽度 76% 的实心带
      c.fillStyle = `rgba(${r},${g},${bl},.96)`;
      c.beginPath();
      for (let i = 0; i < pts.length; i++) c.lineTo(pts[i][0] + nrm[i][0] * wid[i] * .38, pts[i][1] + nrm[i][1] * wid[i] * .38);
      for (let i = pts.length - 1; i >= 0; i--) c.lineTo(pts[i][0] - nrm[i][0] * wid[i] * .38, pts[i][1] - nrm[i][1] * wid[i] * .38);
      c.fill();
      // 笔毛：每根毛的墨量沿笔画递减，墨不够的地方用噪声挖出飞白
      c.lineCap = 'round';
      const N = opt.bristles;
      for (let j = 0; j < N; j++) {
        const off = (j / (N - 1)) * 2 - 1 + (hash(seed, j) - .5) * .08;
        const edge = Math.abs(off);
        const ink0 = 1 - .25 * hash(seed, j, 2), drain = opt.dry * (.35 + .9 * hash(seed, j, 3)) * (.4 + edge);
        c.lineWidth = Math.max(.6, W / N * 2.3);
        let open = false;
        for (let i = 0; i < pts.length; i++) {
          const a = i * step, ink = ink0 - drain * (a / 109) * 1.6;
          const gap = noise(seed + j * 3.17, a * .11) > clamp(ink * .9 + .25 - edge * .25, .1, 1.2);
          const x = pts[i][0] + nrm[i][0] * wid[i] * .5 * off, y = pts[i][1] + nrm[i][1] * wid[i] * .5 * off;
          if (gap || ink <= 0) { if (open) { c.stroke(); open = false; } continue; }
          if (!open) { c.strokeStyle = `rgba(${r},${g},${bl},${clamp(.55 + ink * .45)})`; c.beginPath(); c.moveTo(x, y); open = true; }
          else c.lineTo(x, y);
        }
        if (open) c.stroke();
      }
      // 起笔顿点：沿起笔方向的椭圆
      const [x0, y0] = pts[0], ang = Math.atan2(nrm[0][0], -nrm[0][1]);
      c.fillStyle = `rgba(${r},${g},${bl},.95)`;
      c.beginPath(); c.ellipse(x0, y0, wid[0] * .62, wid[0] * .46, ang + .6, 0, Math.PI * 2); c.fill();
      // 写完的"止"笔在末端积一点墨
      if (u >= 1 && !sweep) { const e = pts[pts.length - 1], we = wid[wid.length - 3] || wid[0];
        c.beginPath(); c.arc(e[0], e[1], we * .42, 0, Math.PI * 2); c.fill(); }
      // 出锋的笔画写完时甩出几滴墨
      if (u >= 1 && sweep && hash(seed, 1, 6) < opt.splash) {
        const e = pts[pts.length - 1], q = pts[Math.max(0, pts.length - 6)];
        const dx = e[0] - q[0], dy = e[1] - q[1], ll = Math.hypot(dx, dy) || 1;
        const nd = 1 + Math.floor(hash(seed, 2, 6) * 3);
        for (let d = 0; d < nd; d++) {
          const dist = (3 + 9 * hash(seed, d, 7)) * sc, rr = (1 + 1.8 * hash(seed, d, 8)) * sc;
          const sp = (hash(seed, d, 9) - .5) * .6;
          c.beginPath(); c.arc(e[0] + (dx / ll + sp * dy / ll) * dist, e[1] + (dy / ll - sp * dx / ll) * dist, rr, 0, Math.PI * 2); c.fill();
        }
      }
    }

    // 写完的笔画缓存
    let cache = null, cached = 0, cacheS = 0;
    function rebuild(n, S, W, H) {
      if (!cache || cache.width !== W || cache.height !== H || cacheS !== S || n < cached) {
        cache = cache && cache.width === W && cache.height === H ? cache : Object.assign(document.createElement('canvas'), { width: W, height: H });
        cache.getContext('2d').clearRect(0, 0, W, H); cached = 0; cacheS = S;
      }
      const c = cache.getContext('2d');
      for (; cached < n; cached++) stroke(c, strokes[cached], 1, S, cached);
    }

    return {
      strokes, tEnd, charStarts: chars.map((_, ci) => strokes.find(s => s.ci === ci).t0),
      // fade：整体透明度；dx/dy：整体位移（像素，1080 基准）
      draw(ctx, t, S = 1, { fade = 1, dx = 0, dy = 0, scale = 1, cx = 540, cy = 960 } = {}) {
        if (t < opt.t0 || fade <= 0) return;
        const W = ctx.canvas.width, H = ctx.canvas.height;
        const done = strokes.filter(s => t >= s.t1).length;
        rebuild(done, S, W, H);
        // 写完后每 2 帧轻微抖一下（手绘颤动）
        const f = Math.floor(t * 15), bo = t > tEnd ? opt.boil * S : 0;
        const jx = (hash(f, opt.seed) - .5) * 2 * bo + dx * S, jy = (hash(f, opt.seed, 5) - .5) * 2 * bo + dy * S;
        const zoom = c => { c.translate(cx * S, cy * S); c.scale(scale, scale); c.translate(-cx * S, -cy * S); };
        ctx.save(); ctx.globalAlpha = fade; zoom(ctx);
        if (opt.glow) { ctx.shadowColor = opt.glow; ctx.shadowBlur = 40 * S; ctx.drawImage(cache, jx, jy); }
        if (opt.shadow) { ctx.shadowColor = 'rgba(4,8,30,.7)'; ctx.shadowBlur = 24 * S; }
        ctx.drawImage(cache, jx, jy);
        ctx.restore();
        // 正在写的那一笔
        const cur = strokes[done];
        if (cur && t >= cur.t0 && t < cur.t1) {
          ctx.save(); ctx.globalAlpha = fade; zoom(ctx); ctx.translate(jx, jy);
          stroke(ctx, cur, sstep(0, 1, (t - cur.t0) / (cur.t1 - cur.t0)), S, done);
          ctx.restore();
        }
      },
    };
  };
})();
