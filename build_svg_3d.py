"""
True 3D Hyperlinks.SPACE emoji from SVG paths (Frame 121.svg).
No photo planes — extruded logo + text meshes, mesh burst props,
dynamic lights/shadows, real explosion with tumbling angles.
"""
from __future__ import annotations

import math
import os
import shutil
from pathlib import Path

import bpy
from mathutils import Euler, Vector

ROOT = Path(r"c:\1\1\1\1\1\HyperlinksSpaceAnimatedEmoji")
SVG = ROOT / "Frame 121.svg"
FRAMES = ROOT / "render_frames"
BLEND = ROOT / "hyperlinks_svg_3d.blend"

FPS = 30
TOTAL = int(os.environ.get("HL_FRAMES", "90"))
RES = int(os.environ.get("HL_RES", "512"))
SAMPLES = int(os.environ.get("HL_SAMPLES", "36"))


def clear():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for coll in (
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.curves,
        bpy.data.images,
        bpy.data.lights,
        bpy.data.cameras,
    ):
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


def glossy(name, color, emission=1.35, metal=0.28, rough=0.12):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Roughness"].default_value = rough
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.7
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = 1.0
        bsdf.inputs["Coat Roughness"].default_value = 0.04
    if "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = (*color, 1)
        bsdf.inputs["Emission Strength"].default_value = emission
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat, bsdf


def paint_face_sides(obj, face_mat, side_mat):
    """Colored front/back faces, glossy black extrusion sides."""
    mesh = obj.data
    mesh.materials.clear()
    mesh.materials.append(face_mat)
    mesh.materials.append(side_mat)
    for poly in mesh.polygons:
        n = poly.normal
        if abs(n.z) > 0.35:
            poly.material_index = 0
        else:
            poly.material_index = 1


def clean_mesh(obj, remesh=False, voxel=0.006):
    """Remove degenerate SVG artifacts that crash Embree BVH."""
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-4)
    bpy.ops.mesh.dissolve_degenerate(threshold=1e-4)
    bpy.ops.mesh.delete_loose()
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.mesh.quads_convert_to_tris(quad_method="BEAUTY", ngon_method="BEAUTY")
    bpy.ops.object.mode_set(mode="OBJECT")
    if remesh:
        mod = obj.modifiers.new("Remesh", "REMESH")
        mod.mode = "VOXEL"
        mod.voxel_size = voxel
        mod.use_smooth_shade = True
        bpy.ops.object.modifier_apply(modifier="Remesh")
        # Solidify back a bit of depth lost to remesh
        sol = obj.modifiers.new("Solidify", "SOLIDIFY")
        sol.thickness = 0.035
        sol.offset = 0.0
        bpy.ops.object.modifier_apply(modifier="Solidify")
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode="OBJECT")


def bbox_center_size(objs):
    mins = Vector((1e9, 1e9, 1e9))
    maxs = Vector((-1e9, -1e9, -1e9))
    for ob in objs:
        for corner in ob.bound_box:
            w = ob.matrix_world @ Vector(corner)
            mins = Vector((min(mins.x, w.x), min(mins.y, w.y), min(mins.z, w.z)))
            maxs = Vector((max(maxs.x, w.x), max(maxs.y, w.y), max(maxs.z, w.z)))
    center = (mins + maxs) * 0.5
    size = maxs - mins
    return center, size


def mat_rgb(obj):
    if not obj.data.materials:
        return None
    m = obj.data.materials[0]
    if not m:
        return None
    if m.use_nodes and m.node_tree:
        for n in m.node_tree.nodes:
            if n.type == "BSDF_PRINCIPLED":
                return tuple(n.inputs["Base Color"].default_value[:3])
            if n.type == "RGB":
                return tuple(n.outputs[0].default_value[:3])
    return tuple(m.diffuse_color[:3])


