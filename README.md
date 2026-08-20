# Hyperlinks.SPACE — Animated Telegram Emoji / Sticker

VP9 WEBM animated emoji and sticker for **[Hyperlinks.SPACE](https://www.hyperlinks.space/)**.

## Specs

| Format | Size | Limit |
|--------|------|-------|
| Sticker | 512×512 | ≤256 KB, ≤3s, ≤30 fps, transparent |
| Emoji | 100×100 | ≤256 KB, ≤3s, ≤30 fps, transparent |

## Deliverables

| File | Variant |
|------|---------|
| `hyperlinks-space-sticker.webm` / `hyperlinks-space-emoji.webm` | Current (firebomb FX) |
| `*-firebomb.webm` | Fire + lightning + screen fill |
| `*-shatter.webm` | 3D shatter only |
| `*-layered.webm` | Layered reconstruction |

## Build

```bash
npm install
HL_FRAMES=90 node capture_volumetric3d.mjs
```

Requires FFmpeg with `libvpx-vp9` (alpha) and Playwright.

Main scene: `scene_volumetric3d.html`  
Capture: `capture_volumetric3d.mjs`

## License

© Hyperlinks Space. All rights reserved unless otherwise noted.
