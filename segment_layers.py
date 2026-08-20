"""
Disjoint layer partition of the logo so stacked 3D cards reconstruct the original 1:1.
Priority (front-most claim wins): text > N > sphere > swoop > red tube > black tube > spikes > rest
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(r"c:\1\1\1\1\1\HyperlinksSpaceAnimatedEmoji")
SRC = next(ROOT.glob("ChatGPT Image*.png"))
OUT = ROOT / "layers"
OUT.mkdir(exist_ok=True)


def main():
    img = Image.open(SRC).convert("RGBA")
    arr = np.array(img).astype(np.float32)
    rgb = arr[:, :, :3]
    luma = 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]
    alpha = np.clip((luma - 6.0) / 22.0, 0.0, 1.0)
    arr[:, :, 3] = alpha * 255.0

    H, W = alpha.shape
    yy, xx = np.mgrid[0:H, 0:W]
    cx, cy = W * 0.5, H * 0.42
    rr = np.sqrt(((xx - cx) / W) ** 2 + ((yy - cy) / H) ** 2)

    bgr = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2BGR)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    vis = alpha > 0.08

    # Candidates
    text_zone = (yy > H * 0.40) & (yy < H * 0.90) & (np.abs(xx - cx) / W < 0.45)
    white = vis & (luma > 155) & (s < 75) & text_zone
    text_core = cv2.dilate(white.astype(np.uint8), np.ones((9, 9), np.uint8), 1) > 0
    text_black = (
        vis & text_zone & (luma < 60) & (s < 90)
        & (cv2.dilate(white.astype(np.uint8), np.ones((23, 23), np.uint8), 1) > 0)
    )
    text = text_core | text_black

    n_zone = (yy < H * 0.50) & (np.abs(xx - cx) / W < 0.30) & (rr < 0.40)
    green_n = vis & n_zone & (g > 110) & (g > r * 1.1) & (g > b * 1.05) & (s > 35)
    n_black = (
        vis & n_zone & (luma < 55)
        & (cv2.dilate(green_n.astype(np.uint8), np.ones((27, 27), np.uint8), 1) > 0)
    )
    letter_n = green_n | n_black

    red = vis & (r > 135) & (r > g * 1.3) & (r > b * 1.15) & (s > 70)
    sphere = red & (xx > W * 0.58) & (yy > H * 0.34) & (yy < H * 0.60) & (rr < 0.52)
    # Keep sphere compact
    sphere = cv2.morphologyEx(sphere.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)) > 0
    red_tube = red & (xx < W * 0.50) & ~sphere

    swoop = (
        vis & (g > 120) & (g > r * 1.08) & (g > b * 1.02) & (s > 50)
        & (xx > W * 0.55) & (yy > H * 0.28) & (yy < H * 0.70) & ~n_zone
    )

    black_tube = (
        vis & (luma < 45) & (xx > W * 0.52) & (yy < H * 0.48) & ~n_zone & ~text_zone
    )

    yellow = (s > 85) & (v > 85) & (h >= 15) & (h <= 45)
    magenta = (s > 85) & (v > 85) & (((h >= 140) & (h <= 179)) | (h <= 8))
    cyan = (s > 85) & (v > 85) & (h >= 78) & (h <= 110)
    lime = (s > 85) & (v > 85) & (h >= 40) & (h <= 75) & (g > 130)
    spikes = vis & (yellow | magenta | cyan | lime)

    # Disjoint assignment by priority
    claimed = np.zeros((H, W), dtype=bool)
    layers_defs = [
        ("06_text", text),
        ("05_letter_n", letter_n),
        ("04_red_sphere", sphere),
        ("03_green_swoop", swoop),
        ("01_red_squiggle", red_tube),
        ("02_black_squiggle", black_tube),
        ("00_spikes", spikes),
    ]

    metas = []
    assigned = {}
    for name, cand in layers_defs:
        mask = cand & vis & ~claimed
        claimed |= mask
        assigned[name] = mask

    rest = vis & ~claimed
    assigned["08_rest"] = rest

    def save(name: str, mask: np.ndarray, feather=True):
        out = arr.copy()
        m = mask.astype(np.float32)
        if feather:
            m8 = (m * 255).astype(np.uint8)
            m8 = cv2.GaussianBlur(m8, (0, 0), 0.8)
            # Keep hard core
            m = np.maximum(m, m8.astype(np.float32) / 255.0 * 0.35)
            m = np.clip(m, 0, 1)
            m = np.where(mask, 1.0, m)  # no holes inside
            m = mask.astype(np.float32)  # crisp partition for perfect rebuild
        out[:, :, 3] = out[:, :, 3] * m
        ys, xs = np.where(out[:, :, 3] > 4)
        if len(xs) == 0:
            Image.fromarray(out.astype(np.uint8)).save(OUT / f"{name}.png")
            return {"name": name, "bbox_norm": None, "file": f"{name}.png"}
        pad = 6
        y0, y1 = max(0, ys.min() - pad), min(H, ys.max() + pad + 1)
        x0, x1 = max(0, xs.min() - pad), min(W, xs.max() + pad + 1)
        Image.fromarray(out[y0:y1, x0:x1].astype(np.uint8)).save(OUT / f"{name}.png")
        meta = {
            "name": name,
            "file": f"{name}.png",
            "bbox_norm": [x0 / W, y0 / H, x1 / W, y1 / H],
            "z_hint": name,
        }
        print(f"{name}: {int(mask.sum())} px")
        return meta

    metas = [save(n, assigned[n]) for n, _ in layers_defs]
    metas.append(save("08_rest", assigned["08_rest"]))

    # Full hero square
    ys, xs = np.where(vis)
    y0, y1 = ys.min(), ys.max() + 1
    x0, x1 = xs.min(), xs.max() + 1
    crop = arr[y0:y1, x0:x1]
    side = int(max(crop.shape[0], crop.shape[1]) * 1.02)
    square = np.zeros((side, side, 4), dtype=np.float32)
    oy, ox = (side - crop.shape[0]) // 2, (side - crop.shape[1]) // 2
    square[oy : oy + crop.shape[0], ox : ox + crop.shape[1]] = crop
    Image.fromarray(square.astype(np.uint8)).save(OUT / "hero_square.png")

    # Composite check: rebuild from layers into full canvas
    rebuild = np.zeros_like(arr)
    for name, mask in assigned.items():
        rebuild[mask] = arr[mask]
    Image.fromarray(rebuild.astype(np.uint8)).save(OUT / "rebuild_check.png")

    with open(OUT / "meta.json", "w", encoding="utf-8") as f:
        json.dump({"layers": metas, "src_size": [W, H]}, f, indent=2)
    print("OK", OUT)


if __name__ == "__main__":
    main()
