#!/usr/bin/env python3
"""Extract a source-pixel asset using caller-supplied silhouette/background hints."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def integer(value, name, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} must be an integer in [{low}, {high}]")
    return value


def polygon_mask(polygons, roi, name, cv2, np):
    left, top, right, bottom = roi
    result = np.zeros((bottom - top, right - left), np.uint8)
    if not isinstance(polygons, list):
        raise ValueError(f"{name} must be a list of polygons")
    for polygon in polygons:
        if not isinstance(polygon, list) or len(polygon) < 3:
            raise ValueError(f"{name}: a polygon needs at least three points")
        local = []
        for point in polygon:
            if not isinstance(point, list) or len(point) != 2:
                raise ValueError(f"{name}: points must be [x, y]")
            x = integer(point[0], name + '.x', left, right - 1)
            y = integer(point[1], name + '.y', top, bottom - 1)
            local.append([x - left, y - top])
        contour = np.array(local, np.int32)
        if cv2.contourArea(contour) < 1:
            raise ValueError(f"{name}: polygon has no usable area")
        cv2.fillPoly(result, [contour], 1)
    return result.astype(bool)


def refine_edge(rgb, binary, excluded, radius, cv2, np):
    alpha = binary.astype(np.float64)
    color = rgb.astype(np.float64)
    if radius:
        from scipy.ndimage import distance_transform_edt
        kernel = np.ones((2 * radius + 1, 2 * radius + 1), np.uint8)
        inner = cv2.erode(binary.astype(np.uint8), kernel,
                          borderType=cv2.BORDER_CONSTANT, borderValue=0) > 0
        outer = cv2.dilate(binary.astype(np.uint8), kernel) > 0
        # No stable interior/exterior: preserve the hard mask for visual review.
        if inner.any() and (~outer).any():
            fi = distance_transform_edt(~inner, return_distances=False, return_indices=True)
            bi = distance_transform_edt(outer, return_distances=False, return_indices=True)
            fg, bg = color[tuple(fi)], color[tuple(bi)]
            delta = fg - bg
            denominator = (delta ** 2).sum(2)
            reliable = outer & ~inner & (denominator >= 900) & ~excluded
            estimate = np.clip(((color - bg) * delta).sum(2) /
                               np.maximum(denominator, 1), 0, 1)
            alpha[reliable] = estimate[reliable]
            alpha[alpha < .025] = 0
            alpha[alpha > .985] = 1
            edge = reliable & (alpha > 0) & (alpha < 1)
            unmixed = (color - bg * (1 - alpha[:, :, None])) / np.maximum(alpha[:, :, None], .001)
            color[edge] = np.clip(unmixed[edge], 0, 255)
    alpha[excluded] = 0
    color[alpha == 0] = 0
    return np.dstack([np.rint(color).astype(np.uint8), np.rint(alpha * 255).astype(np.uint8)])


def extract(source: Path, hints: dict):
    import cv2
    import numpy as np
    from PIL import Image

    if not isinstance(hints, dict):
        raise ValueError("hints must be an object")
    with Image.open(source) as image:
        rgba = np.array(image.convert('RGBA'))
    height, width = rgba.shape[:2]
    if hints.get('sourceSize') != [width, height]:
        raise ValueError("sourceSize must match the actual source image; use source-pixel coordinates")
    source_alpha = rgba[:, :, 3]
    if not source_alpha.max():
        raise ValueError("Input is fully transparent (EMPTY)")

    if source_alpha.min() < 255:
        # A prior alpha channel is never chroma-keyed or overwritten by segmentation.
        roi = [0, 0, width, height]
        result = Image.fromarray(rgba)
        visible = list(result.getchannel('A').getbbox())
        pad, translation = 0, [0, 0]
        mask_image = result.getchannel('A')
        method = 'ALPHA_REUSED'
        settings = {}
    else:
        roi = hints.get('roi')
        if not isinstance(roi, list) or len(roi) != 4:
            raise ValueError("roi must be [left, top, right, bottom]")
        left = integer(roi[0], 'roi.left', 0, width - 1)
        top = integer(roi[1], 'roi.top', 0, height - 1)
        right = integer(roi[2], 'roi.right', left + 1, width)
        bottom = integer(roi[3], 'roi.bottom', top + 1, height)
        radius = integer(hints.get('uncertaintyRadius', 7), 'uncertaintyRadius', 1, 64)
        edge_radius = integer(hints.get('edgeRadius', 2), 'edgeRadius', 0, 8)
        iterations = integer(hints.get('iterations', 5), 'iterations', 1, 10)
        pad = integer(hints.get('padding', 12), 'padding', 0, 256)
        rgb = rgba[top:bottom, left:right, :3].copy()
        silhouette = polygon_mask(hints.get('foregroundPolygons', []), roi, 'foregroundPolygons', cv2, np)
        background = polygon_mask(hints.get('backgroundPolygons', []), roi, 'backgroundPolygons', cv2, np)
        excluded = background | polygon_mask(hints.get('excludePolygons', []), roi, 'excludePolygons', cv2, np)
        silhouette &= ~excluded
        kernel = np.ones((2 * radius + 1, 2 * radius + 1), np.uint8)
        inner = cv2.erode(silhouette.astype(np.uint8), kernel,
                          borderType=cv2.BORDER_CONSTANT, borderValue=0) > 0
        outer = cv2.dilate(silhouette.astype(np.uint8), kernel) > 0
        labels = np.full(silhouette.shape, cv2.GC_BGD, np.uint8)
        labels[outer] = cv2.GC_PR_BGD
        labels[silhouette] = cv2.GC_PR_FGD
        labels[inner] = cv2.GC_FGD
        labels[excluded] = cv2.GC_BGD
        if not (labels == cv2.GC_FGD).any() or not (labels == cv2.GC_BGD).any():
            raise ValueError("Hints need definite foreground and background seeds; revise the ROI/outline")
        cv2.setRNGSeed(7)
        cv2.grabCut(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), labels, None,
                    np.zeros((1, 65)), np.zeros((1, 65)), iterations, cv2.GC_INIT_WITH_MASK)
        binary = (labels == cv2.GC_FGD) | (labels == cv2.GC_PR_FGD)
        if not binary.any() or binary.all():
            raise ValueError("Segmentation has no usable foreground/background separation")
        pixels = refine_edge(rgb, binary, excluded, edge_radius, cv2, np)
        mask_image = Image.fromarray(pixels[:, :, 3])
        box = mask_image.getbbox()
        if box is None:
            raise ValueError("Segmentation produced an EMPTY asset")
        x0, y0, x1, y1 = box
        visible = [left + x0, top + y0, left + x1, top + y1]
        translation = [left + x0 - pad, top + y0 - pad]
        result = Image.new('RGBA', (x1 - x0 + pad * 2, y1 - y0 + pad * 2), (0, 0, 0, 0))
        result.paste(Image.fromarray(pixels).crop(box), (pad, pad))
        method = 'ASSISTED_GRABCUT'
        settings = {'uncertaintyRadius': radius, 'edgeRadius': edge_radius, 'iterations': iterations,
                    'foregroundPolygonCount': len(hints.get('foregroundPolygons', [])),
                    'backgroundPolygonCount': len(hints.get('backgroundPolygons', [])),
                    'excludePolygonCount': len(hints.get('excludePolygons', []))}

    final_alpha = np.array(result.getchannel('A'))
    components = cv2.connectedComponents((final_alpha > 0).astype(np.uint8), connectivity=8)[0] - 1
    metadata = {'schemaVersion': '1.0', 'generatedBy': 'extract_asset_grabcut.py',
                'method': method, 'visualStatus': 'NOT_REVIEWED', 'sourceSize': [width, height],
                'roi': roi, 'visibleBBoxSource': visible, 'outputSize': list(result.size),
                'padding': pad, 'outputToSource': {'translateX': translation[0], 'translateY': translation[1]},
                'bboxConvention': 'source pixels; LTRB; right/bottom exclusive',
                'alphaMin': int(final_alpha.min()), 'alphaMax': int(final_alpha.max()),
                'partialAlphaPixels': int(np.count_nonzero((final_alpha > 0) & (final_alpha < 255))),
                'componentCount': int(components), 'settings': settings,
                'note': 'Caller-supplied hints; no occlusion completion. Edge RGB may be adjusted. '
                        'Alpha presence does not prove correct separation; inspect the preview and final PPT.'}
    return result, mask_image, metadata


def make_preview(asset):
    from PIL import Image, ImageDraw
    thumb = asset.copy()
    thumb.thumbnail((800, 800))
    panel_width, panel_height = thumb.width + 32, thumb.height + 52
    preview = Image.new('RGB', (panel_width * 2, panel_height))
    for index, (label, background, foreground) in enumerate([
        ('DARK', '#222936', 'white'), ('LIGHT', '#e6edf5', '#172333')
    ]):
        panel = Image.new('RGBA', (panel_width, panel_height), background)
        panel.alpha_composite(thumb, (16, 36))
        ImageDraw.Draw(panel).text((16, 10), label, fill=foreground)
        preview.paste(panel.convert('RGB'), (index * panel_width, 0))
    return preview


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--hints', required=True)
    parser.add_argument('--out-dir', required=True)
    args = parser.parse_args()
    try:
        source, hints_path, output = Path(args.input).resolve(), Path(args.hints).resolve(), Path(args.out_dir).resolve()
        if output.exists():
            raise ValueError("Output directory already exists; choose a new revision directory")
        hints = json.loads(hints_path.read_text(encoding='utf-8-sig'))
        started = time.perf_counter()
        asset, mask, metadata = extract(source, hints)
        metadata['processingMs'] = round((time.perf_counter() - started) * 1000, 1)
        metadata.update({'source': str(source), 'sourceSha256': sha256(source),
                         'hints': str(hints_path), 'hintsSha256': sha256(hints_path)})
        preview = make_preview(asset)
        output.mkdir(parents=True, exist_ok=False)
        asset.save(output / 'asset.png')
        mask.save(output / 'mask.png')
        preview.save(output / 'preview.png')
        metadata['outputSha256'] = sha256(output / 'asset.png')
        (output / 'cutout.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'status': 'READY_FOR_VISUAL_REVIEW', 'method': metadata['method'],
                          'output': str(output / 'asset.png'), 'processingMs': metadata['processingMs']}))
        return 0
    except Exception as exc:
        # OpenCV's native error is not a ValueError; return a machine-readable CLI failure.
        print(json.dumps({'status': 'INVALID', 'error': str(exc)}, ensure_ascii=True))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
