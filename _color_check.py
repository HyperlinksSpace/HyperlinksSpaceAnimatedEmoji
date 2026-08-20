"""One-frame color check with the bright emission materials."""
from pathlib import Path
import bpy

ROOT = Path(r"c:\1\1\1\1\1\HyperlinksSpaceAnimatedEmoji")
ns = {}
exec((ROOT / "build_blender_scene.py").read_text(encoding="utf-8"), ns)

# Patch TOTAL before build pieces run — call internals manually
clear = ns["clear"]
lights = ns["lights"]
camera = ns["camera"]
add_card = ns["add_card"]
animate = ns["animate"]
configure_render = ns["configure_render"]
META = ns["META"]
FRAMES = ns["FRAMES"]
ROOT = ns["ROOT"]

# Force 1-frame loop for quick check
ns["TOTAL"] = 1
# Also patch module-level TOTAL used inside animate via closure — animate reads TOTAL from global in ns
import types

# Re-bind TOTAL in the executed namespace and wrap animate
TOTAL = 1

def animate_one(root, cards, cam):
    # Use original animate but scene range 1..1
    sc = bpy.context.scene
    sc.frame_start = 1
    sc.frame_end = 1
    # Call original with patched global
    g = dict(ns)
    g["TOTAL"] = 1
    exec(
        "def _a(root, cards, cam):\n"
        + "\n".join(
            "    " + line if line else ""
            for line in ns["animate"].__code__  # can't easily
        ),
        g,
    )

clear()
lights()
cam = camera()
root = bpy.data.objects.new("Root", None)
bpy.context.collection.objects.link(root)
by = {m["name"]: m for m in META["layers"]}
stack = [
    ("08_rest", -0.40, 0.035, 1.05),
    ("00_spikes", -0.28, 0.05, 1.25),
    ("01_red_squiggle", -0.16, 0.06, 1.2),
    ("02_black_squiggle", -0.12, 0.055, 1.0),
    ("03_green_swoop", -0.06, 0.06, 1.3),
    ("05_letter_n", 0.06, 0.09, 1.45),
    ("06_text", 0.20, 0.1, 1.15),
    ("04_red_sphere", 0.32, 0.09, 1.5),
]
cards = []
for name, z, depth, emission in stack:
    meta = by.get(name)
    if not meta:
        continue
    ob = add_card(meta, z, depth, emission)
    if ob:
        ob.parent = root
        cards.append(ob)

# Minimal rest pose keyframe
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 1
configure_render()
bpy.context.scene.render.filepath = str(ROOT / "color_check")
bpy.ops.render.render(write_still=True)
print("WROTE", ROOT / "color_check.png")
