"""Blender 场景脚本的公共工具（在 blender -b -P 的脚本里 import）。

    import sys; sys.path.insert(0, r'<skill>/scripts'); from blender_kit import *

只放踩过坑之后确定的做法，见 references/stack-map.md 的「Blender」一节。
"""
import json, math
import bpy
from mathutils import Vector


def hex_rgb(h):
    """#RRGGBB → Blender 的线性 RGBA（Principled 的颜色输入要线性值）"""
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [1]


def bsdf_of(m):
    """按类型找 Principled 节点，不要按名字（界面语言不同，名字会变）"""
    return next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')


def mat(name, col, rough, metal=0.0, coat=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = bsdf_of(m)
    b.inputs['Base Color'].default_value = hex_rgb(col); b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal; b.inputs['Coat Weight'].default_value = coat
    return m


def box(name, loc, size, m=None):
    """长方体。只烘焙缩放：transform_apply 默认连位置一起烘焙，原点会跑到世界原点，旋转和刚体碰撞盒都会错"""
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc); o = bpy.context.object
    o.name = name; o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if m: o.data.materials.append(m)
    return o


def look_at(o, target):
    o.rotation_euler = (Vector(target) - o.location).to_track_quat('-Z', 'Y').to_euler()


def area_light(name, loc, energy, col, size=1.0, target=(0, 0, 0)):
    d = bpy.data.lights.new(name, 'AREA'); d.energy = energy; d.color = hex_rgb(col)[:3]; d.size = size
    o = bpy.data.objects.new(name, d); o.location = loc; look_at(o, target)
    bpy.context.scene.collection.objects.link(o); return o


def setup_cycles(sc, samples=32, preview=False, size=(1080, 1920), shutter=0.3):
    """OptiX GPU、自适应采样 + OptiX 降噪。实测 32 采样和 128 采样降噪后肉眼无差。
    颜色管理用 Khronos PBR Neutral：AgX 会把品牌红压成暗红"""
    sc.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'; prefs.get_devices()
    for d in prefs.devices: d.use = d.type == 'OPTIX'
    cy = sc.cycles; cy.device = 'GPU'; cy.use_adaptive_sampling = True; cy.adaptive_threshold = 0.02
    cy.samples = 8 if preview else samples
    cy.use_denoising = True; cy.denoiser = 'OPTIX'
    sc.render.use_persistent_data = True
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = shutter   # 108° 快门：有动感，快速运镜时不至于糊成一片
    sc.render.resolution_x, sc.render.resolution_y = size
    sc.render.resolution_percentage = 50 if preview else 100
    sc.view_settings.view_transform = 'Khronos PBR Neutral'
    sc.render.image_settings.file_format = 'PNG'


def export_vp(cam, n_frames, path, size=(1080, 1920)):
    """每帧的“世界坐标 → 屏幕像素”投影矩阵（4x4 行优先），给 HTML 叠加层把标注贴到 3D 物体旁边。
    JS 里：clip = M·[x,y,z,1]，屏幕 x = (clip.x/clip.w + 1)/2·W，y = (1 − clip.y/clip.w)/2·H"""
    sc = bpy.context.scene; dg = bpy.context.evaluated_depsgraph_get(); mats = []
    for fr in range(n_frames):
        sc.frame_set(fr)
        P = cam.calc_matrix_camera(dg, x=size[0], y=size[1]) @ cam.matrix_world.inverted()
        mats.append([round(P[i][j], 6) for i in range(4) for j in range(4)])
    json.dump({'fps': sc.render.fps, 'vp': mats}, open(path, 'w'))
    return len(mats)
