#!/usr/bin/env python3
"""Encode Telegram-compliant VP9 WEBM from PNG frame sequence."""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(r"c:\1\1\1\1\1\HyperlinksSpaceAnimatedEmoji")
FFMPEG = Path(
    r"C:\Users\ASUS\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin\ffmpeg.exe"
)
FRAMES = ROOT / "render_frames"


def encode(size: int, out_name: str, crf: int, bitrate: str):
    out = ROOT / out_name
    # scale with alpha preserved
    vf = f"scale={size}:{size}:flags=lanczos:format=rgba,format=yuva420p"
    cmd = [
        str(FFMPEG),
        "-y",
        "-framerate",
        "30",
        "-i",
        str(FRAMES / "frame_%04d.png"),
        "-vf",
        vf,
        "-c:v",
        "libvpx-vp9",
        "-pix_fmt",
        "yuva420p",
        "-auto-alt-ref",
        "0",
        "-b:v",
        bitrate,
        "-crf",
        str(crf),
        "-an",
        "-t",
        "3",
        "-r",
        "30",
        "-row-mt",
        "1",
        str(out),
    ]
    print(" ".join(cmd))
    subprocess.check_call(cmd)
    kb = out.stat().st_size / 1024
    print(f"Wrote {out} ({kb:.1f} KB)")
    if kb > 256:
        print("WARNING: exceeds Telegram 256KB video emoji/sticker limit")


def main():
    n = len(list(FRAMES.glob("frame_*.png")))
    print(f"Frames: {n}")
    if n < 30:
        raise SystemExit("Not enough frames")
    # Sticker 512 + emoji 100
    encode(512, "hyperlinks-space-sticker.webm", crf=32, bitrate="450k")
    encode(100, "hyperlinks-space-emoji.webm", crf=36, bitrate="140k")


if __name__ == "__main__":
    main()
