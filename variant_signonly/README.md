# Sign-only sticker + emoji

Same shatter / sphere / second-boom animation as the video avatar, on a **transparent** canvas.

Fitted inside an Android-style rounded square (~14% edge inset, ~22% corner radius) so corners survive Telegram’s emoji rounding.

```bash
HL_FRAMES=90 node capture_signonly.mjs
```

## Outputs
- `hyperlinks-space-sticker-sign.webm` — 512² VP9+alpha, ≤256 KB
- `hyperlinks-space-emoji-sign.webm` — 100² VP9+alpha, ≤64 KB

Preview: `../preview_sign.html`
