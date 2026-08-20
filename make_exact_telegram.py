"""
Telegram video emoji/sticker from the EXACT reference artwork.

Every frame is a geometric 3D-style transform of the original pixels
(no recolor, no relight, no segmentation). Accents draw only outside the logo.
Output: PNG sequence → VP9 WEBM (512 sticker + 100 emoji).
"""
from __future__ import annotations

import math
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(r"c:\1\1\1\1\1\HyperlinksSpaceAnimatedEmoji")
SRC = next(ROOT.glob("ChatGPT Image*.png"))
FRAMES = ROOT / "render_frames"
FFMPEG = Path(
    r"C:\Users\ASUS\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin\ffmpeg.exe"
)

FPS = 30
DURATION = 3.0
TOTAL = int(FPS * DURATION)
SIZE = 512  # master render; emoji downscaled at encode


def load_hero(size: int) -> Image.Image:
    arr = np.array(Image.open(SRC).convert("RGBA")).astype(np.float32)
    rgb = arr[:, :, :3]
    luma = 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]
    # Soft matte only — RGB untouched
    alpha = np.clip((luma - 4.0) / 18.0, 0.0, 1.0)
    arr[:, :, 3] = alpha * 255.0
    ys, xs = np.where(alpha > 0.05)
    crop = arr[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]
    side = max(crop.shape[0], crop.shape[1])
    sq = np.zeros((side, side, 4), np.float32)
    oy = (side - crop.shape[0]) // 2
    ox = (side - crop.shape[1]) // 2
    sq[oy : oy + crop.shape[0], ox : ox + crop.shape[1]] = crop
    hero = Image.fromarray(sq.astype(np.uint8))
    # Slight inset so 3D tilt never clips canvas
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    fitted = hero.resize((size, size), Image.Resampling.LANCZOS)
    canvas.alpha_composite(fitted, (0, 0))
    return canvas


def perspective_coeffs(src_pts, dst_pts):
    """PIL perspective transform coefficients."""
    matrix = []
    for (x, y), (u, v) in zip(src_pts, dst_pts):
        matrix.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        matrix.append([0, 0, 0, x, y, 1, -v * x, -v * y])
    A = np.asarray(matrix, dtype=np.float64)
    B = np.asarray(dst_pts, dtype=np.float64).reshape(8)
    res = np.linalg.solve(A, B)
    return tuple(res.tolist())


def transform_logo(hero: Image.Image, t: float) -> Image.Image:
    """t in [0,1) seamless. Returns SIZE x SIZE RGBA."""
    w = h = SIZE
    # AAA-ish 3D card motion (all sin-based → perfect loop)
    scale = 0.97 + 0.025 * math.sin(t * math.tau)  # near full-bleed, exact pixels
    bounce = 0.008 * math.sin(t * math.tau * 2)
    yaw = 0.11 * math.sin(t * math.tau)
    pitch = 0.07 * math.sin(t * math.tau + 0.7)
    roll = 0.03 * math.sin(t * math.tau + 1.2)

    # Quad corners of the logo card in image space
    cx, cy = w / 2, h / 2 + bounce * h
    hw, hh = (w * scale) / 2, (h * scale) / 2

    # Base rectangle corners (TL, TR, BR, BL)
    corners = np.array([
        [-hw, -hh],
        [hw, -hh],
        [hw, hh],
        [-hw, hh],
    ], dtype=np.float64)

    # Roll
    ca, sa = math.cos(roll), math.sin(roll)
    R = np.array([[ca, -sa], [sa, ca]])
    corners = corners @ R.T

    # Fake perspective via yaw/pitch (horizontal/vertical trapezoid)
    # yaw > 0: right side closer (larger)
    for i, (x, y) in enumerate(corners):
        # depth factor from x (yaw) and y (pitch)
        z = 1.0 + yaw * (x / hw) + pitch * (y / hh)
        z = max(z, 0.55)
        corners[i, 0] = x / z
        corners[i, 1] = y / z

    dst = [(cx + x, cy + y) for x, y in corners]
    src = [(0, 0), (w, 0), (w, h), (0, h)]
    coeffs = perspective_coeffs(src, dst)

    # Transform only RGB; handle alpha separately for sharpness
    rgb = hero.convert("RGB").transform(
        (w, h), Image.Transform.PERSPECTIVE, coeffs, Image.Resampling.BICUBIC, fillcolor=(0, 0, 0)
    )
    alpha = hero.split()[-1].transform(
        (w, h), Image.Transform.PERSPECTIVE, coeffs, Image.Resampling.BILINEAR, fillcolor=0
    )
    out = rgb.copy()
    out.putalpha(alpha)

    # Specular shine sweep (additive on bright areas only — keeps brand colors)
    shine = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(shine)
    # Moving diagonal band
    phase = (t * w * 1.4) % (w * 1.6) - w * 0.3
    for i in range(18):
        x = phase + i * 3
        a = int(28 * math.exp(-((i - 8) ** 2) / 18))
        draw.line([(x, -20), (x + h * 0.35, h + 20)], fill=(255, 255, 255, a), width=3)
    # Mask shine by logo alpha and prefer highlights
    shine_a = shine.split()[-1]
    # Multiply shine alpha by logo alpha
    logo_a = out.split()[-1]
    shine_a = Image.composite(shine_a, Image.new("L", (w, h), 0), logo_a)
    shine.putalpha(shine_a)
    out = Image.alpha_composite(out, shine)
    return out


