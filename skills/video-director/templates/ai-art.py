# AI 静帧批量生成模板（Atlas Cloud · GPT Image 2.5 Flare）。复制到 <project>/gen/art.py 后改 CHAR / PALETTE / SHOTS。
# 来源：夏の残響 OP（F:\aiwork\natsu-op\gen\art.py），提示词写法见 references/stack-map.md「AI 生图 + AI 音乐」。
# 用法：python gen/art.py 06            # 出 06 号
#       python gen/art.py 01 02 03       # 多张并行
#       python gen/art.py plate 07 09    # 给有人物的图出背景板（/edit 去掉人物），人物层用 scripts/cutout.py 本地抠
# 有人物的镜头走 /edit 并带角色锚点图；无人物的走 text-to-image。
# 依赖：atlas-cloud-image skill 的 ~/atlas-tools/gen.py 和 ~/.atlas/key。调用前先向用户报张数和费用。
import os, sys, base64, threading
sys.path.insert(0, os.path.expanduser('~/atlas-tools'))
from gen import gen

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, 'art')
os.makedirs(ART, exist_ok=True)
T2I = 'openai/gpt-image-2.5-flare/text-to-image'
EDIT = 'openai/gpt-image-2.5-flare/edit'
# 竖屏一律 1088x2560 + xhigh：high 档会被缩到约 820 宽，不按 size 出图
BASE = {'size': '1088x2560', 'quality': 'xhigh', 'output_format': 'png'}

# 角色锚点：先单独出一张正面 3/4 胸像，用户确认后，所有带人物的镜头都以它为参考
ANCHOR = os.path.join(ART, 'anchor.png')

# 角色固定特征：每条提示词原样重复
CHAR = "<年龄、发型发色、发饰、瞳色、服装及颜色，一句话写全>"

STYLE = ("STYLE: Modern Japanese TV anime production still. Clean, crisp lineart with consistent thin "
         "line weight; flat cel shading with two to three tonal steps per color area; smooth vector-clean "
         "gradients in the sky; soft bloom only on light sources. Matte, clean skin.")

# 偏黄、偏褐靠写明色板压住，比只写 "no yellow" 稳
PALETTE = "Neutral white balance; whites and highlights stay clean white, never yellow. Palette: <3–5 个具名颜色 + 色值>."

FINISH = ("FINISH: Clean, polished, even digital finish. Solid uniform color fills, smooth gradients, "
          "sharp edges, high clarity. Simple readable shapes with only the necessary detail.")

# 负面提示词：没有 negative 参数，用一段 AVOID 句子。保持一段，不要无限加长
AVOID = ("AVOID: grain, noise, speckle, dithering, film grain, dirty or gritty texture, paper texture, "
         "dust, smudges, muddy or banded gradients, over-detailed grime, JPEG artifacts, halos, fringing, "
         "sepia or yellow color cast, vignette, photorealism, 3D render look, plastic skin, extra fingers, "
         "deformed hands, extra limbs, twisted torso, unnatural neck or shoulder angle, text, captions, "
         "kanji, signs with writing, logos, watermarks, signature, UI elements.")

KEEP = ("Image 1 is the character reference. Keep exactly the same character: same face, hairstyle, "
        "accessories, eye color, outfit and proportions, and the same clean cel-shaded art style. Do not "
        "redesign the character. Ignore Image 1's pose, framing and background; create a new image as "
        "described below.")

# 每个镜头：(是否带人物, 第一行 [USE]，之后 SCENE / SUBJECT / COMPOSITION / LIGHTING & COLOR)
# 姿势：正面、3/4、纯侧脸、远景背影、局部特写最稳；扭头回望、背对扭身没有姿势参考图就不要用
SHOTS = {
 'anchor': (False, """[USE] Main character key visual for a Japanese TV anime opening, vertical 9:16 frame. This image will be the character reference for the whole series.
SCENE: <场景>
SUBJECT: """ + CHAR + """ Upper-body portrait, facing the viewer in a gentle three-quarter view, shoulders relaxed, arms down at her sides.
COMPOSITION: Chest-up framing, the face in the upper-middle third.
LIGHTING & COLOR: <具名光源和方向>"""),
 '01': (True, """[USE] <这张图在片子里的用途>, vertical 9:16 frame.
SCENE: <...>
SUBJECT: <有人物时写 "The girl from the reference ..."，并重复 CHAR 的关键特征>
COMPOSITION: <景别、机位、视线落点、前中后景>
LIGHTING & COLOR: <...>"""),
}


def prompt(sid):
    person, body = SHOTS[sid]
    first, rest = body.split('\n', 1)
    return '\n\n'.join(([KEEP] if person else []) + [first, STYLE, rest, PALETTE, FINISH, AVOID])


def data_uri(path):
    return 'data:image/png;base64,' + base64.b64encode(open(path, 'rb').read()).decode()


def make(sid):
    p = prompt(sid)
    out = os.path.join(ART, sid + '.png')
    open(out[:-4] + '.prompt.txt', 'w', encoding='utf-8').write(p)
    if SHOTS[sid][0]:
        return gen(EDIT, p, out, images=[data_uri(ANCHOR)], **BASE)
    return gen(T2I, p, out, **BASE)


PLATE = ("Remove the person completely from this image and fill the area behind them with the background "
         "that would naturally be there, continuing the same scene, lines, lighting and colors. Keep every "
         "other part of the image exactly the same: same composition, same framing, same art style. "
         "No people, no figures, no silhouettes. " + FINISH + "\n\n" + AVOID)


def plate(sid):
    src = os.path.join(ART, sid + '.png')
    return gen(EDIT, PLATE, os.path.join(ART, sid + '_bg.png'), images=[data_uri(src)], **BASE)


def run(name, fn):
    try:
        print(name, '->', fn(), flush=True)
    except Exception as e:
        print(name, 'FAILED', repr(e), flush=True)


if __name__ == '__main__':
    args = sys.argv[1:]
    fn = make
    if args and args[0] == 'plate':
        fn, args = plate, args[1:]
    ts = [threading.Thread(target=run, args=(s, lambda s=s: fn(s))) for s in args]
    for t in ts: t.start()
    for t in ts: t.join()
