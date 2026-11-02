# 把 KanjiVG 的 SVG 转成页面能直接用的笔画表：window.STROKES = {字: [{d, type}, ...]}（按笔顺）
# 用法：python tools/kanjivg.py strokes/svg strokes/strokes.js
# 笔画数据：KanjiVG (http://kanjivg.tagaini.net)，CC BY-SA 3.0，成片需署名
import sys, os, re, json
src, out = sys.argv[1], sys.argv[2]
res = {}
for f in sorted(os.listdir(src)):
    if not f.endswith('.svg'): continue
    ch = chr(int(f[:-4].split('-')[0], 16))
    s = open(os.path.join(src, f), encoding='utf-8').read()
    paths = re.findall(r'<path[^>]*?id="kvg:[0-9a-f]+-s(\d+)"[^>]*?/>', s)
    strokes = []
    for m in re.finditer(r'<path([^>]*)/>', s):
        attrs = m.group(1)
        i = re.search(r'id="kvg:[0-9a-f-]+-s(\d+)"', attrs)
        d = re.search(r'\bd="([^"]+)"', attrs)
        ty = re.search(r'kvg:type="([^"]*)"', attrs)
        if i and d:
            strokes.append((int(i.group(1)), {'d': d.group(1), 'type': ty.group(1) if ty else ''}))
    res[ch] = [x for _, x in sorted(strokes, key=lambda z: z[0])]
    print(ch, len(res[ch]), 'strokes')
open(out, 'w', encoding='utf-8').write('// KanjiVG (http://kanjivg.tagaini.net), CC BY-SA 3.0\nwindow.STROKES = ' +
                                       json.dumps(res, ensure_ascii=False) + ';\n')
