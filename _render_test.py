"""
Blender 5 — pixel-perfect layered 3D reconstruction + AAA loop for Telegram WEBM.

Layers are a disjoint partition of the source art; at rest they rebuild the logo.
Animation adds parallax / spin / pulse without changing the brand look.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import bpy
from mathutils import Euler, Vector

ROOT = Path(r"c:\1\1\1\1\1\HyperlinksSpaceAnimatedEmoji")
LAYERS = ROOT / "layers"
FRAMES = ROOT / "render_frames"
META = json.loads((LAYERS / "meta.json").read_text(encoding="utf-8"))

FPS = 30
TOTAL = 1  # color check
RES = 512


def clear():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.curves, bpy.data.lights):
        for b in list(coll):
            coll.remove(b)


def load_img(path: Path):
    img = bpy.data.images.load(str(path), check_existing=True)
    img.alpha_mode = "CHANNEL_PACKED"
    img.colorspace_settings.name = "sRGB"
    return img


def make_mat(name, img, emission=1.0):
    """
    Source art is already lit/composited. Display it via Emission so colors
    stay neon-bright (Principled+lights+AgX was washing them to pastel).
    """
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    else:
        mat.blend_method = "HASHED"
    mat.use_backface_culling = False
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Closest"  # keep graffiti edges crisp
    # Keep authored sRGB values; do not re-light
    emis = nodes.new("ShaderNodeEmission")
    emis.inputs["Strength"].default_value = max(emission, 1.0)
    links.new(tex.outputs["Color"], emis.inputs["Color"])

    # Transparent where alpha is low
    transparent = nodes.new("ShaderNodeBsdfTransparent")
    mix = nodes.new("ShaderNodeMixShader")
    links.new(tex.outputs["Alpha"], mix.inputs["Fac"])
    links.new(transparent.outputs["BSDF"], mix.inputs[1])
    links.new(emis.outputs["Emission"], mix.inputs[2])
    links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return mat


def add_card(meta, z, depth, emission):
    if not meta.get("bbox_norm"):
        return None
    path = LAYERS / meta["file"]
    if not path.exists():
        return None
    img = load_img(path)
    x0, y0, x1, y1 = meta["bbox_norm"]
    cx = (x0 + x1) * 0.5 * 2 - 1
    cy = 1 - (y0 + y1) * 0.5 * 2
    w = max((x1 - x0) * 2.0, 0.05)
    h = max((y1 - y0) * 2.0, 0.05)

    bpy.ops.mesh.primitive_plane_add(size=1, location=(cx, cy, z))
    obj = bpy.context.active_object
    obj.name = meta["name"]
    obj.scale = (w, h, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    solid = obj.modifiers.new("Solidify", "SOLIDIFY")
    solid.thickness = depth
    solid.offset = 1.0  # extrude backward so face stays at z

    # Bevel lightly — heavy bevel + lighting was milking saturation
    bevel = obj.modifiers.new("Bevel", "BEVEL")
    bevel.width = min(0.006, depth * 0.12)
    bevel.segments = 2

    obj.data.materials.append(make_mat(meta["name"] + "_mat", img, emission))
    obj["hl"] = meta["name"]
    # Store rest pose
    obj["rest_loc"] = list(obj.location)
    obj["rest_scale"] = list(obj.scale)
    return obj


def lights():
    # Keep scene dark — cards are emissive; a tiny rim only for side thickness
    world = bpy.data.worlds.new("World") if "World" not in bpy.data.worlds else bpy.data.worlds["World"]
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0, 0, 0, 1)
        bg.inputs[1].default_value = 0.0

    data = bpy.data.lights.new("RimSoft", "AREA")
    data.energy = 15
    data.color = (1.0, 1.0, 1.0)
    data.size = 3.0
    ob = bpy.data.objects.new("RimSoft", data)
    bpy.context.collection.objects.link(ob)
    ob.location = (0.0, -2.5, 1.2)

    neon = bpy.data.lights.new("Neon", "POINT")
    neon.energy = 0.0  # pulse driven in animate(); base off so colors stay pure
    neon.color = (0.45, 1.0, 0.3)
    nob = bpy.data.objects.new("Neon", neon)
    bpy.context.collection.objects.link(nob)
    nob.location = (0.0, 0.65, 1.4)


def camera():
    data = bpy.data.cameras.new("Cam")
    data.lens = 55
    cam = bpy.data.objects.new("Cam", data)
    bpy.context.collection.objects.link(cam)
    cam.location = (0, 0, 4.35)
    bpy.context.scene.camera = cam
    return cam


def animate(root, cards, cam):
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = TOTAL
    scene.render.fps = FPS

    motion = {
        "00_spikes": (0.10, 0.55, 0.08, 0.05),   # zAmp, spinZ, tilt, scale
        "01_red_squiggle": (0.14, -0.25, 0.18, 0.04),
        "02_black_squiggle": (0.12, 0.22, 0.15, 0.04),
        "03_green_swoop": (0.13, -0.18, 0.16, 0.05),
        "04_red_sphere": (0.20, 0.40, 0.22, 0.14),
        "05_letter_n": (0.12, 0.10, 0.14, 0.05),
        "06_text": (0.10, -0.06, 0.10, 0.03),
        "08_rest": (0.06, 0.08, 0.06, 0.02),
    }

    for fr in range(1, TOTAL + 1):
        t = (fr - 1) / TOTAL
        # Root breath
        s = 1.0 + 0.035 * math.sin(t * math.tau)
        root.scale = (s, s, s)
        root.keyframe_insert("scale", frame=fr)
        root.rotation_euler = Euler(
            (0.04 * math.sin(t * math.tau + 0.4), 0.10 * math.sin(t * math.tau), 0.03 * math.cos(t * math.tau)),
            "XYZ",
        )
        root.keyframe_insert("rotation_euler", frame=fr)

        for obj in cards:
            name = obj.get("hl", obj.name)
            zamp, spin, tilt, sca = motion.get(name, (0.08, 0.1, 0.08, 0.03))
            rest = Vector(obj["rest_loc"])
            # Parallax offset — returns to rest at t=0 and t=1
            obj.location = (
                rest.x + zamp * 0.25 * math.sin(t * math.tau),
                rest.y + zamp * 0.20 * math.cos(t * math.tau),
                rest.z + zamp * math.sin(t * math.tau + 0.7),
            )
            obj.keyframe_insert("location", frame=fr)
            obj.rotation_euler = Euler(
                (
                    tilt * math.sin(t * math.tau + 0.3),
                    tilt * 1.1 * math.sin(t * math.tau),
                    spin * math.sin(t * math.tau),
                ),
                "XYZ",
            )
            # Spikes get continuous spin component that loops (0.55 * sin is loop-safe;
            # for continuous spin use full turns that land on identity)
            if name == "00_spikes":
                obj.rotation_euler.z = t * math.tau * 0.25  # 90deg over loop — not identity!
                # Fix: use sin-based wobble only for perfect loop
                obj.rotation_euler.z = 0.35 * math.sin(t * math.tau)
            obj.keyframe_insert("rotation_euler", frame=fr)
            sc = 1.0 + sca * math.sin(t * math.tau + 0.5)
            obj.scale = (sc, sc, 1.0)
            obj.keyframe_insert("scale", frame=fr)

        # Camera
        cam.location = (
            0.28 * math.sin(t * math.tau),
            0.10 * math.cos(t * math.tau),
            4.30 + 0.06 * math.sin(t * math.tau * 2),
        )
        cam.keyframe_insert("location", frame=fr)
        cam.rotation_euler = Euler((-0.015 * math.sin(t * math.tau), 0.035 * math.sin(t * math.tau), 0), "XYZ")
        cam.keyframe_insert("rotation_euler", frame=fr)

        neon = bpy.data.objects.get("Neon")
        if neon:
            # Subtle pulse only — do not blow out palette
            neon.data.energy = 8 + 12 * (0.5 + 0.5 * math.sin(t * math.tau))
            neon.data.keyframe_insert("energy", frame=fr)

    # Force cyclic-friendly handles (Blender 5 action API differs)
    for ob in list(cards) + [root, cam]:
        ad = ob.animation_data
        if not ad or not ad.action:
            continue
        action = ad.action
        fcurves = getattr(action, "fcurves", None)
        if fcurves is None:
            # Blender 5 layered actions
            try:
                for layer in action.layers:
                    for strip in layer.strips:
                        ch = getattr(strip, "channelbag", None) or getattr(strip, "channelbags", [None])[0]
                        if ch is None:
                            continue
                        fcurves = getattr(ch, "fcurves", [])
                        for fc in fcurves:
                            for kp in fc.keyframe_points:
                                kp.interpolation = "BEZIER"
                                kp.handle_left_type = "AUTO_CLAMPED"
                                kp.handle_right_type = "AUTO_CLAMPED"
            except Exception as e:
                print("skip fcurve polish:", e)
            continue
        for fc in fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"
                kp.handle_left_type = "AUTO_CLAMPED"
                kp.handle_right_type = "AUTO_CLAMPED"


def configure_render():
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 24
    sc.cycles.use_denoising = True
    sc.render.resolution_x = RES
    sc.render.resolution_y = RES
    sc.render.fps = FPS
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.image_settings.color_depth = "8"
    sc.render.film_transparent = True
    sc.render.filepath = str(FRAMES / "frame_")

    # CRITICAL: AgX/Filmic was crushing neon → pastel. Use Standard.
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0
    sc.display_settings.display_device = "sRGB"
    sc.sequencer_colorspace_settings.name = "sRGB"

    # Mild compositor punch (saturation + contrast) without crushing blacks
    sc.use_nodes = True
    tree = sc.node_tree
    tree.nodes.clear()
    rl = tree.nodes.new("CompositorNodeRLayers")
    bright = tree.nodes.new("CompositorNodeBrightContrast")
    bright.inputs["Bright"].default_value = 0.02
    bright.inputs["Contrast"].default_value = 0.08
    sat = tree.nodes.new("CompositorNodeHueSat")
    sat.inputs["Saturation"].default_value = 1.18
    sat.inputs["Value"].default_value = 1.06
    comp = tree.nodes.new("CompositorNodeComposite")
    links = tree.links
    links.new(rl.outputs["Image"], bright.inputs["Image"])
    links.new(bright.outputs["Image"], sat.inputs["Image"])
    links.new(sat.outputs["Image"], comp.inputs["Image"])

    print("Render engine:", sc.render.engine, "| view_transform:", sc.view_settings.view_transform)


def build():
    clear()
    lights()
    cam = camera()

    root = bpy.data.objects.new("Root", None)
    bpy.context.collection.objects.link(root)

    by = {m["name"]: m for m in META["layers"]}
    stack = [
        # name, z, depth, emission strength (1.0 = original color)
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

    animate(root, cards, cam)
    configure_render()

    blend = ROOT / "hyperlinks_space_emoji.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    print("Saved", blend)

    FRAMES.mkdir(exist_ok=True)
    for p in FRAMES.glob("*.png"):
        p.unlink()

    bpy.context.scene.frame_set(1)
bpy.ops.render.render(write_still=True)
print("TEST_FRAME", bpy.context.scene.render.filepath)

    print("Done frames ->", FRAMES)


if __name__ == "__main__":
    build()
