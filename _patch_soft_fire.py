from pathlib import Path

path = Path(r"c:\1\1\1\1\1\HyperlinksSpaceAnimatedEmoji\scene_volumetric3d.html")
text = path.read_text(encoding="utf-8")

def repl(old, new, label):
    global text
    if old not in text:
        raise SystemExit(f"FAIL: {label}")
    text = text.replace(old, new, 1)
    print("ok", label)

# --- Soft rounded flame (not jagged chips) ---
start = text.find("function makeSignFlameTex(seed) {")
end = text.find("function makeWhiteFlashTex() {")
if start < 0 or end < 0:
    raise SystemExit(f"flame markers {start} {end}")

text = text[:start] + r'''function makeSignFlameTex(seed) {
  const rnd = seeded(seed * 91 + 5);
  const w = 256, h = 480;
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  const ctx = c.getContext('2d');
  const lean = (rnd() - 0.5) * 36;
  const cx = w * 0.5 + lean * 0.15;
  const top = 18 + rnd() * 16;
  const bot = 460;
  const hw = 78 + rnd() * 28;
  /* Soft round cartoon fire — smooth flamePath, no jagged chip edges. */
  for (let i = 0; i < 4; i++) {
    const k = i / 3;
    flamePath(ctx, cx + lean * k * 0.05, top + 6 * k, bot - 4 * k, hw * (1.25 - k * 0.12));
    const a = 0.16 + (1 - k) * 0.18;
    const g = ctx.createLinearGradient(cx, bot, cx + lean * 0.2, top);
    g.addColorStop(0.00, `rgba(255,50,0,${a * 0.45})`);
    g.addColorStop(0.4, `rgba(255,130,15,${a})`);
    g.addColorStop(0.75, `rgba(255,210,60,${a * 0.85})`);
    g.addColorStop(1.00, `rgba(255,255,220,${a * 0.25})`);
    ctx.fillStyle = g;
    ctx.fill();
  }
  flamePath(ctx, cx, top + 22, bot - 10, hw * 0.78);
  const body = ctx.createLinearGradient(cx, bot, cx + lean * 0.25, top);
  body.addColorStop(0.00, 'rgba(255,35,0,0.95)');
  body.addColorStop(0.3, 'rgba(255,100,0,1)');
  body.addColorStop(0.58, 'rgba(255,175,25,1)');
  body.addColorStop(0.82, 'rgba(255,240,140,0.98)');
  body.addColorStop(1.00, 'rgba(255,255,255,0.7)');
  ctx.fillStyle = body;
  ctx.fill();
  flamePath(ctx, cx + lean * 0.06, top + 70, bot - 55, hw * 0.34);
  const core = ctx.createLinearGradient(cx, bot - 50, cx, top + 40);
  core.addColorStop(0.00, 'rgba(255,200,70,0.95)');
  core.addColorStop(0.55, 'rgba(255,255,210,1)');
  core.addColorStop(1.00, 'rgba(255,255,255,0.9)');
  ctx.fillStyle = core;
  ctx.fill();
  const tip = ctx.createRadialGradient(cx + lean * 0.2, top + 55, 2, cx + lean * 0.2, top + 70, 55);
  tip.addColorStop(0.00, 'rgba(255,255,255,0.85)');
  tip.addColorStop(0.4, 'rgba(255,235,150,0.4)');
  tip.addColorStop(1.00, 'rgba(255,120,0,0)');
  ctx.fillStyle = tip;
  ctx.beginPath();
  ctx.ellipse(cx + lean * 0.2, top + 65, 28, 50, 0, 0, Math.PI * 2);
  ctx.fill();
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.minFilter = THREE.LinearFilter;
  tex.magFilter = THREE.LinearFilter;
  tex.generateMipmaps = false;
  tex.needsUpdate = true;
  return tex;
}

''' + text[end:]

