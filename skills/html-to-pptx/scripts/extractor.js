// html-to-pptx · DOM 几何/样式提取器（page.evaluate 注入，单文件）。
// 返回 { elements: [...] }，坐标全为 CSS px。见 references/pipeline-contracts.md。
// 注入方式：page.evaluate(EXTRACTOR_JS, {clipTop, clipHeight}) —— clip 用于 fixed 分页逐屏切。
(function extract(opts) {
  opts = opts || {};
  var clipTop = opts.clipTop || 0;
  var clipHeight = opts.clipHeight || window.innerHeight;
  var clipBottom = clipTop + clipHeight;

  var BLOCKISH = { block: 1, flex: 1, grid: 1, table: 1, "list-item": 1, "flow-root": 1, "inline-block": 0 };

  function toHex(color) {
    // color: "rgb(a,b,c)" / "rgba(a,b,c,d)" → #RRGGBBAA
    if (!color || color === "transparent") return "#00000000";
    if (color[0] === "#") return color; // already hex (rare from computed style)
    var m = color.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    var parts = m[1].split(",").map(function (s) { return s.trim(); });
    var r = parseInt(parts[0], 10), g = parseInt(parts[1], 10), b = parseInt(parts[2], 10);
    var a = parts.length > 3 ? parseFloat(parts[3]) : 1;
    function h(n) { return ("0" + n.toString(16)).slice(-2); }
    return "#" + h(r) + h(g) + h(b) + h(Math.round(a * 255));
  }

  function domPath(el) {
    var parts = [];
    while (el && el.nodeType === 1 && el.tagName.toLowerCase() !== "html") {
      var tag = el.tagName.toLowerCase();
      var idx = 1, sib = el;
      while ((sib = sib.previousElementSibling)) {
        if (sib.tagName.toLowerCase() === tag) idx++;
      }
      parts.unshift(tag + ":nth-of-type(" + idx + ")");
      el = el.parentElement;
    }
    parts.unshift("html");
    return parts.join(">");
  }

  function selectorPath(el) {
    return domPath(el).split(">").join(" > ");
  }

  function parseStops(raw) {
    // 从 "linear-gradient(90deg, #fff 0%, #000 100%)" 抽 stops + angle
    var out = { stops: [], angle: null };
    var inner = raw.substring(raw.indexOf("(") + 1, raw.lastIndexOf(")"));
    // 分割顶层逗号（忽略括号内）
    var parts = [], depth = 0, cur = "";
    for (var i = 0; i < inner.length; i++) {
      var c = inner[i];
      if (c === "(") depth++;
      if (c === ")") depth--;
      if (c === "," && depth === 0) { parts.push(cur); cur = ""; } else cur += c;
    }
    if (cur) parts.push(cur);
    parts.forEach(function (p, i) {
      p = p.trim();
      var deg = p.match(/^(-?[\d.]+)deg$/);
      if (deg && i === 0) { out.angle = parseFloat(deg[1]); return; }
      if (/^to\b/.test(p) && i === 0) { out.angle = 180; return; } // 粗略
      var cm = p.match(/(#[0-9a-fA-F]+|rgba?\([^)]+\))\s*([\d.]+%)?/);
      if (cm) {
        var offset = cm[2] ? parseFloat(cm[2]) / 100 : null;
        out.stops.push({ color: toHex(cm[1].indexOf("#") === 0 ? cm[1] : cm[1]) || cm[1], offset: offset });
      }
    });
    // 补齐缺失 offset（均匀分布）
    var n = out.stops.length;
    out.stops.forEach(function (s, i) { if (s.offset === null) s.offset = n > 1 ? i / (n - 1) : 0; });
    return out;
  }

  function background(cs) {
    var img = cs.backgroundImage;
    var bg = { raw: img && img !== "none" ? img : cs.backgroundColor, type: "none" };
    if (img && img.indexOf("linear-gradient") === 0) {
      bg.type = "linear-gradient"; var g = parseStops(img); bg.stops = g.stops; bg.angle = g.angle == null ? 180 : g.angle;
    } else if (img && img.indexOf("radial-gradient") === 0) {
      bg.type = "radial-gradient"; var r = parseStops(img); bg.stops = r.stops;
    } else if (img && img.indexOf("url(") === 0) {
      bg.type = "image"; bg.imageUrl = img.substring(4, img.length - 1).replace(/['"]/g, "");
    } else {
      var col = toHex(cs.backgroundColor);
      if (col && col !== "#00000000") { bg.type = "color"; bg.color = col; }
    }
    return bg;
  }

  function border(cs) {
    function side(w, c, s) { return { width: parseFloat(w) || 0, color: toHex(c) || "#00000000", style: s }; }
    return {
      top: side(cs.borderTopWidth, cs.borderTopColor, cs.borderTopStyle),
      right: side(cs.borderRightWidth, cs.borderRightColor, cs.borderRightStyle),
      bottom: side(cs.borderBottomWidth, cs.borderBottomColor, cs.borderBottomStyle),
      left: side(cs.borderLeftWidth, cs.borderLeftColor, cs.borderLeftStyle),
      radius: {
        tl: parseFloat(cs.borderTopLeftRadius) || 0, tr: parseFloat(cs.borderTopRightRadius) || 0,
        br: parseFloat(cs.borderBottomRightRadius) || 0, bl: parseFloat(cs.borderBottomLeftRadius) || 0
      }
    };
  }

  function boxShadow(cs) {
    var s = cs.boxShadow;
    if (!s || s === "none") return [];
    // 单层解析：[inset] offX offY blur spread color（color 可能在前）
    var out = [];
    var layers = s.split(/,(?![^(]*\))/);
    layers.forEach(function (layer) {
      layer = layer.trim();
      var inset = /inset/.test(layer);
      layer = layer.replace("inset", "").trim();
      var colorMatch = layer.match(/(#[0-9a-fA-F]+|rgba?\([^)]+\))/);
      var color = colorMatch ? toHex(colorMatch[1]) : "#00000040";
      var nums = layer.replace(/(#[0-9a-fA-F]+|rgba?\([^)]+\))/, "").trim().split(/\s+/).map(parseFloat);
      out.push({ offsetX: nums[0] || 0, offsetY: nums[1] || 0, blur: nums[2] || 0, spread: nums[3] || 0, color: color, inset: inset });
    });
    return out;
  }

  function decomposeTransform(cs, el) {
    var t = cs.transform;
    if (!t || t === "none") return null;
    var m = t.match(/matrix\(([^)]+)\)/);
    if (!m) return null;
    var v = m[1].split(",").map(parseFloat);
    var a = v[0], b = v[1], c = v[2], d = v[3], e = v[4], f = v[5];
    var rot = Math.atan2(b, a) * 180 / Math.PI;
    var scaleX = Math.sqrt(a * a + b * b), scaleY = Math.sqrt(c * c + d * d);
    if (Math.abs(rot) < 0.01 && Math.abs(scaleX - 1) < 0.001 && Math.abs(scaleY - 1) < 0.001 && Math.abs(e) < 0.01 && Math.abs(f) < 0.01) return null;
    return { matrix: [a, b, c, d, e, f], rot: rot, scaleX: scaleX, scaleY: scaleY, translateX: e, translateY: f };
  }

  function rasterizeFlags(cs, el) {
    var reasons = [];
    if (cs.backdropFilter && cs.backdropFilter !== "none") reasons.push("backdrop-filter");
    if (cs.filter && cs.filter !== "none") reasons.push("filter");
    if (cs.clipPath && cs.clipPath !== "none") reasons.push("clip-path");
    if ((cs.webkitMaskImage && cs.webkitMaskImage !== "none") || (cs.maskImage && cs.maskImage !== "none")) reasons.push("mask");
    if (cs.mixBlendMode && cs.mixBlendMode !== "normal") reasons.push("mix-blend-mode");
    var tag = el.tagName.toLowerCase();
    if (tag === "canvas") reasons.push("canvas");
    if (tag === "video") reasons.push("video");
    if (tag === "svg") {
      var paths = el.querySelectorAll("path").length;
      if (el.querySelector("filter,mask,use,image") || paths > 12) reasons.push("complex-svg");
    }
    return { required: reasons.length > 0, reasons: reasons };
  }

  function hasBlockChild(el) {
    for (var i = 0; i < el.children.length; i++) {
      var d = getComputedStyle(el.children[i]).display;
      if (BLOCKISH[d] === 1) return true;
    }
    return false;
  }

  function directText(el) {
    var s = "";
    for (var i = 0; i < el.childNodes.length; i++) {
      var n = el.childNodes[i];
      if (n.nodeType === 3) s += n.nodeValue;
    }
    return s;
  }

  function collectRuns(el) {
    // 走 text node，run 样式取最近祖先 computed
    var runs = [];
    var walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null);
    var node;
    while ((node = walker.nextNode())) {
      var txt = node.nodeValue;
      if (!txt || !txt.trim()) continue;
      var p = node.parentElement;
      var cs = getComputedStyle(p);
      runs.push({
        text: txt,
        bold: parseInt(cs.fontWeight, 10) >= 600,
        italic: cs.fontStyle === "italic",
        color: toHex(cs.color) || "#000000FF",
        sizePx: parseFloat(cs.fontSize),
        family: cs.fontFamily,
        weight: parseInt(cs.fontWeight, 10) || 400,
        style: cs.fontStyle
      });
    }
    return runs;
  }

  function lineRects(el) {
    var range = document.createRange();
    range.selectNodeContents(el);
    var rects = range.getClientRects();
    // 按 y 聚类为行
    var lines = [];
    for (var i = 0; i < rects.length; i++) {
      var r = rects[i];
      if (r.width < 0.5 || r.height < 0.5) continue;
      var placed = false;
      for (var j = 0; j < lines.length; j++) {
        if (Math.abs((lines[j].y + lines[j].h / 2) - (r.top + r.height / 2)) <= r.height * 0.6) {
          var L = lines[j];
          var right = Math.max(L.x + L.w, r.right), bottom = Math.max(L.y + L.h, r.bottom);
          L.x = Math.min(L.x, r.left); L.y = Math.min(L.y, r.top);
          L.w = right - L.x; L.h = bottom - L.y; placed = true; break;
        }
      }
      if (!placed) lines.push({ x: r.left, y: r.top, w: r.width, h: r.height, text: "" });
    }
    lines.sort(function (a, b) { return a.y - b.y; });
    return lines;
  }

  var elements = [];
  var paintIndex = 0;
  var all = document.querySelectorAll("*");
  for (var i = 0; i < all.length; i++) {
    var el = all[i];
    var tag = el.tagName.toLowerCase();
    if (tag === "script" || tag === "style" || tag === "head" || tag === "meta" || tag === "link" || tag === "title") continue;
    var cs = getComputedStyle(el);
    if (cs.display === "none" || cs.visibility === "hidden" || parseFloat(cs.opacity) === 0) continue;
    var rect = el.getBoundingClientRect();
    if (rect.width < 0.5 || rect.height < 0.5) continue;
    // clip：fixed 分页——只要与本屏 [clipTop, clipBottom) 相交就收
    if (rect.bottom <= clipTop - 2 || rect.top >= clipBottom + 2) continue;

    var textEl = null;
    var dt = directText(el);
    var hasText = (el.textContent || "").trim().length > 0;
    if (hasText && !hasBlockChild(el)) {
      var runs = collectRuns(el);
      if (runs.length) {
        textEl = {
          content: (el.textContent || "").replace(/\s+/g, " ").trim(),
          lines: lineRects(el),
          runs: runs,
          font: {
            family: cs.fontFamily, sizePx: parseFloat(cs.fontSize), weight: parseInt(cs.fontWeight, 10) || 400,
            style: cs.fontStyle, lineHeightPx: parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.2,
            letterSpacingPx: cs.letterSpacing === "normal" ? 0 : parseFloat(cs.letterSpacing) || 0,
            color: toHex(cs.color) || "#000000FF", align: cs.textAlign, whiteSpace: cs.whiteSpace
          }
        };
      }
    }

    var imageEl = null;
    if (tag === "img") {
      imageEl = { kind: "img", naturalWidth: el.naturalWidth, naturalHeight: el.naturalHeight, currentSrc: el.currentSrc || el.src };
    } else if (tag === "svg") {
      imageEl = { kind: "svg", naturalWidth: rect.width, naturalHeight: rect.height, svg: el.outerHTML };
    } else if (tag === "canvas") {
      var dataUrl = null, tainted = false;
      try { dataUrl = el.toDataURL("image/png"); } catch (e) { tainted = true; }
      imageEl = { kind: "canvas", naturalWidth: el.width, naturalHeight: el.height, dataUrl: dataUrl, tainted: tainted };
    } else {
      var bgImg = cs.backgroundImage;
      if (bgImg && bgImg.indexOf("url(") === 0) {
        imageEl = { kind: "background", naturalWidth: rect.width, naturalHeight: rect.height, currentSrc: bgImg.substring(4, bgImg.length - 1).replace(/['"]/g, "") };
      }
    }

    var transform = decomposeTransform(cs, el);
    var untransformed = null;
    if (transform) {
      // 未变换盒：offsetWidth/Height + 相对最近定位祖先的 offset 近似
      untransformed = { x: el.offsetLeft, y: el.offsetTop, w: el.offsetWidth, h: el.offsetHeight };
    }

    elements.push({
      id: domPath(el),
      tag: tag,
      paintIndex: paintIndex++,
      bbox: { x: rect.left, y: rect.top, w: rect.width, h: rect.height },
      untransformedBox: untransformed,
      transform: transform,
      style: {
        background: background(cs),
        border: border(cs),
        boxShadow: boxShadow(cs),
        opacity: parseFloat(cs.opacity),
        overflow: cs.overflow,
        zIndex: cs.zIndex === "auto" ? "auto" : parseInt(cs.zIndex, 10),
        mixBlendMode: cs.mixBlendMode
      },
      text: textEl,
      image: imageEl,
      rasterize: rasterizeFlags(cs, el),
      selectorPath: selectorPath(el)
    });
  }

  // clip 偏移：把 y 平移到本屏局部坐标（fixed 分页时 clipTop>0）
  if (clipTop) {
    elements.forEach(function (e) {
      e.bbox.y -= clipTop;
      e.text && e.text.lines.forEach(function (l) { l.y -= clipTop; });
    });
  }
  return { elements: elements };
})
