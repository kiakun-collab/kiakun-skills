# 用 rembg（isnet-anime 模型）从整张插画里抠出人物层，和原图像素对齐，供 2.5D 视差用。
# 用法：python tools/cutout.py art/06.png art/07.png ...   → art/06_fg.png ...
# 抠完会在暗底上合成一张检查图 art/_fgcheck_<id>.png，看边缘有没有光晕。
import sys, os
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage
from rembg import remove, new_session

sess = new_session('isnet-anime')
for p in sys.argv[1:]:
    im = Image.open(p).convert('RGB')
    m = remove(im, session=sess, only_mask=True, post_process_mask=True)
    # 只留最大连通区域（去掉粘上的背景光斑），并填满内部的洞（发夹等亮色小物件常被误判成背景）
    soft = np.asarray(m).astype(np.float32) / 255
    lab, n = ndimage.label(soft > 0.5)
    if n > 1:
        sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
        keep = lab == (1 + int(np.argmax(sizes)))
    else:
        keep = lab > 0
    keep = ndimage.binary_fill_holes(keep)
    soft = np.where(keep, np.maximum(soft, ndimage.binary_erosion(keep, iterations=2)), 0)
    m = Image.fromarray((soft * 255).astype(np.uint8))
    # 轻微收边 + 羽化 1px，去掉背景色残边
    m = m.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
    out = im.convert('RGBA'); out.putalpha(m)
    base = os.path.splitext(p)[0]
    out.save(base + '_fg.png')
    a = np.asarray(m) / 255.0
    chk = Image.new('RGB', im.size, (20, 20, 20)); chk.paste(im, mask=m)
    chk.resize((im.width // 2, im.height // 2)).save(os.path.join(os.path.dirname(p), '_fgcheck_' + os.path.basename(base) + '.png'))
    print(p, 'alpha coverage %.1f%%' % (100 * (a > 0.5).mean()))
