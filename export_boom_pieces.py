"""
Export Hyperlinks.SPACE logo as true 3D piece textures for Blender.
- Green flank elements (L/R of the N) stay static — not exploded
- Disjoint pieces rebuild the logo (no duplicate overlay)
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(r"c:\1\1\1\1\1\HyperlinksSpaceAnimatedEmoji")
SRC = next(ROOT.glob("ChatGPT Image*.png"))
OUT = ROOT / "boom_3d_pieces"
SIZE = 512


def matte_square() -> np.ndarray:
    arr = np.array(Image.open(SRC).convert("RGBA")).astype(np.float32)
    rgb = arr[:, :, :3]
    luma = 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]
    arr[:, :, 3] = np.clip((luma - 4.0) / 18.0, 0, 1) * 255
    a = arr[:, :, 3] / 255.0
    ys, xs = np.where(a > 0.05)
    crop = arr[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]
    side = max(crop.shape[0], crop.shape[1])
    sq = np.zeros((side, side, 4), np.float32)
    oy, ox = (side - crop.shape[0]) // 2, (side - crop.shape[1]) // 2
    sq[oy : oy + crop.shape[0], ox : ox + crop.shape[1]] = crop
    return sq


def main():
    OUT.mkdir(exist_ok=True)
    for p in OUT.glob("*.png"):
        p.unlink()

    base0 = matte_square()
    base = np.array(
        Image.fromarray(base0.astype(np.uint8)).resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    ).astype(np.float32)
    H = W = SIZE
    rgb = base[:, :, :3]
    a = base[:, :, 3] / 255.0
    vis = a > 0.08

    bgr = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2BGR)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    r, g, bch = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    luma = 0.2126 * r + 0.7152 * g + 0.0722 * bch
    yy, xx = np.mgrid[0:H, 0:W]
    ocx, ocy = W * 0.5, H * 0.42
    rr = np.sqrt(((xx - ocx) / W) ** 2 + ((yy - ocy) / H) ** 2)

    text_zone = (yy > H * 0.40) & (yy < H * 0.90) & (np.abs(xx - ocx) / W < 0.45)
    white = vis & (luma > 155) & (s < 75) & text_zone
    text = (cv2.dilate(white.astype(np.uint8), np.ones((9, 9), np.uint8), 1) > 0) | (
        vis & text_zone & (luma < 60) & (s < 90)
        & (cv2.dilate(white.astype(np.uint8), np.ones((23, 23), np.uint8), 1) > 0)
    )

    n_zone = (yy < H * 0.52) & (np.abs(xx - ocx) / W < 0.28) & (rr < 0.38)
    green_n = vis & n_zone & (g > 110) & (g > r * 1.1) & (g > bch * 1.05) & (s > 35)
    letter_n = green_n | (
        vis & n_zone & (luma < 55)
        & (cv2.dilate(green_n.astype(np.uint8), np.ones((27, 27), np.uint8), 1) > 0)
    )

    # Green flanks L/R of the sign — DO NOT explode / do not "touch"
    flank_green = (
        vis
        & (g > 115)
        & (g > r * 1.05)
        & (g > bch * 1.0)
        & (s > 40)
        & ~letter_n
        & ~text
        & (
            ((xx < W * 0.38) & (yy < H * 0.58) & (yy > H * 0.12))
            | ((xx > W * 0.58) & (yy < H * 0.72) & (yy > H * 0.22))
        )
    )
    # Include red sphere with right flank (sits in green swoop) as static pair
    sphere = vis & (r > 150) & (r > g * 1.4) & (xx > W * 0.60) & (yy > H * 0.34) & (yy < H * 0.58)
    static = flank_green | sphere

    red = vis & (r > 135) & (r > g * 1.3) & (r > bch * 1.15) & (s > 70) & ~static
    black_tube = vis & (luma < 45) & (xx > W * 0.52) & (yy < H * 0.48) & ~n_zone & ~text_zone & ~static

    yellow = (s > 80) & (v > 80) & (h >= 15) & (h <= 45)
    magenta = (s > 80) & (v > 80) & (((h >= 140) & (h <= 179)) | (h <= 8))
    cyan = (s > 80) & (v > 80) & (h >= 78) & (h <= 110)
    lime = (s > 80) & (v > 80) & (h >= 40) & (h <= 75) & (g > 120)
    burst = vis & (yellow | magenta | cyan | lime | red | black_tube)
    burst &= ~text & ~letter_n & ~static

    claimed = text | letter_n | burst | static
    rest = vis & ~claimed

    def save_mask(name: str, mask: np.ndarray, role: str, idx: int = 0) -> dict | None:
        if mask.sum() < 40:
            return None
        ys, xs = np.where(mask)
        y0, y1 = max(0, ys.min() - 2), min(H, ys.max() + 3)
        x0, x1 = max(0, xs.min() - 2), min(W, xs.max() + 3)
        tile = base[y0:y1, x0:x1].copy()
        tile[:, :, 3] *= mask[y0:y1, x0:x1].astype(np.float32)
        fname = f"{role}_{idx:03d}_{name}.png"
        Image.fromarray(tile.astype(np.uint8)).save(OUT / fname)
        cx = float(xs.mean())
        cy = float(ys.mean())
        dx, dy = (cx - SIZE * 0.5) / SIZE, (cy - SIZE * 0.42) / SIZE
        dist = float(np.hypot(dx, dy) + 1e-4)
        rng = abs(hash((round(cx, 1), round(cy, 1), name, idx))) % 1000 / 1000.0
        return {
            "file": fname,
            "role": role,
            "cx": cx / SIZE * 2 - 1,  # -1..1 for Blender plane of size 2
            "cy": 1 - cy / SIZE * 2,
            "w": (x1 - x0) / SIZE * 2,
            "h": (y1 - y0) / SIZE * 2,
            "ang": float(np.arctan2(dy, dx)),
            "dist": dist,
            "power": 0.5 + 0.9 * rng,
            "spin": float((-1 if idx % 2 == 0 else 1) * (0.4 + 0.8 * rng)),
            "delay": 0.012 * (idx % 7),
            "hue_shift": float((-0.08 + 0.16 * rng)),
        }

    meta = {"size": SIZE, "pieces": []}

    # Static green flanks (untouched by explosion)
    m = save_mask("flanks", static, "static", 0)
    if m:
        meta["pieces"].append(m)

    # Rest filler
    m = save_mask("rest", rest, "rest", 0)
    if m:
        meta["pieces"].append(m)

    # Exploding shards
    opened = cv2.morphologyEx(burst.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    nlab, labels = cv2.connectedComponents(opened)
    si = 0
    for i in range(1, nlab):
        piece = labels == i
        if piece.sum() < 90:
            continue
        m = save_mask("shard", piece, "shard", si)
        if m:
            meta["pieces"].append(m)
            si += 1

    m = save_mask("letter_n", letter_n, "sign", 0)
    if m:
        meta["pieces"].append(m)
    m = save_mask("text", text, "text", 0)
    if m:
        meta["pieces"].append(m)

    with open(OUT / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    # Rebuild check
    rebuild = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    for p in meta["pieces"]:
        img = Image.open(OUT / p["file"]).convert("RGBA")
        # place using bbox from normalized coords
        pw = int(p["w"] / 2 * SIZE)
        ph = int(p["h"] / 2 * SIZE)
        img = img.resize((max(1, pw), max(1, ph)), Image.Resampling.LANCZOS)
        cx = int((p["cx"] + 1) / 2 * SIZE)
        cy = int((1 - p["cy"]) / 2 * SIZE)
        layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        layer.paste(img, (cx - img.width // 2, cy - img.height // 2), img)
        rebuild = Image.alpha_composite(rebuild, layer)
    rebuild.save(OUT / "rebuild.png")
    print(f"Wrote {len(meta['pieces'])} pieces -> {OUT}")
    print(f"shards={si} static_px={int(static.sum())} n={int(letter_n.sum())} text={int(text.sum())}")


if __name__ == "__main__":
    main()