def import_svg_logo():
    """Import Frame 121.svg → extruded N + text meshes (flat convert → scale → solidify)."""
    if not SVG.exists():
        raise SystemExit(f"Missing {SVG}")

    before = set(bpy.data.objects)
    bpy.ops.import_curve.svg(filepath=str(SVG))
    curves = [o for o in bpy.data.objects if o not in before and o.type == "CURVE"]
    if not curves:
        raise SystemExit("SVG import produced no curves")

    green, white = [], []
    for c in curves:
        col = mat_rgb(c)
        center, size = bbox_center_size([c])
        if size.x > 0.02 and size.y > 0.02 and abs(size.x - size.y) < 0.005:
            bpy.data.objects.remove(c, do_unlink=True)
            continue
        if col is None or max(col) < 0.08:
            bpy.data.objects.remove(c, do_unlink=True)
            continue
        if col[1] > 0.55 and col[1] > col[0] * 1.2:
            green.append(c)
        elif min(col) > 0.7:
            white.append(c)
        else:
            if center.x < 0.01:
                green.append(c)
            else:
                white.append(c)

    if not green or not white:
        raise SystemExit(f"SVG parse failed green={len(green)} white={len(white)}")

    # Flat curves only — extrude AFTER scale via Solidify on meshes
    for c in green + white:
        d = c.data
        d.dimensions = "2D"
        d.fill_mode = "BOTH"
        d.extrude = 0.0
        d.bevel_depth = 0.0
        for sp in d.splines:
            sp.resolution_u = 8 if c in green else 5

    bpy.ops.object.select_all(action="DESELECT")
    for o in green + white:
        o.select_set(True)
    bpy.context.view_layer.objects.active = green[0]
    bpy.ops.object.convert(target="MESH")

    n_objs = [o for o in green if o.name in bpy.data.objects]
    t_objs = [o for o in white if o.name in bpy.data.objects]

    bpy.ops.object.select_all(action="DESELECT")
    for o in n_objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = n_objs[0]
    if len(n_objs) > 1:
        bpy.ops.object.join()
    logo_n = bpy.context.active_object
    logo_n.name = "LogoN"

    bpy.ops.object.select_all(action="DESELECT")
    for o in t_objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = t_objs[0]
    if len(t_objs) > 1:
        bpy.ops.object.join()
    logo_text = bpy.context.active_object
    logo_text.name = "LogoText"

    # Flip SVG Y-down → Blender Y-up. Y-flip reverses winding; recalc normals outward
    # (do NOT also flip_normals — that would show the mirrored back faces).
    for ob in (logo_n, logo_text):
        for v in ob.data.vertices:
            v.co.y *= -1
        ob.data.update()
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode="OBJECT")

    center, size = bbox_center_size([logo_n, logo_text])
    span = max(size.x, size.y, 1e-9)
    scale = 2.35 / span
    for ob in (logo_n, logo_text):
        for v in ob.data.vertices:
            v.co = (v.co - center) * scale
        ob.data.update()
        ob.location = (0, 0, 0)
        ob.scale = (1, 1, 1)

    # True 3D thickness
    for ob, thick in ((logo_n, 0.11), (logo_text, 0.085)):
        sol = ob.modifiers.new("Solidify", "SOLIDIFY")
        sol.thickness = thick
        sol.offset = 0.0
        sol.use_even_offset = True
        sol.use_quality_normals = True
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.modifier_apply(modifier="Solidify")
        bev = ob.modifiers.new("Bevel", "BEVEL")
        bev.width = 0.004 if ob is logo_n else 0.003
        bev.segments = 2
        bev.limit_method = "ANGLE"
        bpy.ops.object.modifier_apply(modifier="Bevel")
        bpy.ops.object.shade_smooth()

    center2, size2 = bbox_center_size([logo_n, logo_text])
    root = bpy.data.objects.new("BrandRoot", None)
    bpy.context.collection.objects.link(root)
    for ob in (logo_n, logo_text):
        ob.location = (
            ob.location.x - center2.x,
            ob.location.y - center2.y,
            ob.location.z - center2.z,
        )
        ob.parent = root

    logo_n.location.z += 0.08
    logo_text.location.z -= 0.01

    green_face, _ = glossy("NFace", (0.0, 0.92, 0.32), emission=2.1, metal=0.12, rough=0.08)
    white_face, _ = glossy("TextFace", (1.0, 1.0, 1.0), emission=1.1, metal=0.05, rough=0.16)
    black_side, _ = glossy("BlackSide", (0.02, 0.02, 0.025), emission=0.04, metal=0.85, rough=0.08)

    clean_mesh(logo_n, remesh=False)
    clean_mesh(logo_text, remesh=False)
    paint_face_sides(logo_n, green_face, black_side)
    paint_face_sides(logo_text, white_face, black_side)

    _, sz = bbox_center_size([logo_n, logo_text])
    print(
        "Logo meshes:",
        f"N={len(logo_n.data.polygons)} tris",
        f"Text={len(logo_text.data.polygons)} tris",
        f"size=({sz.x:.2f},{sz.y:.2f},{sz.z:.2f})",
    )
    return root, logo_n, logo_text


