"""
Blender 5 — true 3D Hyperlinks.SPACE boom sticker/emoji.

Pieces are textured 3D cards (solidify + bevel). Timeline:
  1) Shard explosion in 3D
  2) Sign (N) zooms toward camera
  3) Text zooms on diagonal
  4) Return home
Green flanks stay put. Color pulses on shards. Camera dolly prevents crop.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

import bpy
from mathutils import Euler, Vector

ROOT = Path(r"c:\1\1\1\1\1\HyperlinksSpaceAnimatedEmoji")
PIECES = ROOT / "boom_3d_pieces"
FRAMES = ROOT / "render_frames"
META = json.loads((PIECES / "meta.json").read_text(encoding="utf-8"))

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
    u = u * u * (3 - 2 * u)
    return 1.0 - u


def make_mat(name, img, emission=1.15):
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

    # Hue/sat for color animation (driven via keyframes on node)
    hsv = nodes.new("ShaderNodeHueSaturation")
    hsv.name = "HSV"
    hsv.inputs["Hue"].default_value = 0.5
    hsv.inputs["Saturation"].default_value = 1.15
    hsv.inputs["Value"].default_value = 1.05
    links.new(tex.outputs["Color"], hsv.inputs["Color"])

    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(hsv.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    bsdf.inputs["Metallic"].default_value = 0.25
    bsdf.inputs["Roughness"].default_value = 0.22
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = 1.0
        bsdf.inputs["Coat Roughness"].default_value = 0.06
    if "Emission Color" in bsdf.inputs:
        links.new(hsv.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = emission
    emis_str = bsdf.inputs.get("Emission Strength")
    transparent = nodes.new("ShaderNodeBsdfTransparent")
    mix = nodes.new("ShaderNodeMixShader")
    links.new(tex.outputs["Alpha"], mix.inputs["Fac"])
    links.new(transparent.outputs["BSDF"], mix.inputs[1])
    links.new(bsdf.outputs["BSDF"], mix.inputs[2])
    links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return mat, hsv, emis_str


def add_card(pinfo, z, depth=0.05):
    path = PIECES / pinfo["file"]
    img = bpy.data.images.load(str(path), check_existing=True)
    img.alpha_mode = "CHANNEL_PACKED"
    img.colorspace_settings.name = "sRGB"

    bpy.ops.mesh.primitive_plane_add(size=1, location=(pinfo["cx"], pinfo["cy"], z))
    obj = bpy.context.active_object
    obj.name = pinfo["file"]
    obj.scale = (max(pinfo["w"], 0.02), max(pinfo["h"], 0.02), 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    sol = obj.modifiers.new("Solidify", "SOLIDIFY")
    sol.thickness = depth
    sol.offset = 0.0
    bev = obj.modifiers.new("Bevel", "BEVEL")
    bev.width = min(0.01, depth * 0.2)
    bev.segments = 3

    em = 1.35 if pinfo["role"] == "sign" else (1.2 if pinfo["role"] == "shard" else 1.1)
    mat, hsv, emis = make_mat(obj.name + "_mat", img, emission=em)
    obj.data.materials.append(mat)
    obj["role"] = pinfo["role"]
    obj["rest_loc"] = list(obj.location)
    obj["rest_scale"] = list(obj.scale)
    obj["pinfo"] = json.dumps({k: pinfo[k] for k in pinfo if k != "file"})
    obj["hsv_name"] = hsv.name
    obj["mat_name"] = mat.name
    return obj


def setup_world_lights():
    world = bpy.data.worlds.new("World") if "World" not in bpy.data.worlds else bpy.data.worlds["World"]
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0, 0, 0, 1)
        bg.inputs[1].default_value = 0.0

    def lamp(name, typ, loc, energy, color):
        data = bpy.data.lights.new(name, typ)
        data.energy = energy
        data.color = color
        if typ == "AREA":
            data.size = 2.5
        ob = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(ob)
        ob.location = loc
        return ob

    lamp("Key", "AREA", (2.2, 2.4, 3.5), 180, (1, 0.98, 0.95))
    lamp("Fill", "AREA", (-2.5, 0.5, 2.0), 70, (0.6, 0.85, 1.0))
    lamp("Rim", "AREA", (0.0, -2.6, 1.6), 110, (1.0, 0.4, 0.75))
    neon = lamp("Neon", "POINT", (0.0, 0.55, 1.3), 40, (0.4, 1.0, 0.25))
    return neon


def setup_camera():
    data = bpy.data.cameras.new("Cam")
    data.lens = 50
    cam = bpy.data.objects.new("Cam", data)
    bpy.context.collection.objects.link(cam)
    # Framed with margin — dolly out further during zooms
    cam.location = (0, 0, 4.8)
    bpy.context.scene.camera = cam
    return cam


def animate(root, cards, cam, neon):
    sc = bpy.context.scene
    sc.frame_start = 1
    sc.frame_end = TOTAL
    sc.render.fps = FPS

    for fr in range(1, TOTAL + 1):
        t = (fr - 1) / TOTAL
        explode = trap(t, 0.00, 0.14, 0.66, 0.90)
        zoom_n = trap(t, 0.18, 0.32, 0.68, 0.92)
        zoom_text = trap(t, 0.38, 0.52, 0.70, 0.94)

        # Camera dolly OUT when zooming so nothing crops
        dolly = 4.8 + 0.55 * zoom_n + 0.85 * zoom_text + 0.25 * explode
        cam.location = (
            0.08 * math.sin(t * math.tau) * (1 - 0.5 * zoom_text),
            0.05 * math.cos(t * math.tau),
            dolly,
        )
        cam.keyframe_insert("location", frame=fr)
        cam.rotation_euler = Euler(
            (-0.01 * math.sin(t * math.tau), 0.02 * math.sin(t * math.tau), 0), "XYZ"
        )
        cam.keyframe_insert("rotation_euler", frame=fr)

        # Root subtle turn for AAA depth read
        root.rotation_euler = Euler(
            (0.04 * explode * math.sin(t * 8), 0.06 * explode, 0.03 * zoom_text),
            "XYZ",
        )
        root.keyframe_insert("rotation_euler", frame=fr)

        if neon:
            neon.data.energy = 25 + 55 * zoom_n + 35 * explode
            neon.data.keyframe_insert("energy", frame=fr)

        for obj in cards:
            role = obj.get("role", "")
            rest = Vector(obj["rest_loc"])
            rs = Vector(obj["rest_scale"])
            info = json.loads(obj["pinfo"])

            if role == "static":
                # Green flanks — never explode / never get pushed
                obj.location = rest
                obj.scale = rs
                obj.rotation_euler = Euler((0, 0, 0), "XYZ")
            elif role == "rest":
                obj.location = (
                    rest.x,
                    rest.y,
                    rest.z + 0.02 * explode,
                )
                obj.scale = rs
                obj.rotation_euler = Euler((0.02 * explode, 0, 0), "XYZ")
            elif role == "shard":
                d = info.get("delay", 0)
                e = trap(t, 0.00 + d, 0.14 + d, 0.66, 0.90)
                fly = e * info["power"] * 0.55
                ang = info["ang"]
                # True 3D: out in XY + forward/back Z pop
                obj.location = (
                    rest.x + math.cos(ang) * fly,
                    rest.y + math.sin(ang) * fly,
                    rest.z + e * (0.15 + 0.35 * info["power"]) * (1 if hash(obj.name) % 2 == 0 else -0.4),
                )
                sca = 1.0 + e * (0.2 + 0.45 * info["power"])
                obj.scale = (rs.x * sca, rs.y * sca, rs.z)
                obj.rotation_euler = Euler(
                    (
                        e * info["spin"] * 0.9,
                        e * info["spin"] * 0.55,
                        e * info["spin"] * 1.2,
                    ),
                    "XYZ",
                )
                # Color animation
                mat = bpy.data.materials.get(obj["mat_name"])
                if mat and mat.node_tree:
                    hsv = mat.node_tree.nodes.get("HSV")
                    if hsv:
                        hsv.inputs["Hue"].default_value = 0.5 + info["hue_shift"] * e * 1.4
                        hsv.inputs["Saturation"].default_value = 1.1 + 0.55 * e
                        hsv.inputs["Value"].default_value = 1.0 + 0.25 * e
                        hsv.inputs["Hue"].keyframe_insert("default_value", frame=fr)
                        hsv.inputs["Saturation"].keyframe_insert("default_value", frame=fr)
                        hsv.inputs["Value"].keyframe_insert("default_value", frame=fr)
                    bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
                    if bsdf and "Emission Strength" in bsdf.inputs:
                        bsdf.inputs["Emission Strength"].default_value = 1.15 + 1.1 * e
                        bsdf.inputs["Emission Strength"].keyframe_insert("default_value", frame=fr)
            elif role == "sign":
                # Zoom toward camera (Z+) + scale — flanks untouched elsewhere
                sca = 1.0 + 0.65 * zoom_n
                obj.location = (
                    rest.x,
                    rest.y + 0.04 * zoom_n,
                    rest.z + 0.55 * zoom_n,
                )
                obj.scale = (rs.x * sca, rs.y * sca, rs.z)
                obj.rotation_euler = Euler(
                    (-0.12 * zoom_n, 0.18 * zoom_n, -0.06 * zoom_n),
                    "XYZ",
                )
                mat = bpy.data.materials.get(obj["mat_name"])
                if mat:
                    bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
                    hsv = mat.node_tree.nodes.get("HSV")
                    if hsv:
                        hsv.inputs["Saturation"].default_value = 1.1 + 0.4 * zoom_n
                        hsv.inputs["Value"].default_value = 1.0 + 0.2 * zoom_n
                        hsv.inputs["Saturation"].keyframe_insert("default_value", frame=fr)
                        hsv.inputs["Value"].keyframe_insert("default_value", frame=fr)
                    if bsdf and "Emission Strength" in bsdf.inputs:
                        bsdf.inputs["Emission Strength"].default_value = 1.3 + 1.4 * zoom_n
                        bsdf.inputs["Emission Strength"].keyframe_insert("default_value", frame=fr)
            elif role == "text":
                sca = 1.0 + 0.85 * zoom_text
                # Diagonal travel for max presence
                obj.location = (
                    rest.x + 0.22 * zoom_text,
                    rest.y - 0.18 * zoom_text,
                    rest.z + 0.70 * zoom_text,
                )
                obj.scale = (rs.x * sca, rs.y * sca, rs.z)
                obj.rotation_euler = Euler(
                    (0.10 * zoom_text, -0.14 * zoom_text, 0.22 * zoom_text),
                    "XYZ",
                )
                mat = bpy.data.materials.get(obj["mat_name"])
                if mat:
                    bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
                    if bsdf and "Emission Strength" in bsdf.inputs:
                        bsdf.inputs["Emission Strength"].default_value = 1.15 + 0.9 * zoom_text
                        bsdf.inputs["Emission Strength"].keyframe_insert("default_value", frame=fr)

            obj.keyframe_insert("location", frame=fr)
            obj.keyframe_insert("scale", frame=fr)
            obj.keyframe_insert("rotation_euler", frame=fr)


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
    sc.render.film_transparent = True
    sc.render.filepath = str(FRAMES / "frame_")
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.05
    sc.view_settings.gamma = 1.0
    print("Cycles Standard | frames", TOTAL)


def build():
    clear()
    neon = setup_world_lights()
    cam = setup_camera()
    root = bpy.data.objects.new("Root", None)
    bpy.context.collection.objects.link(root)

    # Depth order
    z_for = {"static": -0.05, "rest": -0.02, "shard": -0.12, "sign": 0.08, "text": 0.18}
    depth_for = {"static": 0.06, "rest": 0.04, "shard": 0.07, "sign": 0.12, "text": 0.14}

    cards = []
    for p in META["pieces"]:
        role = p["role"]
        # shards start slightly behind
        z = z_for.get(role, 0.0)
        if role == "shard":
            z = -0.08 - 0.04 * (hash(p["file"]) % 5)
        obj = add_card(p, z=z, depth=depth_for.get(role, 0.05))
        obj.parent = root
        cards.append(obj)

    animate(root, cards, cam, neon)
    configure_render()
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "hyperlinks_boom_3d.blend"))

    FRAMES.mkdir(exist_ok=True)
    for p in FRAMES.glob("*.png"):
        p.unlink()

    if TOTAL <= 2:
        bpy.context.scene.render.filepath = str(ROOT / "preview_t0")
        bpy.ops.render.render(write_still=True)
        print("preview only")
    else:
        bpy.ops.render.render(animation=True)
        print("Done frames", FRAMES)


if __name__ == "__main__":
    build()
