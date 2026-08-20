"""
Exact-reference Telegram emoji/sticker render.

The logo art is the original image (pixel-identical). AAA motion comes from
3D camera/object animation + outer accents that never cover the art at rest.
"""
from __future__ import annotations

import math
import os
from pathlib import Path

import bpy
from mathutils import Euler, Vector

ROOT = Path(r"c:\1\1\1\1\1\HyperlinksSpaceAnimatedEmoji")
HERO = ROOT / "layers" / "hero_square.png"
FRAMES = ROOT / "render_frames"
FPS = 30
TOTAL = int(os.environ.get("HL_FRAMES", "90"))
RES = 512


def clear():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.lights):
        for b in list(coll):
            coll.remove(b)


def emission_image_mat(name: str, img, strength=1.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Closest"
    emis = nodes.new("ShaderNodeEmission")
    emis.inputs["Strength"].default_value = strength
    links.new(tex.outputs["Color"], emis.inputs["Color"])
    trans = nodes.new("ShaderNodeBsdfTransparent")
    mix = nodes.new("ShaderNodeMixShader")
    links.new(tex.outputs["Alpha"], mix.inputs["Fac"])
    links.new(trans.outputs["BSDF"], mix.inputs[1])
    links.new(emis.outputs["Emission"], mix.inputs[2])
    links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return mat


def solid_emission_mat(name, color, strength=1.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    emis = nodes.new("ShaderNodeEmission")
    emis.inputs["Color"].default_value = (*color, 1)
    emis.inputs["Strength"].default_value = strength
    links.new(emis.outputs["Emission"], out.inputs["Surface"])
    return mat


def setup_world():
    world = bpy.data.worlds.new("World") if "World" not in bpy.data.worlds else bpy.data.worlds["World"]
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0, 0, 0, 1)
        bg.inputs[1].default_value = 0.0


def add_hero():
    img = bpy.data.images.load(str(HERO), check_existing=True)
    img.alpha_mode = "CHANNEL_PACKED"
    img.colorspace_settings.name = "sRGB"

    # Exact square plane — texture maps 1:1 to hero_square.png
    bpy.ops.mesh.primitive_plane_add(size=2.0, location=(0, 0, 0))
    hero = bpy.context.active_object
    hero.name = "HeroLogo"
    hero.data.materials.append(emission_image_mat("HeroMat", img, strength=1.0))

    # Thin dark backplate for edge thickness when tilted (does not change front pixels)
    bpy.ops.mesh.primitive_plane_add(size=2.0, location=(0, 0, -0.035))
    back = bpy.context.active_object
    back.name = "HeroBack"
    back.scale = (0.995, 0.995, 1)
    back.data.materials.append(solid_emission_mat("BackMat", (0.02, 0.02, 0.02), 1.0))
    return hero, back


def add_outer_accents(parent):
    """Accents orbit OUTSIDE the logo silhouette — never cover the reference art."""
    colors = [
        (1.0, 0.9, 0.05),
        (1.0, 0.15, 0.55),
        (0.05, 0.95, 1.0),
        (0.45, 1.0, 0.1),
        (1.0, 0.35, 0.08),
    ]
    ring = bpy.data.objects.new("AccentRing", None)
    bpy.context.collection.objects.link(ring)
    ring.parent = parent

    for i in range(16):
        ang = (i / 16) * math.tau
        # Outside hero square (hero half-extent ≈ 1.0)
        r = 1.28 + (i % 3) * 0.06
        bpy.ops.mesh.primitive_cone_add(
            vertices=4,
            radius1=0.045,
            depth=0.28,
            location=(math.cos(ang) * r, math.sin(ang) * r, -0.08),
        )
        sp = bpy.context.active_object
        sp.name = f"accent_{i:02d}"
        direction = Vector((math.cos(ang), math.sin(ang), 0))
        sp.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
        sp.data.materials.append(solid_emission_mat(f"acc_mat_{i}", colors[i % len(colors)], 1.35))
        sp.parent = ring
        sp["base_ang"] = ang
        sp["base_r"] = r
    return ring


def add_camera():
    data = bpy.data.cameras.new("Cam")
    data.lens = 60
    cam = bpy.data.objects.new("Cam", data)
    bpy.context.collection.objects.link(cam)
    # Framed so the full hero fills the canvas like the reference
    cam.location = (0, 0, 3.55)
    bpy.context.scene.camera = cam
    return cam


def animate(root, hero, ring, cam):
    sc = bpy.context.scene
    sc.frame_start = 1
    sc.frame_end = TOTAL
    sc.render.fps = FPS

    for fr in range(1, TOTAL + 1):
        t = (fr - 1) / TOTAL
        # Seamless loop: all motion is sin/cos based
        breath = 1.0 + 0.03 * math.sin(t * math.tau)
        root.scale = (breath, breath, breath)
        root.keyframe_insert("scale", frame=fr)

        root.rotation_euler = Euler(
            (
                0.07 * math.sin(t * math.tau),
                0.14 * math.sin(t * math.tau + 0.2),
                0.05 * math.cos(t * math.tau),
            ),
            "XYZ",
        )
        root.keyframe_insert("rotation_euler", frame=fr)
        root.location.z = 0.03 * math.sin(t * math.tau)
        root.keyframe_insert("location", index=2, frame=fr)

        # Soft Z wobble on accents only
        if ring:
            ring.rotation_euler.z = 0.45 * math.sin(t * math.tau)
            ring.keyframe_insert("rotation_euler", index=2, frame=fr)
            for sp in ring.children:
                pop = 1.0 + 0.18 * math.sin(t * math.tau * 2 + sp.get("base_ang", 0))
                sp.scale = (pop, pop, pop)
                sp.keyframe_insert("scale", frame=fr)

        cam.location = (
            0.18 * math.sin(t * math.tau),
            0.08 * math.cos(t * math.tau),
            3.55 + 0.05 * math.sin(t * math.tau),
        )
        cam.keyframe_insert("location", frame=fr)
        cam.rotation_euler = Euler(
            (-0.012 * math.sin(t * math.tau), 0.025 * math.sin(t * math.tau), 0),
            "XYZ",
        )
        cam.keyframe_insert("rotation_euler", frame=fr)


def configure_render():
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 16  # emission-only: low samples are clean
    sc.cycles.use_denoising = False
    sc.render.resolution_x = RES
    sc.render.resolution_y = RES
    sc.render.fps = FPS
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.film_transparent = True
    sc.render.filepath = str(FRAMES / "frame_")
    # Exact color reproduction
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0
    sc.display_settings.display_device = "sRGB"
    print("view_transform=Standard emission=1.0 samples=", sc.cycles.samples)


def build():
    if not HERO.exists():
        raise SystemExit(f"Missing {HERO} — run segment_layers.py once for hero_square.png")

    clear()
    setup_world()
    cam = add_camera()

    root = bpy.data.objects.new("Root", None)
    bpy.context.collection.objects.link(root)

    hero, back = add_hero()
    hero.parent = root
    back.parent = root

    # Accents off by default for exact look; enable with HL_ACCENTS=1
    ring = None
    if os.environ.get("HL_ACCENTS", "0") == "1":
        ring = add_outer_accents(root)

    animate(root, hero, ring, cam)
    configure_render()

    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "hyperlinks_space_emoji.blend"))

    FRAMES.mkdir(exist_ok=True)
    if TOTAL <= 2:
        bpy.context.scene.render.filepath = str(ROOT / "color_check")
        bpy.ops.render.render(write_still=True)
        print("Wrote", ROOT / "color_check.png")
    else:
        for p in FRAMES.glob("*.png"):
            p.unlink()
        bpy.ops.render.render(animation=True)
        print("Done", FRAMES)


if __name__ == "__main__":
    build()