def add_burst(parent):
    """Reference-inspired 3D props: crystals, red squiggle, green loop, red sphere, zigzag."""
    colors = [
        (1.0, 0.92, 0.08),  # yellow
        (1.0, 0.18, 0.62),  # hot pink
        (0.15, 0.85, 1.0),  # cyan
        (1.0, 0.45, 0.08),  # orange
        (0.55, 1.0, 0.2),   # lime
        (1.0, 0.25, 0.4),   # coral pink
    ]
    props = []

    # --- Crystal spikes ---
    n = 26
    for i in range(n):
        ang = (i / n) * math.tau + (i % 5) * 0.04
        r = 0.82 + (i % 4) * 0.07
        x = math.cos(ang) * r
        y = math.sin(ang) * r * 0.88
        z = -0.28 - (i % 3) * 0.04
        bpy.ops.mesh.primitive_cone_add(
            vertices=5 + (i % 2),
            radius1=0.055 + (i % 4) * 0.012,
            depth=0.48 + (i % 5) * 0.07,
            location=(x, y, z),
        )
        cr = bpy.context.active_object
        cr.name = f"spike_{i:02d}"
        cr.rotation_euler = Vector((x, y, 0.2)).to_track_quat("Z", "Y").to_euler()
        mat, _ = glossy(f"spike_mat_{i}", colors[i % len(colors)], emission=1.7, metal=0.35, rough=0.1)
        cr.data.materials.append(mat)
        cr.parent = parent
        bpy.ops.object.shade_smooth()
        cr["kind"] = "spike"
        cr["rest_loc"] = list(cr.location)
        cr["rest_rot"] = list(cr.rotation_euler)
        cr["ang"] = ang
        cr["power"] = 0.7 + 0.9 * ((i * 41) % 100) / 100.0
        cr["spin"] = (-1 if i % 2 == 0 else 1) * (0.8 + 1.2 * ((i * 19) % 100) / 100.0)
        cr["delay"] = 0.008 * (i % 7)
        cr["mat"] = mat.name
        props.append(cr)

    # --- Red squiggle: chained glossy capsules (stable mesh, no curve BVH issues) ---
    mat_r, _ = glossy("RedTube", (1.0, 0.08, 0.12), emission=1.4, metal=0.4, rough=0.1)
    sq_root = bpy.data.objects.new("RedSquiggle", None)
    bpy.context.collection.objects.link(sq_root)
    sq_root.parent = parent
    sq_pts = [
        (-0.85, -0.15, -0.04),
        (-0.55, 0.28, 0.06),
        (-0.2, -0.08, -0.03),
        (0.15, 0.32, 0.08),
        (0.48, 0.02, -0.02),
    ]
    for i in range(len(sq_pts) - 1):
        a = Vector(sq_pts[i])
        b = Vector(sq_pts[i + 1])
        mid = (a + b) * 0.5
        length = (b - a).length
        bpy.ops.mesh.primitive_cylinder_add(radius=0.042, depth=max(0.08, length), location=mid)
        seg = bpy.context.active_object
        seg.name = f"squiggle_seg_{i}"
        seg.rotation_euler = (b - a).to_track_quat("Z", "Y").to_euler()
        seg.data.materials.append(mat_r)
        seg.parent = sq_root
        bpy.ops.object.shade_smooth()
    # Join segments into one prop for animation
    bpy.ops.object.select_all(action="DESELECT")
    for ch in list(sq_root.children):
        ch.select_set(True)
    bpy.context.view_layer.objects.active = sq_root.children[0]
    bpy.ops.object.join()
    sq = bpy.context.active_object
    sq.name = "RedSquiggle"
    sq.parent = parent
    bpy.data.objects.remove(sq_root, do_unlink=True)
    sq["kind"] = "squiggle"
    sq["rest_loc"] = list(sq.location)
    sq["rest_rot"] = list(sq.rotation_euler)
    sq["ang"] = math.pi * 0.85
    sq["power"] = 1.1
    sq["spin"] = 1.4
    sq["delay"] = 0.02
    sq["mat"] = mat_r.name
    props.append(sq)

    # --- Green loop + red sphere ---
    bpy.ops.mesh.primitive_torus_add(
        major_radius=0.28,
        minor_radius=0.055,
        major_segments=48,
        minor_segments=16,
        location=(0.72, -0.05, -0.08),
    )
    loop = bpy.context.active_object
    loop.name = "GreenLoop"
    loop.rotation_euler = (0.9, 0.35, 0.4)
    mat_g, _ = glossy("GreenLoopMat", (0.05, 0.95, 0.4), emission=1.5, metal=0.3, rough=0.11)
    loop.data.materials.append(mat_g)
    loop.parent = parent
    bpy.ops.object.shade_smooth()
    loop["kind"] = "loop"
    loop["rest_loc"] = list(loop.location)
    loop["rest_rot"] = list(loop.rotation_euler)
    loop["ang"] = 0.15
    loop["power"] = 0.95
    loop["spin"] = -1.1
    loop["delay"] = 0.015
    loop["mat"] = mat_g.name
    props.append(loop)

    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.11, segments=32, ring_count=16, location=(0.72, -0.05, -0.08))
    ball = bpy.context.active_object
    ball.name = "RedSphere"
    mat_b, _ = glossy("RedBall", (1.0, 0.05, 0.1), emission=1.35, metal=0.55, rough=0.06)
    ball.data.materials.append(mat_b)
    ball.parent = parent
    bpy.ops.object.shade_smooth()
    ball["kind"] = "ball"
    ball["rest_loc"] = list(ball.location)
    ball["rest_rot"] = [0, 0, 0]
    ball["ang"] = 0.2
    ball["power"] = 1.0
    ball["spin"] = 2.0
    ball["delay"] = 0.01
    ball["mat"] = mat_b.name
    props.append(ball)

    # --- Black zigzag bolt ---
    bpy.ops.mesh.primitive_cube_add(size=0.12, location=(0.35, 0.75, -0.12))
    zig = bpy.context.active_object
    zig.name = "ZigZag"
    zig.scale = (0.35, 0.08, 0.55)
    zig.rotation_euler = (0.2, 0.5, 0.9)
    mat_z, _ = glossy("ZigMat", (0.03, 0.03, 0.04), emission=0.08, metal=0.9, rough=0.07)
    zig.data.materials.append(mat_z)
    zig.parent = parent
    zig["kind"] = "zig"
    zig["rest_loc"] = list(zig.location)
    zig["rest_rot"] = list(zig.rotation_euler)
    zig["ang"] = 1.1
    zig["power"] = 0.85
    zig["spin"] = 1.6
    zig["delay"] = 0.025
    zig["mat"] = mat_z.name
    props.append(zig)

    return props


