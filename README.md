# Hyperlinks.SPACE — Animated Telegram Emoji / Sticker

VP9 WEBM animated emoji and sticker for **[Hyperlinks.SPACE](https://www.hyperlinks.space/)**.

Telegram video stickers/emoji require **VP9 in a WebM container** ([official encoding guide](https://core.telegram.org/stickers/webm-vp9-encoding)). **AV1 was evaluated and rejected** for this pipeline: Telegram does not accept AV1 for stickers/emoji, and FFmpeg `libaom-av1` cannot encode a single-stream alpha channel (`yuva420p` falls back to opaque `yuv420p`). Dual-stream AV1+alpha is larger and still not Telegram-uploadable. Deliverables stay **VP9 + alpha**.

## Specs

| Format | Size | Limit |
|--------|------|-------|
| Sticker | 512×512 | ≤256 KB, ≤3s, ≤30 fps, transparent VP9 WebM |
| Custom emoji | 100×100 | ≤64 KB, ≤3s, ≤30 fps, transparent VP9 WebM |

No audio. Loop preferred.

## Deliverables

| File | Variant |
|------|---------|
| `hyperlinks-space-sticker.webm` / `hyperlinks-space-emoji.webm` | Current (firebomb FX) |
| `*-firebomb.webm` | Fire + lightning + screen fill |
| `*-shatter.webm` | 3D shatter only |
| `*-layered.webm` | Layered reconstruction |
| `*-sign.webm` | Sign only (N, no text), centered & enlarged |

## Build

```bash
npm install
HL_FRAMES=90 node capture_volumetric3d.mjs
HL_FRAMES=90 node capture_signonly.mjs
```

Requires FFmpeg with `libvpx-vp9` (alpha via `format=yuva420p` + `alpha_mode=1`) and Playwright.

Main scene: `scene_volumetric3d.html` (`?signOnly=1` for sign-only)  
Capture: `capture_volumetric3d.mjs`, `capture_signonly.mjs`

## License

© Hyperlinks Space. All rights reserved unless otherwise noted.