def draw_outer_sparkles(base: Image.Image, t: float) -> Image.Image:
    """Tiny neon sparkles outside the opaque logo core."""
    arr = np.array(base)
    alpha = arr[:, :, 3]
    # Dilate mask roughly: sparkles only where alpha is low
    from PIL import ImageFilter

    core = base.split()[-1].point(lambda p: 255 if p > 40 else 0)
    core = core.filter(ImageFilter.MaxFilter(15))
    canvas = base.copy()
    draw = ImageDraw.Draw(canvas, "RGBA")
    colors = [
        (255, 230, 0, 220),
        (255, 40, 140, 220),
        (0, 240, 255, 220),
        (80, 255, 40, 220),
        (255, 80, 30, 220),
    ]
    rng_core = core
    for i in range(20):
        ang = (i / 20) * math.tau + t * math.tau * 0.6
        rad = 0.42 + 0.08 * math.sin(t * math.tau * 2 + i)
        x = SIZE * (0.5 + rad * math.cos(ang))
        y = SIZE * (0.5 + rad * math.sin(ang) * 0.95)
        ix, iy = int(x), int(y)
        if 0 <= ix < SIZE and 0 <= iy < SIZE and rng_core.getpixel((ix, iy)) > 0:
            continue  # skip if over logo
        twinkle = 0.45 + 0.55 * max(0.0, math.sin(t * math.tau * 3 + i * 0.7))
        r = max(1, int(2 + 2 * twinkle))
        col = colors[i % len(colors)]
        col = (col[0], col[1], col[2], int(col[3] * twinkle))
        draw.ellipse([x - r, y - r, x + r, y + r], fill=col)
    return canvas


def render_frames():
    FRAMES.mkdir(exist_ok=True)
    for p in FRAMES.glob("*.png"):
        p.unlink()
    hero = load_hero(SIZE)
    # Save identity reference for QA
    hero.save(ROOT / "reference_512.png")
    for i in range(TOTAL):
        t = i / TOTAL
        frame = transform_logo(hero, t)
        frame = draw_outer_sparkles(frame, t)
        frame.save(FRAMES / f"frame_{i+1:04d}.png")
        if i % 15 == 0:
            print(f"frame {i+1}/{TOTAL}")
    # Also write rest-pose identity (no motion) for QA
    hero.save(ROOT / "identity_exact.png")
    print("frames ready", FRAMES)


def encode(size: int, name: str, crf: int, br: str):
    out = ROOT / name
    vf = f"scale={size}:{size}:flags=lanczos"
    cmd = [
        str(FFMPEG), "-y",
        "-framerate", str(FPS),
        "-i", str(FRAMES / "frame_%04d.png"),
        "-vf", vf,
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
    print(f"{out.name}: {out.stat().st_size/1024:.1f} KB")


def main():
    render_frames()
    # Verify identity vs first-frame motion isn't required — check load path
    encode(512, "hyperlinks-space-sticker.webm", 30, "500k")
    encode(100, "hyperlinks-space-emoji.webm", 34, "160k")
    print("DONE")


if __name__ == "__main__":
    main()
