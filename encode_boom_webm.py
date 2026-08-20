"""Encode boom 3D frames to Telegram WEBM."""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(r"c:\1\1\1\1\1\HyperlinksSpaceAnimatedEmoji")
FRAMES = ROOT / "render_frames"
FFMPEG = Path(
    r"C:\Users\ASUS\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin\ffmpeg.exe"
)


def encode(size, name, crf, br):
    out = ROOT / name
    cmd = [
        str(FFMPEG), "-y", "-framerate", "30",
        "-i", str(FRAMES / "frame_%04d.png"),
        "-vf", f"scale={size}:{size}:flags=lanczos",
        "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0",
        "-b:v", br, "-crf", str(crf), "-an", "-t", "3", "-r", "30", "-row-mt", "1",
        str(out),
    ]
    subprocess.check_call(cmd)
    kb = out.stat().st_size / 1024
    print(f"{out.name}: {kb:.1f} KB {'OK' if out.stat().st_size <= 256*1024 else 'OVER'}")


def main():
    n = len(list(FRAMES.glob("frame_*.png")))
    print("frames", n)
    if n < 30:
        raise SystemExit("not enough frames")
    encode(512, "hyperlinks-space-sticker.webm", 44, "160k")
    encode(100, "hyperlinks-space-emoji.webm", 40, "100k")


if __name__ == "__main__":
    main()
