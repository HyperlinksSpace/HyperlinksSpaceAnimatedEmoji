"""
Telegram-style premium emoji (video WEBM path):
Official TGS/Lottie is vector-only (no photo shards, no AE 3D layers).
For this glossy brand art we use the supported WEBM path with a gift-like
true-3D Blender scene:

  • ONE intact logo (never fragmented)
  • Real mesh crystals/spikes for the boom (not cutouts)
  • Camera moves for "zoom N" and "diagonal text" beats
  • Tight framing (logo fills the emoji)
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


def trap(t, up0, up1, down0, down1):
    if t <= up0 or t >= down1:
        return 0.0
    if t < up1:
        u = (t - up0) / max(1e-6, up1 - up0)
        return u * u * (3 - 2 * u)
    if t < down0:
        return 1.0
    u = (t - down0) / max(1e-6, down1 - down0)
    return 1.0 - (u * u * (3 - 2 * u))


def emission_mat(name, color, strength=1.4, metal=0.35):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Roughness"].default_value = 0.15
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = 1.0
        bsdf.inputs["Coat Roughness"].default_value = 0.05
    if "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = (*color, 1)
        bsdf.inputs["Emission Strength"].default_value = strength
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat, bsdf


def hero_mat(img):
    mat = bpy.data.materials.new("HeroMat")
    mat.use_nodes = True
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Cubic"
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    bsdf.inputs["Metallic"].default_value = 0.12
    bsdf.inputs["Roughness"].default_value = 0.28
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = 0.85
        bsdf.inputs["Coat Roughness"].default_value = 0.08
    if "Emission Color" in bsdf.inputs:
        links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 1.05
    trans = nodes.new("ShaderNodeBsdfTransparent")
    mix = nodes.new("ShaderNodeMixShader")
    links.new(tex.outputs["Alpha"], mix.inputs["Fac"])
    links.new(trans.outputs["BSDF"], mix.inputs[1])
    links.new(bsdf.outputs["BSDF"], mix.inputs[2])
    links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return mat, bsdf


def add_hero():
    img = bpy.data.images.load(str(HERO), check_existing=True)
    img.alpha_mode = "CHANNEL_PACKED"
    img.colorspace_settings.name = "sRGB"
    # Fill frame tightly — plane size ~2.15 in ortho-ish framing
    bpy.ops.mesh.primitive_plane_add(size=2.28, location=(0, 0.02, 0.35))
    hero = bpy.context.active_object
    hero.name = "HeroLogo"
    sol = hero.modifiers.new("Solidify", "SOLIDIFY")
    sol.thickness = 0.08
    sol.offset = 0.0
    bev = hero.modifiers.new("Bevel", "BEVEL")
    bev.width = 0.012
    bev.segments = 4
    mat, bsdf = hero_mat(img)
    hero.data.materials.append(mat)
    hero["bsdf"] = mat.name
    return hero, bsdf


def add_crystals(parent):
    """True 3D gift-style crystals — not photo fragments."""
    colors = [
        (1.0, 0.15, 0.55),  # magenta
        (1.0, 0.92, 0.05),  # yellow
        (0.05, 0.95, 1.0),  # cyan
        (0.45, 1.0, 0.12),  # lime
        (1.0, 0.35, 0.05),  # orange
        (1.0, 0.2, 0.35),   # hot pink
    ]
    group = bpy.data.objects.new("CrystalBoom", None)
    bpy.context.collection.objects.link(group)
    group.parent = parent
    crystals = []
    n = 28
    for i in range(n):
        ang = (i / n) * math.tau + (i % 3) * 0.07
        # Sit behind / around logo rim
        r = 1.05 + (i % 4) * 0.09
        x = math.cos(ang) * r
        y = math.sin(ang) * r * 0.92
        z = -0.15 - (i % 3) * 0.05
        bpy.ops.mesh.primitive_cone_add(
            vertices=5 + (i % 3),
            radius1=0.085 + (i % 4) * 0.018,
            depth=0.62 + (i % 5) * 0.09,
            location=(x, y, z),
        )
        cr = bpy.context.active_object
        cr.name = f"crystal_{i:02d}"
        # Point outward
        direction = Vector((x, y, 0.05))
        cr.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
        col = colors[i % len(colors)]
        mat, bsdf = emission_mat(f"cry_mat_{i}", col, strength=1.6)
        cr.data.materials.append(mat)
        cr.parent = group
        cr["rest_loc"] = list(cr.location)
        cr["rest_rot"] = list(cr.rotation_euler)
        cr["rest_scale"] = list(cr.scale)
        cr["ang"] = ang
        cr["r"] = r
        cr["power"] = 0.55 + 0.7 * ((i * 37) % 100) / 100.0
        cr["spin"] = (-1 if i % 2 == 0 else 1) * (0.5 + 0.6 * ((i * 17) % 100) / 100.0)
        cr["mat_name"] = mat.name
        cr["delay"] = 0.01 * (i % 6)
        crystals.append(cr)
    return group, crystals


def lights():
    world = bpy.data.worlds.new("World") if "World" not in bpy.data.worlds else bpy.data.worlds["World"]
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0, 0, 0, 1)
        bg.inputs[1].default_value = 0.0

    def add(name, typ, loc, energy, color):
        data = bpy.data.lights.new(name, typ)
        data.energy = energy
        data.color = color
        if typ == "AREA":
            data.size = 2.2
        ob = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(ob)
        ob.location = loc
        return ob

    add("Key", "AREA", (2.0, 2.2, 3.2), 220, (1, 0.98, 0.95))
    add("Fill", "AREA", (-2.2, 0.3, 1.8), 80, (0.55, 0.8, 1.0))
    add("Rim", "AREA", (0.1, -2.4, 1.4), 140, (1.0, 0.35, 0.7))
    return add("Neon", "POINT", (0.0, 0.5, 1.2), 55, (0.35, 1.0, 0.25))


def camera():
    data = bpy.data.cameras.new("Cam")
    data.lens = 55
    cam = bpy.data.objects.new("Cam", data)
    bpy.context.collection.objects.link(cam)
    # Close framing — logo fills ~90%+ of the emoji
    cam.location = (0, 0, 3.12)
    bpy.context.scene.camera = cam
    return cam


def animate(root, hero, crystals, cam, neon):
    sc = bpy.context.scene
    sc.frame_start = 1
    sc.frame_end = TOTAL
    sc.render.fps = FPS

    # Rest camera aim: center. Zoom-N aim. Diagonal text aim.
    # Look-at approximated by cam location + slight rotation
    for fr in range(1, TOTAL + 1):
        t = (fr - 1) / TOTAL
        explode = trap(t, 0.00, 0.15, 0.64, 0.88)
        zoom_n = trap(t, 0.18, 0.34, 0.66, 0.90)
        zoom_text = trap(t, 0.38, 0.54, 0.70, 0.94)

        # --- Intact logo: subtle 3D presence, never fragmented ---
        # During N zoom: bring logo forward + slight tilt to feature sign
        # During text zoom: diagonal pose
        hero_z = 0.35 + 0.25 * zoom_n + 0.35 * zoom_text
        hero_s = 1.0 + 0.06 * zoom_n + 0.10 * zoom_text
        hero.location = (
            0.12 * zoom_text,
            0.10 * zoom_n - 0.14 * zoom_text,
            hero_z,
        )
        hero.scale = (hero_s, hero_s, 1.0)
        hero.rotation_euler = Euler(
            (
                -0.08 * zoom_n + 0.12 * zoom_text,
                0.10 * zoom_n - 0.16 * zoom_text,
                0.18 * zoom_text,
            ),
            "XYZ",
        )
        hero.keyframe_insert("location", frame=fr)
        hero.keyframe_insert("scale", frame=fr)
        hero.keyframe_insert("rotation_euler", frame=fr)

        # Logo emission punch
        mat = bpy.data.materials.get(hero["bsdf"])
        if mat:
            bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if bsdf and "Emission Strength" in bsdf.inputs:
                bsdf.inputs["Emission Strength"].default_value = (
                    1.05 + 0.55 * zoom_n + 0.45 * zoom_text + 0.25 * explode
                )
                bsdf.inputs["Emission Strength"].keyframe_insert("default_value", frame=fr)

        # --- True 3D crystal boom ---
        for cr in crystals:
            d = cr["delay"]
            e = trap(t, 0.00 + d, 0.15 + d, 0.64, 0.88)
            rest = Vector(cr["rest_loc"])
            ang = cr["ang"]
            fly = e * cr["power"] * 0.85
            # Outward + Z pop (true depth)
            cr.location = (
                rest.x + math.cos(ang) * fly,
                rest.y + math.sin(ang) * fly,
                rest.z + e * (0.35 + 0.55 * cr["power"]),
            )
            sca = 1.0 + e * (0.45 + 0.65 * cr["power"])
            cr.scale = (sca, sca, sca)
            rr = Vector(cr["rest_rot"])
            cr.rotation_euler = Euler(
                (
                    rr.x + e * cr["spin"] * 1.4,
                    rr.y + e * cr["spin"] * 0.9,
                    rr.z + e * cr["spin"] * 1.8,
                ),
                "XYZ",
            )
            cr.keyframe_insert("location", frame=fr)
            cr.keyframe_insert("scale", frame=fr)
            cr.keyframe_insert("rotation_euler", frame=fr)

            # Color / glow animation on crystals
            mat = bpy.data.materials.get(cr["mat_name"])
            if mat:
                bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
                if bsdf and "Emission Strength" in bsdf.inputs:
                    bsdf.inputs["Emission Strength"].default_value = 1.2 + 2.2 * e
                    bsdf.inputs["Emission Strength"].keyframe_insert("default_value", frame=fr)
                if bsdf and "Roughness" in bsdf.inputs:
                    bsdf.inputs["Roughness"].default_value = 0.18 - 0.08 * e
                    bsdf.inputs["Roughness"].keyframe_insert("default_value", frame=fr)

        # Close shot; pull back for boom + zooms so nothing clips
        pull = 3.12 + 0.22 * explode + 0.30 * zoom_n + 0.45 * zoom_text
        cam.location = (
            0.14 * zoom_text,
            0.18 * zoom_n - 0.16 * zoom_text,
            pull,
        )
        cam.rotation_euler = Euler(
            (
                -0.06 * zoom_n + 0.08 * zoom_text,
                0.05 * zoom_text,
                0.10 * zoom_text,
            ),
            "XYZ",
        )
        cam.keyframe_insert("location", frame=fr)
        cam.keyframe_insert("rotation_euler", frame=fr)

        if neon:
            neon.data.energy = 40 + 80 * zoom_n + 50 * explode + 40 * zoom_text
            neon.data.keyframe_insert("energy", frame=fr)

        # Root micro-turn for AAA depth read (logo + crystals together)
        root.rotation_euler = Euler(
            (0.03 * explode, 0.04 * explode + 0.05 * zoom_text, 0.02 * zoom_n),
            "XYZ",
        )
        root.keyframe_insert("rotation_euler", frame=fr)


def configure_render():
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 28
    sc.cycles.use_denoising = True
    sc.render.resolution_x = RES
    sc.render.resolution_y = RES
    sc.render.fps = FPS
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.film_transparent = True
    sc.render.filepath = str(FRAMES / "frame_")
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.08
    print("Premium 3D boom | tight frame | intact logo + mesh crystals")


def build():
    if not HERO.exists():
        raise SystemExit(f"Missing {HERO}")
    clear()
    neon = lights()
    cam = camera()
    root = bpy.data.objects.new("Root", None)
    bpy.context.collection.objects.link(root)

    hero, _ = add_hero()
    hero.parent = root
    _, crystals = add_crystals(root)

    animate(root, hero, crystals, cam, neon)
    configure_render()
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "hyperlinks_premium_3d.blend"))

    FRAMES.mkdir(exist_ok=True)
    for p in FRAMES.glob("*.png"):
        p.unlink()
    bpy.ops.render.render(animation=True)
    print("Done", FRAMES)


if __name__ == "__main__":
    build()