def lights():
    world = bpy.data.worlds.new("World") if "World" not in bpy.data.worlds else bpy.data.worlds["World"]
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0, 0, 0, 1)
        bg.inputs[1].default_value = 0.0

    objs = []

    def add(name, typ, loc, energy, color, size=2.0, shadow=True):
        data = bpy.data.lights.new(name, typ)
        data.energy = energy
        data.color = color
        if typ == "AREA":
            data.size = size
        if hasattr(data, "use_shadow"):
            data.use_shadow = shadow
        ob = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(ob)
        ob.location = loc
        objs.append(ob)
        return ob

    key = add("Key", "AREA", (1.8, -1.2, 3.4), 350, (1.0, 0.98, 0.95), size=2.4)
    key.rotation_euler = (0.4, 0.15, 0.3)
    add("Fill", "AREA", (-2.4, 1.0, 2.0), 90, (0.7, 1.0, 0.75), size=3.0)
    add("Rim", "AREA", (0.2, 2.6, 1.6), 160, (1.0, 0.4, 0.7), size=2.2)
    neon = add("Neon", "POINT", (0.0, -0.2, 1.4), 100, (0.15, 1.0, 0.3))
    add("Kick", "POINT", (-0.8, -1.0, 0.6), 40, (1.0, 0.55, 0.15))
    return neon, objs


