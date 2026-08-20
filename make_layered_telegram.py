"""
Layered Telegram emoji: each 3D part from the reference moves independently.
Pixels come from the original art (no recolor). Safe margins prevent edge crop.
"""
from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageFilter

ROOT = Path(r"c:\1\1\1\1\1\HyperlinksSpaceAnimatedEmoji")
SRC = next(ROOT.glob("ChatGPT Image*.png"))
LAYERS_DIR = ROOT / "layers_full"
FRAMES = ROOT / "render_frames"
FFMPEG = Path(
    r"C:\Users\ASUS\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin\ffmpeg.exe"
)

FPS = 30
DURATION = 3.0
TOTAL = int(FPS * DURATION)
SIZE = 512
# Final fit margin so nothing ever touches emoji edges
SAFE_SCALE = 0.78
# Layer motion uses almost full source; fit_in_frame shrinks the result
LAYER_SCALE = 0.96


def matte_rgba(path: Path) -> np.ndarray:
    arr = np.array(Image.open(path).convert("RGBA")).astype(np.float32)
    rgb = arr[:, :, :3]
    luma = 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]
    alpha = np.clip((luma - 4.0) / 18.0, 0.0, 1.0)
    arr[:, :, 3] = alpha * 255.0
    return arr


def to_square(arr: np.ndarray) -> np.ndarray:
    a = arr[:, :, 3] / 255.0
    ys, xs = np.where(a > 0.05)
    crop = arr[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]
    side = max(crop.shape[0], crop.shape[1])
    sq = np.zeros((side, side, 4), np.float32)
    oy = (side - crop.shape[0]) // 2
    ox = (side - crop.shape[1]) // 2
    sq[oy : oy + crop.shape[0], ox : ox + crop.shape[1]] = crop
    return sq


