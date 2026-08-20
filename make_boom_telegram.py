"""
Hyperlinks.SPACE boom emoji — same elements only (no overlay duplicates).

Timeline (seamless loop):
  1) Explosion — shards fly out
  2) Zoom the N sign
  3) Zoom text on a diagonal (max presence)
  4) Everything returns to the assembled logo
No fade in/out.
"""
from __future__ import annotations

import math
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

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
SIZE = 512
SAFE_SCALE = 0.78  # final fit so zoomed steps never clip


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


def resize_rgba(arr: np.ndarray, size: int) -> np.ndarray:
    return np.array(
        Image.fromarray(arr.astype(np.uint8)).resize((size, size), Image.Resampling.LANCZOS)
    ).astype(np.float32)


def split_components(mask: np.ndarray, min_px: int = 90) -> list[np.ndarray]:
    m = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, labels = cv2.connectedComponents(m)
    return [labels == i for i in range(1, n) if (labels == i).sum() >= min_px]


def extract_piece(base: np.ndarray, mask: np.ndarray) -> dict:
    H, W = mask.shape
    ys, xs = np.where(mask)
    y0, y1 = max(0, ys.min() - 2), min(H, ys.max() + 3)
    x0, x1 = max(0, xs.min() - 2), min(W, xs.max() + 3)
    tile = base[y0:y1, x0:x1].copy()
    tile[:, :, 3] *= mask[y0:y1, x0:x1].astype(np.float32)
    scale = SIZE / H
    tw = max(2, int(round((x1 - x0) * scale)))
    th = max(2, int(round((y1 - y0) * scale)))
    img = Image.fromarray(tile.astype(np.uint8)).resize((tw, th), Image.Resampling.LANCZOS)
    cx = float(xs.mean()) * scale
    cy = float(ys.mean()) * scale
    dx, dy = cx - SIZE * 0.5, cy - SIZE * 0.42
    dist = math.hypot(dx, dy) + 1e-3
    return {
        "img": img,
        "cx": cx,
        "cy": cy,
        "w": tw,
        "h": th,
        "ang": math.atan2(dy, dx),
        "dist": dist,
    }


def build_pieces():
    base = resize_rgba(matte_square(), SIZE)
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
        vis
        & text_zone
        & (luma < 60)
        & (s < 90)
        & (cv2.dilate(white.astype(np.uint8), np.ones((23, 23), np.uint8), 1) > 0)
    )

    n_zone = (yy < H * 0.50) & (np.abs(xx - ocx) / W < 0.30) & (rr < 0.40)
    green_n = vis & n_zone & (g > 110) & (g > r * 1.1) & (g > bch * 1.05) & (s > 35)
    letter_n = green_n | (
        vis
        & n_zone
        & (luma < 55)
        & (cv2.dilate(green_n.astype(np.uint8), np.ones((27, 27), np.uint8), 1) > 0)
    )

    red = vis & (r > 135) & (r > g * 1.3) & (r > bch * 1.15) & (s > 70)
    sphere = vis & (r > 150) & (r > g * 1.45) & (xx > W * 0.58) & (yy > H * 0.34) & (yy < H * 0.58)
    red_tube = red & (xx < W * 0.52) & ~sphere
    swoop = (
        vis
        & (g > 120)
        & (g > r * 1.08)
        & (s > 50)
        & (xx > W * 0.55)
        & (yy > H * 0.28)
        & (yy < H * 0.70)
        & ~n_zone
    )
    black_tube = vis & (luma < 45) & (xx > W * 0.52) & (yy < H * 0.48) & ~n_zone & ~text_zone

    yellow = (s > 80) & (v > 80) & (h >= 15) & (h <= 45)
    magenta = (s > 80) & (v > 80) & (((h >= 140) & (h <= 179)) | (h <= 8))
    cyan = (s > 80) & (v > 80) & (h >= 78) & (h <= 110)
    lime = (s > 80) & (v > 80) & (h >= 40) & (h <= 75) & (g > 120)
    burst = vis & (yellow | magenta | cyan | lime | red_tube | swoop | black_tube | sphere)
    burst &= ~text & ~letter_n

    claimed = text | letter_n | burst
    rest_mask = vis & ~claimed

    shards = []
    for i, m in enumerate(split_components(burst, min_px=90)):
        p = extract_piece(base, m)
        rng = abs(hash((round(p["cx"], 1), round(p["cy"], 1), i))) % 1000 / 1000.0
        p["power"] = 0.55 + 0.85 * rng
        p["spin"] = (-1 if i % 2 == 0 else 1) * (0.4 + 0.7 * rng)
        p["delay"] = 0.015 * (i % 6)
        shards.append(p)

    logo_n = extract_piece(base, letter_n) if letter_n.sum() > 30 else None
    logo_text = extract_piece(base, text) if text.sum() > 30 else None
    rest = extract_piece(base, rest_mask) if rest_mask.sum() > 30 else None

    # Rebuild QA
    rebuild = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    for p in ([rest] if rest else []) + shards + ([logo_n] if logo_n else []) + ([logo_text] if logo_text else []):
        layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        x = int(round(p["cx"] - p["img"].width / 2))
        y = int(round(p["cy"] - p["img"].height / 2))
        layer.paste(p["img"], (x, y), p["img"])
        rebuild = Image.alpha_composite(rebuild, layer)
    rebuild.save(ROOT / "preview_rebuild.png")

    print(f"shards={len(shards)} text_px={int(text.sum())} n_px={int(letter_n.sum())} rest_px={int(rest_mask.sum())}")
    return shards, logo_n, logo_text, rest