# Dense white flash orb
repl(
    """function makeWhiteFlashTex() {
  const c = document.createElement('canvas');
  c.width = c.height = 96;
  const ctx = c.getContext('2d');
  const g = ctx.createRadialGradient(48, 48, 1, 48, 48, 46);
  g.addColorStop(0.00, 'rgba(255,255,255,1)');
  g.addColorStop(0.25, 'rgba(255,255,255,0.75)');
  g.addColorStop(0.55, 'rgba(230,245,255,0.25)');
  g.addColorStop(1.00, 'rgba(200,230,255,0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 96, 96);""",
    """function makeWhiteFlashTex() {
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const ctx = c.getContext('2d');
  const g = ctx.createRadialGradient(64, 64, 1, 64, 64, 62);
  g.addColorStop(0.00, 'rgba(255,255,255,1)');
  g.addColorStop(0.12, 'rgba(255,255,255,1)');
  g.addColorStop(0.32, 'rgba(255,252,245,0.85)');
  g.addColorStop(0.55, 'rgba(230,245,255,0.45)');
  g.addColorStop(1.00, 'rgba(200,230,255,0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 128, 128);""",
    "white flash tex",
)

# Dense white streak — thick glowing bolt sprite
repl(
    """function makeWhiteStreakTex(seed) {
  const rnd = seeded(seed * 47 + 3);
  const w = 48, h = 280;
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  const ctx = c.getContext('2d');
  const cx = w * 0.5;
  /* Jagged white lightning streak sprite. */
  ctx.strokeStyle = 'rgba(255,255,255,0.95)';
  ctx.lineWidth = 2.4;
  ctx.lineJoin = 'miter';
  ctx.beginPath();
  let x = cx + (rnd() - 0.5) * 4;
  ctx.moveTo(x, h - 4);
  const steps = 9 + ((rnd() * 4) | 0);
  for (let i = 1; i <= steps; i++) {
    const u = i / steps;
    x += (rnd() - 0.5) * 18;
    x = Math.max(6, Math.min(w - 6, x));
    ctx.lineTo(x, h - 4 - u * (h - 10));
  }
  ctx.stroke();
  ctx.strokeStyle = 'rgba(255,255,255,0.45)';
  ctx.lineWidth = 6;
  ctx.stroke();
  const bloom = ctx.createRadialGradient(cx, h * 0.35, 1, cx, h * 0.35, 16);
  bloom.addColorStop(0, 'rgba(255,255,255,0.95)');
  bloom.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = bloom;
  ctx.beginPath();
  ctx.arc(cx, h * 0.35, 16, 0, Math.PI * 2);
  ctx.fill();""",
    """function makeWhiteStreakTex(seed) {
  const rnd = seeded(seed * 47 + 3);
  const w = 96, h = 320;
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  const ctx = c.getContext('2d');
  const cx = w * 0.5;
  /* Dense thick white lightning ribbon + glow. */
  const pts = [];
  let x = cx + (rnd() - 0.5) * 6;
  pts.push([x, h - 6]);
  const steps = 8 + ((rnd() * 4) | 0);
  for (let i = 1; i <= steps; i++) {
    const u = i / steps;
    x += (rnd() - 0.5) * 22;
    x = Math.max(14, Math.min(w - 14, x));
    pts.push([x, h - 6 - u * (h - 14)]);
  }
  ctx.lineJoin = 'round';
  ctx.lineCap = 'round';
  ctx.strokeStyle = 'rgba(255,255,255,0.35)';
  ctx.lineWidth = 22;
  ctx.beginPath();
  ctx.moveTo(pts[0][0], pts[0][1]);
  for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
  ctx.stroke();
  ctx.strokeStyle = 'rgba(255,255,255,0.7)';
  ctx.lineWidth = 11;
  ctx.stroke();
  ctx.strokeStyle = 'rgba(255,255,255,1)';
  ctx.lineWidth = 4.5;
  ctx.stroke();
  const bloom = ctx.createRadialGradient(cx, h * 0.32, 2, cx, h * 0.32, 28);
  bloom.addColorStop(0, 'rgba(255,255,255,1)');
  bloom.addColorStop(0.4, 'rgba(255,255,255,0.55)');
  bloom.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = bloom;
  ctx.beginPath();
  ctx.arc(cx, h * 0.32, 28, 0, Math.PI * 2);
  ctx.fill();""",
    "white streak tex",
)