def build_full_layers() -> list[dict]:
    """Disjoint full-canvas layers; stacked at rest == original."""
    LAYERS_DIR.mkdir(exist_ok=True)
    base = to_square(matte_rgba(SRC))
    H, W = base.shape[:2]
    rgb = base[:, :, :3]
    a = base[:, :, 3] / 255.0
    vis = a > 0.08

    bgr = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2BGR)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
    yy, xx = np.mgrid[0:H, 0:W]
    cx, cy = W * 0.5, H * 0.42
    rr = np.sqrt(((xx - cx) / W) ** 2 + ((yy - cy) / H) ** 2)

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
    sphere = red & (xx > W * 0.55) & (yy > H * 0.32) & (yy < H * 0.62)
    # Prefer compact round blob on the right
    sphere = cv2.morphologyEx(sphere.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
    # If too small, grow from red highlights on right mid
    if sphere.sum() < 500:
        sphere = vis & (r > 160) & (r > g * 1.5) & (xx > W * 0.62) & (yy > H * 0.36) & (yy < H * 0.55)
    red_tube = red & (xx < W * 0.52) & ~sphere

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

    order = [
        ("spikes", spikes),
        ("red_squiggle", red_tube),
        ("black_squiggle", black_tube),
        ("letter_n", letter_n),
        ("text", text),
        ("green_swoop", swoop),
        ("red_sphere", sphere),
    ]

    claimed = np.zeros((H, W), dtype=bool)
    layers = []
    for name, cand in order:
        mask = cand & vis & ~claimed
        claimed |= mask
        out = base.copy()
        out[:, :, 3] = out[:, :, 3] * mask.astype(np.float32)
        # Full-canvas layer (same dims as square) — exact alignment at rest
        img = Image.fromarray(out.astype(np.uint8)).resize((SIZE, SIZE), Image.Resampling.LANCZOS)
        path = LAYERS_DIR / f"{name}.png"
        img.save(path)
        layers.append({"name": name, "file": path.name, "pixels": int(mask.sum())})
        print(f"  {name}: {mask.sum()} px")

    rest = vis & ~claimed
    out = base.copy()
    out[:, :, 3] = out[:, :, 3] * rest.astype(np.float32)
    img = Image.fromarray(out.astype(np.uint8)).resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    img.save(LAYERS_DIR / "rest.png")
    layers.insert(0, {"name": "rest", "file": "rest.png", "pixels": int(rest.sum())})
    print(f"  rest: {rest.sum()} px")

    # Hero for QA
    hero = Image.fromarray(base.astype(np.uint8)).resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    hero.save(LAYERS_DIR / "hero.png")

    # Rebuild check
    rebuild = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    for L in layers:
        rebuild = Image.alpha_composite(rebuild, Image.open(LAYERS_DIR / L["file"]))
    rebuild.save(LAYERS_DIR / "rebuild.png")
    ha = np.array(hero).astype(float)
    ra = np.array(rebuild).astype(float)
    m = ha[:, :, 3] > 10
    diff = np.abs(ha - ra)[m].mean() if m.any() else 0
    print(f"rebuild mean abs diff: {diff:.2f}")

    with open(LAYERS_DIR / "meta.json", "w", encoding="utf-8") as f:
        json.dump({"layers": layers}, f, indent=2)
    return layers


def perspective_coeffs(src_pts, dst_pts):
    matrix = []
    for (x, y), (u, v) in zip(src_pts, dst_pts):
        matrix.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        matrix.append([0, 0, 0, x, y, 1, -v * x, -v * y])
    A = np.asarray(matrix, dtype=np.float64)
    B = np.asarray(dst_pts, dtype=np.float64).reshape(8)
    return tuple(np.linalg.solve(A, B).tolist())


def warp_layer(im: Image.Image, t: float, motion: dict) -> Image.Image:
    """Independent part motion; stays inside SAFE_SCALE box."""
    w = h = SIZE
    # Global layer box (almost full); final SAFE_SCALE applied after composite
    gscale = LAYER_SCALE + motion.get("breathe", 0.0) * math.sin(t * math.tau + motion.get("phase", 0))
    ox = motion.get("x", 0.0) * math.sin(t * math.tau + motion.get("phase", 0)) * w
    oy = motion.get("y", 0.0) * math.cos(t * math.tau + motion.get("phase", 0.5)) * h
    yaw = motion.get("yaw", 0.0) * math.sin(t * math.tau + motion.get("phase", 0))
    pitch = motion.get("pitch", 0.0) * math.sin(t * math.tau + motion.get("phase", 1))
    roll = motion.get("roll", 0.0) * math.sin(t * math.tau + motion.get("phase", 2))
    spin = motion.get("spin", 0.0) * math.sin(t * math.tau)  # oscillating spin (loop-safe)
    pop = 1.0 + motion.get("pop", 0.0) * math.sin(t * math.tau * 2 + motion.get("phase", 0))

    cx, cy = w / 2 + ox, h / 2 + oy
    hw = (w * gscale * pop) / 2
    hh = (h * gscale * pop) / 2
    corners = np.array([[-hw, -hh], [hw, -hh], [hw, hh], [-hw, hh]], dtype=np.float64)

    ang = roll + spin
    ca, sa = math.cos(ang), math.sin(ang)
    corners = corners @ np.array([[ca, -sa], [sa, ca]]).T

    for i, (x, y) in enumerate(corners):
        z = 1.0 + yaw * (x / max(hw, 1e-6)) + pitch * (y / max(hh, 1e-6))
        z = max(z, 0.65)
        corners[i, 0] = x / z
        corners[i, 1] = y / z

    pad = 6.0
    dst = []
    for x, y in corners:
        dx = float(np.clip(cx + x, pad, w - pad))
        dy = float(np.clip(cy + y, pad, h - pad))
        dst.append((dx, dy))
    src = [(0, 0), (w, 0), (w, h), (0, h)]
    coeffs = perspective_coeffs(src, dst)

    rgb = im.convert("RGB").transform(
        (w, h), Image.Transform.PERSPECTIVE, coeffs, Image.Resampling.BICUBIC, fillcolor=(0, 0, 0)
    )
    alpha = im.split()[-1].transform(
        (w, h), Image.Transform.PERSPECTIVE, coeffs, Image.Resampling.BILINEAR, fillcolor=0
    )
    out = rgb.copy()
    out.putalpha(alpha)
    return out


# Per-part motion — spikes/swoops move more; text/N subtler
MOTIONS = {
    "rest": dict(x=0.01, y=0.01, yaw=0.04, pitch=0.03, roll=0.015, pop=0.012, breathe=0.006, phase=0.0),
    "spikes": dict(x=0.02, y=0.02, yaw=0.12, pitch=0.09, roll=0.07, spin=0.22, pop=0.07, breathe=0.012, phase=0.3),
    "red_squiggle": dict(x=0.04, y=0.045, yaw=0.14, pitch=0.11, roll=0.16, pop=0.05, breathe=0.01, phase=1.1),
    "black_squiggle": dict(x=0.035, y=0.04, yaw=0.12, pitch=0.10, roll=-0.14, pop=0.05, breathe=0.01, phase=2.0),
    "green_swoop": dict(x=0.035, y=0.035, yaw=0.13, pitch=0.10, roll=0.12, pop=0.06, breathe=0.012, phase=1.6),
    "letter_n": dict(x=0.018, y=0.022, yaw=0.10, pitch=0.07, roll=0.05, pop=0.045, breathe=0.015, phase=0.5),
    "text": dict(x=0.015, y=0.018, yaw=0.08, pitch=0.06, roll=0.04, pop=0.03, breathe=0.012, phase=0.8),
    "red_sphere": dict(x=0.05, y=0.055, yaw=0.15, pitch=0.12, roll=0.10, pop=0.12, breathe=0.02, phase=2.4),
}

# Back → front composite order
Z_ORDER = [
    "rest",
    "spikes",
    "red_squiggle",
    "black_squiggle",
    "green_swoop",
    "letter_n",
    "text",
    "red_sphere",
]


def fit_in_frame(im: Image.Image, scale: float = SAFE_SCALE) -> Image.Image:
    """Hard guarantee: whole composite is centered with empty margin (no edge crop)."""
    w, h = im.size
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    small = im.resize((nw, nh), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(small, ((w - nw) // 2, (h - nh) // 2), small)
    return out


def shine_sweep(base: Image.Image, t: float) -> Image.Image:
    w = h = SIZE
    shine = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    from PIL import ImageDraw

    draw = ImageDraw.Draw(shine)
    phase = (t * w * 1.3) % (w * 1.5) - w * 0.25
    for i in range(14):
        x = phase + i * 3
        a = int(22 * math.exp(-((i - 6) ** 2) / 14))
        draw.line([(x, -10), (x + h * 0.32, h + 10)], fill=(255, 255, 255, a), width=2)
    logo_a = base.split()[-1]
    sa = ImageChops.multiply(shine.split()[-1], logo_a)
    shine.putalpha(sa)
    return Image.alpha_composite(base, shine)


def render_frames(layers_meta: list[dict]):
    FRAMES.mkdir(exist_ok=True)
    for p in FRAMES.glob("*.png"):
        p.unlink()

    loaded = {
        L["name"]: Image.open(LAYERS_DIR / L["file"]).convert("RGBA")
        for L in layers_meta
    }
    # ensure all z-order keys exist
    for name in Z_ORDER:
        if name not in loaded:
            loaded[name] = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))

    for i in range(TOTAL):
        t = i / TOTAL
        canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        for name in Z_ORDER:
            motion = MOTIONS.get(name, MOTIONS["rest"])
            part = warp_layer(loaded[name], t, motion)
            canvas = Image.alpha_composite(canvas, part)
        canvas = shine_sweep(canvas, t)
        canvas = fit_in_frame(canvas, SAFE_SCALE)
        canvas.save(FRAMES / f"frame_{i+1:04d}.png")
        if i % 15 == 0:
            print(f"frame {i+1}/{TOTAL}")

    t0 = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    for name in Z_ORDER:
        t0 = Image.alpha_composite(t0, warp_layer(loaded[name], 0.0, MOTIONS.get(name, MOTIONS["rest"])))
    t0 = fit_in_frame(shine_sweep(t0, 0.0), SAFE_SCALE)
    t0.save(ROOT / "preview_t0.png")
    print("wrote preview_t0.png")


def encode(size: int, name: str, crf: int, br: str):
    out = ROOT / name
    cmd = [
        str(FFMPEG), "-y",
        "-framerate", str(FPS),
        "-i", str(FRAMES / "frame_%04d.png"),
        "-vf", f"scale={size}:{size}:flags=lanczos",
        "-c:v", "libvpx-vp9",
        "-pix_fmt", "yuva420p",
        "-auto-alt-ref", "0",
        "-b:v", br,
        "-crf", str(crf),
        "-an", "-t", str(DURATION), "-r", str(FPS),
        "-row-mt", "1",
        str(out),
    ]
    subprocess.check_call(cmd)
    kb = out.stat().st_size / 1024
    print(f"{out.name}: {kb:.1f} KB {'OK' if out.stat().st_size <= 256*1024 else 'OVER'}")


def main():
    print("Building full-canvas layers…")
    meta = build_full_layers()
    print("Rendering layered animation…")
    render_frames(meta)
    encode(512, "hyperlinks-space-sticker.webm", 48, "140k")
    encode(100, "hyperlinks-space-emoji.webm", 42, "90k")
    print("DONE")


if __name__ == "__main__":
    main()