def trap(t: float, up0: float, up1: float, down0: float, down1: float) -> float:
    """0 → 1 → hold → 0. Seamless if 0 at t=0 and t=1."""
    if t <= up0 or t >= down1:
        return 0.0
    if t < up1:
        u = (t - up0) / max(1e-6, up1 - up0)
        return u * u * (3 - 2 * u)  # smoothstep up
    if t < down0:
        return 1.0
    u = (t - down0) / max(1e-6, down1 - down0)
    u = u * u * (3 - 2 * u)
    return 1.0 - u


def paste_transformed(canvas, piece, cx, cy, scale, rot_deg):
    img = piece["img"]
    if scale <= 0.02:
        return
    w = max(1, int(round(img.width * scale)))
    h = max(1, int(round(img.height * scale)))
    max_dim = max(w, h)
    if max_dim > SIZE * 0.98:
        k = (SIZE * 0.98) / max_dim
        w, h = max(1, int(w * k)), max(1, int(h * k))
    scaled = img.resize((w, h), Image.Resampling.BILINEAR)
    if abs(rot_deg) > 0.05:
        scaled = scaled.rotate(rot_deg, resample=Image.Resampling.BILINEAR, expand=True)
    x = int(round(cx - scaled.width / 2))
    y = int(round(cy - scaled.height / 2))
    x = int(np.clip(x, -scaled.width * 0.2, SIZE - scaled.width * 0.8))
    y = int(np.clip(y, -scaled.height * 0.2, SIZE - scaled.height * 0.8))
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    layer.paste(scaled, (x, y), scaled)
    canvas.alpha_composite(layer)