def camera():
    data = bpy.data.cameras.new("Cam")
    data.lens = 50
    data.clip_start = 0.05
    cam = bpy.data.objects.new("Cam", data)
    bpy.context.collection.objects.link(cam)
    cam.location = (0.0, -0.02, 2.55)
    bpy.context.scene.camera = cam
    return cam


def animate(root, logo_n, logo_text, props, cam, neon):
    sc = bpy.context.scene
    sc.frame_start = 1
    sc.frame_end = TOTAL
    sc.render.fps = FPS

    n_rest = Vector(logo_n.location)
    t_rest = Vector(logo_text.location)
    n_rrot = Euler(logo_n.rotation_euler)
    t_rrot = Euler(logo_text.rotation_euler)

    for fr in range(1, TOTAL + 1):
        t = (fr - 1) / max(1, TOTAL - 1)
        boom = trap(t, 0.02, 0.18, 0.62, 0.90)
        zoom_n = trap(t, 0.16, 0.32, 0.58, 0.86)
        zoom_txt = trap(t, 0.34, 0.50, 0.68, 0.92)
        settle = trap(t, 0.78, 0.88, 0.95, 1.01)  # soft land

        # --- Logo N: surge forward, tumble, catch light ---
        logo_n.location = (
            n_rest.x + 0.05 * zoom_txt - 0.02 * boom,
            n_rest.y - 0.03 * zoom_n + 0.05 * zoom_txt,
            n_rest.z + 0.14 * zoom_n + 0.08 * boom,
        )
        logo_n.rotation_euler = Euler(
            (
                n_rrot.x - 0.18 * zoom_n + 0.12 * boom + 0.08 * zoom_txt,
                n_rrot.y + 0.22 * boom - 0.14 * zoom_n + 0.08 * zoom_txt,
                n_rrot.z + 0.12 * boom + 0.18 * zoom_txt,
            ),
            "XYZ",
        )
        ns = 1.0 + 0.08 * zoom_n + 0.05 * boom
        logo_n.scale = (ns, ns, ns * (1.0 + 0.1 * boom))
        logo_n.keyframe_insert("location", frame=fr)
        logo_n.keyframe_insert("rotation_euler", frame=fr)
        logo_n.keyframe_insert("scale", frame=fr)

        # --- Text: diagonal whip + depth pop ---
        logo_text.location = (
            t_rest.x + 0.12 * zoom_txt - 0.05 * boom,
            t_rest.y - 0.1 * zoom_txt + 0.03 * boom,
            t_rest.z + 0.1 * zoom_txt + 0.05 * boom - 0.03 * zoom_n,
        )
        logo_text.rotation_euler = Euler(
            (
                t_rrot.x + 0.22 * zoom_txt - 0.08 * boom,
                t_rrot.y - 0.28 * zoom_txt + 0.18 * boom,
                t_rrot.z + 0.32 * zoom_txt + 0.1 * boom,
            ),
            "XYZ",
        )
        ts = 1.0 + 0.08 * zoom_txt + 0.04 * boom
        logo_text.scale = (ts, ts, ts * (1.0 + 0.12 * boom))
        logo_text.keyframe_insert("location", frame=fr)
        logo_text.keyframe_insert("rotation_euler", frame=fr)
        logo_text.keyframe_insert("scale", frame=fr)

        # Punch emission on brand faces during beats
        for mat_name, amp in (("NFace", 1.55 + 1.1 * zoom_n + 0.6 * boom), ("TextFace", 1.25 + 0.9 * zoom_txt + 0.5 * boom)):
            mat = bpy.data.materials.get(mat_name)
            if not mat:
                continue
            bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if bsdf and "Emission Strength" in bsdf.inputs:
                bsdf.inputs["Emission Strength"].default_value = amp
                bsdf.inputs["Emission Strength"].keyframe_insert("default_value", frame=fr)

        # --- Burst props: true radial explosion + tumbling ---
        for p in props:
            d = p["delay"]
            e = trap(t, 0.00 + d, 0.16 + d, 0.60, 0.88)
            rest = Vector(p["rest_loc"])
            rr = Vector(p["rest_rot"])
            ang = p["ang"]
            fly = e * p["power"] * 0.55
            # Outward + lift — keep props in frame during boom
            p.location = (
                rest.x + math.cos(ang) * fly,
                rest.y + math.sin(ang) * fly,
                rest.z + e * (0.22 + 0.35 * p["power"]),
            )
            spin = e * p["spin"] * 1.1
            p.rotation_euler = Euler(
                (
                    rr.x + spin * 1.5,
                    rr.y + spin * 1.2,
                    rr.z + spin * 2.0,
                ),
                "XYZ",
            )
            sca = 1.0 + e * (0.55 + 0.85 * p["power"])
            if p["kind"] == "ball":
                sca = 1.0 + e * 0.55
            p.scale = (sca, sca, sca)
            p.keyframe_insert("location", frame=fr)
            p.keyframe_insert("rotation_euler", frame=fr)
            p.keyframe_insert("scale", frame=fr)

            mat = bpy.data.materials.get(p["mat"])
            if mat:
                bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
                if bsdf and "Emission Strength" in bsdf.inputs:
                    base = 1.4 if p["kind"] != "zig" else 0.08
                    bsdf.inputs["Emission Strength"].default_value = base + 2.4 * e
                    bsdf.inputs["Emission Strength"].keyframe_insert("default_value", frame=fr)

        # Camera: gentle pull on boom; keep brand readable in frame
        pull = 2.55 + 0.35 * boom + 0.12 * zoom_n + 0.18 * zoom_txt
        cam.location = (
            0.08 * zoom_txt - 0.03 * boom,
            -0.02 - 0.06 * zoom_n + 0.05 * zoom_txt,
            pull,
        )
        cam.rotation_euler = Euler(
            (
                0.03 * zoom_n - 0.04 * zoom_txt,
                0.03 * boom + 0.03 * zoom_txt,
                0.05 * zoom_txt - 0.02 * boom,
            ),
            "XYZ",
        )
        cam.keyframe_insert("location", frame=fr)
        cam.keyframe_insert("rotation_euler", frame=fr)

        # Root micro-turn so shadows / speculars sweep
        root.rotation_euler = Euler(
            (
                0.03 * boom + 0.02 * zoom_n,
                0.04 * boom + 0.05 * zoom_txt,
                0.025 * zoom_n - 0.02 * zoom_txt,
            ),
            "XYZ",
        )
        root.keyframe_insert("rotation_euler", frame=fr)

        if neon:
            neon.data.energy = 60 + 140 * boom + 100 * zoom_n + 70 * zoom_txt
            neon.data.keyframe_insert("energy", frame=fr)


def configure_render():
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    # Shadows matter for true 3D read
    sc.cycles.max_bounces = 6
    sc.cycles.diffuse_bounces = 3
    sc.cycles.glossy_bounces = 4
    sc.render.resolution_x = RES
    sc.render.resolution_y = RES
    sc.render.fps = FPS
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.film_transparent = True
    sc.render.filepath = str(FRAMES / "frame_")
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.12
    sc.view_settings.gamma = 1.0
    print(f"SVG 3D boom | frames={TOTAL} res={RES} samples={SAMPLES}")


def build():
    clear()
    neon, _ = lights()
    cam = camera()
    root, logo_n, logo_text = import_svg_logo()
    props = add_burst(root)
    animate(root, logo_n, logo_text, props, cam, neon)
    configure_render()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))

    if FRAMES.exists():
        shutil.rmtree(FRAMES)
    FRAMES.mkdir(parents=True)
    bpy.ops.render.render(animation=True)
    print("Done", FRAMES, "count", len(list(FRAMES.glob('frame_*.png'))))


if __name__ == "__main__":
    build()