# Flame material soft additive
repl(
    """            alphaTest: 0.04,
            depthWrite: false,
            depthTest: false,
            toneMapped: false,
            sizeAttenuation: true,
            blending: THREE.NormalBlending,""",
    """            alphaTest: 0.02,
            depthWrite: false,
            depthTest: false,
            toneMapped: false,
            sizeAttenuation: true,
            blending: THREE.AdditiveBlending,""",
    "flame additive",
)

# More dense white flashes — mostly thick orbs + thick streaks
repl(
    """    for (let i = 0; i < 14; i++) {
      const rnd = seeded(4400 + i * 17);
      const isStreak = i >= 3;""",
    """    for (let i = 0; i < 22; i++) {
      const rnd = seeded(4400 + i * 17);
      const isStreak = i >= 10;""",
    "flash count",
)

repl(
    """        size: isStreak ? (2.8 + rnd() * 2.0) : (1.15 + rnd() * 1.1),""",
    """        size: isStreak ? (3.4 + rnd() * 2.6) : (1.8 + rnd() * 2.2),
        reach: 1.6 + rnd() * 4.2,""",
    "flash sizes",
)

# Fix duplicate reach if we added reach twice - check flash push object
# The signFlashes.push already has reach — need to check
if "reach: 2.2 + rnd() * 3.8,\n        size: isStreak ? (3.4" in text or "reach: 1.6" in text:
    # might have duplicated reach field
    text2 = text.replace(
        """        reach: 2.2 + rnd() * 3.8,
        size: isStreak ? (3.4 + rnd() * 2.6) : (1.8 + rnd() * 2.2),
        reach: 1.6 + rnd() * 4.2,""",
        """        reach: 1.6 + rnd() * 4.2,
        size: isStreak ? (3.4 + rnd() * 2.6) : (1.8 + rnd() * 2.2),""",
        1,
    )
    if text2 != text:
        text = text2
        print("ok dedupe reach")
    else:
        # only size was replaced, reach still old
        text = text.replace(
            """        reach: 2.2 + rnd() * 3.8,
        size: isStreak ? (3.4 + rnd() * 2.6) : (1.8 + rnd() * 2.2),
        reach: 1.6 + rnd() * 4.2,""",
            """        reach: 1.6 + rnd() * 4.2,
        size: isStreak ? (3.4 + rnd() * 2.6) : (1.8 + rnd() * 2.2),""",
            1,
        )

# Thicker bolts
repl(
    """  const thick = SIGN_ONLY
    ? (0.055 + rnd() * 0.04) * thickScale
    : (0.16 + rnd() * 0.18) * thickScale;
  bolt.glow.geometry.dispose();
  bolt.core.geometry.dispose();
  bolt.glow.geometry = new THREE.TubeGeometry(curve, SIGN_ONLY ? 18 : 16, thick * (SIGN_ONLY ? 2.8 : 2.4), SIGN_ONLY ? 5 : 4, false);
  bolt.core.geometry = new THREE.TubeGeometry(curve, SIGN_ONLY ? 18 : 16, thick, SIGN_ONLY ? 4 : 3, false);""",
    """  const thick = SIGN_ONLY
    ? (0.11 + rnd() * 0.07) * thickScale
    : (0.16 + rnd() * 0.18) * thickScale;
  bolt.glow.geometry.dispose();
  bolt.core.geometry.dispose();
  bolt.glow.geometry = new THREE.TubeGeometry(curve, SIGN_ONLY ? 18 : 16, thick * (SIGN_ONLY ? 3.2 : 2.4), SIGN_ONLY ? 6 : 4, false);
  bolt.core.geometry = new THREE.TubeGeometry(curve, SIGN_ONLY ? 18 : 16, thick, SIGN_ONLY ? 5 : 3, false);""",
    "bolt thick",
)

path.write_text(text, encoding="utf-8")
print("part1 done")