def fit_in_frame(im: Image.Image, scale: float = SAFE_SCALE) -> Image.Image:
    w, h = im.size
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    small = im.resize((nw, nh), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(small, ((w - nw) // 2, (h - nh) // 2), small)
    return out


def render(shards, logo_n, logo_text, rest):
    FRAMES.mkdir(exist_ok=True)
    for p in FRAMES.glob("*.png"):
        p.unlink()

    # 3 beats + return (all envelopes 0 at t=0 and t=1)
    # 1) Explosion
    # 2) Zoom N
    # 3) Zoom text diagonally
    # then settle home
    for i in range(TOTAL):
        t = i / TOTAL
        explode = trap(t, 0.00, 0.14, 0.68, 0.92)
        zoom_n = trap(t, 0.18, 0.32, 0.70, 0.93)
        zoom_text = trap(t, 0.38, 0.52, 0.72, 0.95)

        canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))

        # REST (same logo pixels) — slight settle only
        if rest is not None:
            paste_transformed(canvas, rest, rest["cx"], rest["cy"], 1.0, 0.0)

        # STEP 1 — each shard is a real piece of the logo (no duplicate base)
        max_fly = SIZE * 0.14
        for j, piece in enumerate(shards):
            d = piece["delay"]
            e = trap(t, 0.00 + d, 0.14 + d, 0.68, 0.92)
            fly = e * piece["power"] * max_fly
            sc = 1.0 + e * (0.25 + 0.35 * piece["power"])
            px = piece["cx"] + math.cos(piece["ang"]) * fly
            py = piece["cy"] + math.sin(piece["ang"]) * fly
            px = float(np.clip(px, SIZE * 0.08, SIZE * 0.92))
            py = float(np.clip(py, SIZE * 0.08, SIZE * 0.92))
            rot = piece["spin"] * e * 48
            paste_transformed(canvas, piece, px, py, sc, rot)

        # STEP 2 — zoom the N sign (same N pixels)
        if logo_n is not None:
            sc = 1.0 + 0.55 * zoom_n
            # slight lift while zooming for impact
            cy = logo_n["cy"] - zoom_n * SIZE * 0.03
            paste_transformed(canvas, logo_n, logo_n["cx"], cy, sc, -zoom_n * 4)

        # STEP 3 — zoom text diagonally (max space / presence)
        if logo_text is not None:
            sc = 1.0 + 0.70 * zoom_text
            # diagonal toward bottom-right, then back
            dx = zoom_text * SIZE * 0.07
            dy = zoom_text * SIZE * 0.06
            rot = zoom_text * 8  # slight diagonal attitude
            paste_transformed(
                canvas,
                logo_text,
                logo_text["cx"] + dx,
                logo_text["cy"] + dy,
                sc,
                rot,
            )

        canvas = fit_in_frame(canvas, SAFE_SCALE)

        # Hard clear rim
        r, g, b, a = canvas.split()
        wipe = Image.new("L", (SIZE, SIZE), 255)
        wd = ImageDraw.Draw(wipe)
        m = 6
        wd.rectangle([0, 0, SIZE - 1, m - 1], fill=0)
        wd.rectangle([0, SIZE - m, SIZE - 1, SIZE - 1], fill=0)
        wd.rectangle([0, 0, m - 1, SIZE - 1], fill=0)
        wd.rectangle([SIZE - m, 0, SIZE - 1, SIZE - 1], fill=0)
        wipe = wipe.filter(ImageFilter.GaussianBlur(1.2))
        canvas = Image.merge("RGBA", (r, g, b, ImageChops.multiply(a, wipe)))

        canvas.save(FRAMES / f"frame_{i+1:04d}.png")
        if i % 15 == 0:
            print(
                f"frame {i+1}/{TOTAL} expl={explode:.2f} N={zoom_n:.2f} text={zoom_text:.2f}"
            )

    # Previews: rest, explosion peak, N zoom, text zoom
    Image.open(FRAMES / "frame_0001.png").save(ROOT / "preview_t0.png")
    Image.open(FRAMES / f"frame_{int(0.14*TOTAL)+1:04d}.png").save(ROOT / "preview_boom.png")
    Image.open(FRAMES / f"frame_{int(0.32*TOTAL)+1:04d}.png").save(ROOT / "preview_zoom_n.png")
    Image.open(FRAMES / f"frame_{int(0.52*TOTAL)+1:04d}.png").save(ROOT / "preview_zoom_text.png")
    print("wrote previews")


def encode(size: int, name: str, crf: int, br: str):
    out = ROOT / name
    cmd = [
        str(FFMPEG),
        "-y",
        "-framerate",
        str(FPS),
        "-i",
        str(FRAMES / "frame_%04d.png"),
        "-vf",
        f"scale={size}:{size}:flags=lanczos",
        "-c:v",
        "libvpx-vp9",
        "-pix_fmt",
        "yuva420p",
        "-auto-alt-ref",
        "0",
        "-b:v",
        br,
        "-crf",
        str(crf),
        "-an",
        "-t",
        str(DURATION),
        "-r",
        str(FPS),
        "-row-mt",
        "1",
        str(out),
    ]
    subprocess.check_call(cmd)
    kb = out.stat().st_size / 1024
    print(f"{out.name}: {kb:.1f} KB {'OK' if out.stat().st_size <= 256*1024 else 'OVER'}")


def main():
    print("Building pieces (same elements only)…")
    shards, logo_n, logo_text, rest = build_pieces()
    print("Rendering 3-step boom…")
    render(shards, logo_n, logo_text, rest)
    encode(512, "hyperlinks-space-sticker.webm", 44, "160k")
    encode(100, "hyperlinks-space-emoji.webm", 40, "100k")
    print("DONE")


if __name__ == "__main__":
    main()
