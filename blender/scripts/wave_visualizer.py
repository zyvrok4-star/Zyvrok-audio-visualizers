"""
Zyvrok Audio Visualizers - Wave
================================
Builds a glowing, audio-reactive wave visualizer in Blender 5 from any song.

HOW TO USE (inside Blender)
  1. Open Blender 5 -> Scripting tab -> Open this file.
  2. Set AUDIO_PATH below to your song (mp3 / wav / flac / ogg).
  3. Press Run Script (Alt+P). Press Space in the viewport to preview.
  4. Render -> Render Animation (Ctrl+F12) to export an MP4 with the audio.

HOW TO USE (command line, no UI)
  blender -b -P wave_visualizer.py -- --audio "song.mp3" [--landscape] [--render]

Re-running the script only replaces objects it created (names start with "ZV_").

Made by Zyvrok - https://github.com/zyvrok4-star/zyvrok-audio-visualizers
MIT licence - free to use and change, just keep this credit.
"""

import math
import os
import sys

import bpy
import aud
import numpy as np

# --------------------------------------------------------------------------
# SETTINGS - change these
# --------------------------------------------------------------------------
AUDIO_PATH = ""            # e.g. r"C:\Music\my_song.mp3"
LOGO_PATH = ""             # optional PNG shown above the wave (leave "" for none)

VERTICAL = True            # True = 1080x1920 (Reels/Shorts), False = 1920x1080
FPS = 30

BANDS = 96                 # detail of the wave (more = more peaks)
MIN_FREQ = 40.0            # Hz - lowest frequency shown
MAX_FREQ = 12000.0         # Hz - highest frequency shown
MIRROR = True              # True = wave goes up AND down (symmetrical)
BASS_IN_CENTER = True      # True = bass in the middle, highs on the sides

WAVE_WIDTH = 8.0           # width of the wave in Blender units
WAVE_HEIGHT = 1.6          # how tall the peaks get
THICKNESS = 0.025          # line thickness
SMOOTHING = 0.55           # 0 = jumpy, 0.9 = very smooth fall-off
GLOW = True                # bloom glow in the compositor

# Each layer = one line. (colour RGB 0-1, height multiplier, delay in frames, glow strength)
LAYERS = [
    ((0.10, 0.85, 1.00), 1.00, 0, 12.0),   # cyan, front
    ((0.75, 0.25, 1.00), 0.75, 3, 8.0),    # purple, echo
    ((1.00, 0.20, 0.55), 0.50, 6, 6.0),    # pink, far echo
]
BACKGROUND = (0.005, 0.005, 0.012)
HIDE_DEFAULT_CUBE = True   # hides Blender's startup "Cube" so it doesn't block the wave
# --------------------------------------------------------------------------

PREFIX = "ZV_"


def parse_cli():
    """Allow: blender -b -P wave_visualizer.py -- --audio x.mp3 --landscape --render"""
    global AUDIO_PATH, LOGO_PATH, VERTICAL
    render = False
    if "--" in sys.argv:
        args = sys.argv[sys.argv.index("--") + 1:]
        for i, a in enumerate(args):
            if a == "--audio" and i + 1 < len(args):
                AUDIO_PATH = args[i + 1]
            elif a == "--logo" and i + 1 < len(args):
                LOGO_PATH = args[i + 1]
            elif a == "--landscape":
                VERTICAL = False
            elif a == "--render":
                render = True
    return render


# --------------------------------------------------------------------------
# 1. AUDIO ANALYSIS  ->  one row of wave heights per frame
# --------------------------------------------------------------------------
def analyse_audio(path, fps):
    sound = aud.Sound(path)
    rate = int(sound.specs[0])
    samples = sound.data()
    mono = samples.mean(axis=1) if samples.ndim > 1 else samples
    mono = mono.astype(np.float32)

    frames = max(1, int(len(mono) / rate * fps))
    win = 4096
    hann = np.hanning(win).astype(np.float32)
    freqs = np.fft.rfftfreq(win, 1.0 / rate)

    half = BANDS // 2          # left half; mirrored to the right later
    edges = np.geomspace(MIN_FREQ, MAX_FREQ, half + 1)
    bins = [np.where((freqs >= edges[i]) & (freqs < edges[i + 1]))[0] for i in range(half)]
    # make sure every band has at least one FFT bin
    bins = [b if len(b) else np.array([np.argmin(np.abs(freqs - edges[i]))]) for i, b in enumerate(bins)]

    padded = np.concatenate([np.zeros(win // 2, np.float32), mono, np.zeros(win, np.float32)])
    spec = np.zeros((frames, half), np.float32)
    for f in range(frames):
        start = int(f / fps * rate)
        chunk = padded[start:start + win]
        mag = np.abs(np.fft.rfft(chunk * hann))
        spec[f] = [mag[b].mean() for b in bins]

    # loudness curve: log scale, tilt up the highs a bit so they are visible
    spec = np.log1p(spec * 10.0)
    spec *= np.linspace(1.0, 1.8, half)[None, :]
    ref = np.percentile(spec, 99.0) or 1.0
    spec = np.clip(spec / ref, 0.0, 1.0)
    spec = spec ** 1.4                       # more contrast between quiet and loud

    # time smoothing: rise fast, fall slowly
    out = np.zeros_like(spec)
    prev = np.zeros(half, np.float32)
    for f in range(frames):
        cur = spec[f]
        prev = np.where(cur > prev, cur * 0.8 + prev * 0.2, prev * SMOOTHING + cur * (1 - SMOOTHING))
        out[f] = prev

    # small blur across bands so the line stays smooth
    k = np.array([1, 4, 6, 4, 1], np.float32)
    k /= k.sum()
    out = np.apply_along_axis(lambda r: np.convolve(np.pad(r, 2, mode="edge"), k, "valid"), 1, out)

    left = out[:, ::-1] if BASS_IN_CENTER else out
    out = np.concatenate([left, left[:, ::-1]], axis=1)

    # taper the ends so the wave starts and ends flat
    n = out.shape[1]
    x = np.linspace(-1, 1, n)
    out *= (np.cos(x * math.pi / 2) ** 0.6)[None, :]
    return out.astype(np.float32), frames


def bake_to_image(data):
    """Store heights in a float image: x = position on wave, y = frame."""
    frames, n = data.shape
    name = PREFIX + "WaveData"
    old = bpy.data.images.get(name)
    if old:
        bpy.data.images.remove(old)
    img = bpy.data.images.new(name, width=n, height=frames, alpha=False, float_buffer=True)
    img.colorspace_settings.name = "Non-Color"
    px = np.ones((frames, n, 4), np.float32)
    px[..., 0] = px[..., 1] = px[..., 2] = data
    img.pixels.foreach_set(px.ravel())
    img.file_format = "OPEN_EXR"
    img.pack()
    return img


# --------------------------------------------------------------------------
# 2. GEOMETRY NODES  ->  line that reads the image every frame
# --------------------------------------------------------------------------
def build_node_group(img, frames):
    name = PREFIX + "Wave"
    old = bpy.data.node_groups.get(name)
    if old:
        bpy.data.node_groups.remove(old)
    ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
    iface = ng.interface
    iface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    s_h = iface.new_socket("Height", in_out="INPUT", socket_type="NodeSocketFloat")
    s_d = iface.new_socket("Delay", in_out="INPUT", socket_type="NodeSocketFloat")
    s_m = iface.new_socket("Material", in_out="INPUT", socket_type="NodeSocketMaterial")
    s_mi = iface.new_socket("Mirror", in_out="INPUT", socket_type="NodeSocketBool")
    s_h.default_value, s_d.default_value, s_mi.default_value = WAVE_HEIGHT, 0.0, MIRROR
    iface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")

    N = ng.nodes
    L = ng.links
    gin = N.new("NodeGroupInput")
    gout = N.new("NodeGroupOutput")

    line = N.new("GeometryNodeCurvePrimitiveLine")
    line.inputs["Start"].default_value = (-WAVE_WIDTH / 2, 0, 0)
    line.inputs["End"].default_value = (WAVE_WIDTH / 2, 0, 0)

    res = N.new("GeometryNodeResampleCurve")
    res.inputs["Count"].default_value = BANDS * 4
    L.new(line.outputs["Curve"], res.inputs["Curve"])

    # u = position along the line (0..1)
    param = N.new("GeometryNodeSplineParameter")

    # v = (frame - delay + 0.5) / frames
    time = N.new("GeometryNodeInputSceneTime")
    sub = N.new("ShaderNodeMath"); sub.operation = "SUBTRACT"
    L.new(time.outputs["Frame"], sub.inputs[0])
    L.new(gin.outputs["Delay"], sub.inputs[1])
    start = N.new("ShaderNodeMath"); start.operation = "SUBTRACT"
    L.new(sub.outputs[0], start.inputs[0])
    start.inputs[1].default_value = bpy.context.scene.frame_start - 0.5
    div = N.new("ShaderNodeMath"); div.operation = "DIVIDE"
    L.new(start.outputs[0], div.inputs[0])
    div.inputs[1].default_value = float(frames)

    uv = N.new("ShaderNodeCombineXYZ")
    L.new(param.outputs["Factor"], uv.inputs["X"])
    L.new(div.outputs[0], uv.inputs["Y"])

    tex = N.new("GeometryNodeImageTexture")
    tex.interpolation = "Linear"
    tex.extension = "EXTEND"
    tex.inputs["Image"].default_value = img
    L.new(uv.outputs["Vector"], tex.inputs["Vector"])

    sep = N.new("FunctionNodeSeparateColor")
    L.new(tex.outputs["Color"], sep.inputs["Color"])
    mul = N.new("ShaderNodeMath"); mul.operation = "MULTIPLY"
    L.new(sep.outputs[0], mul.inputs[0])
    L.new(gin.outputs["Height"], mul.inputs[1])

    off = N.new("ShaderNodeCombineXYZ")
    L.new(mul.outputs[0], off.inputs["Z"])
    setpos = N.new("GeometryNodeSetPosition")
    L.new(res.outputs["Curve"], setpos.inputs["Geometry"])
    L.new(off.outputs["Vector"], setpos.inputs["Offset"])

    # mirror copy (upside down) when Mirror is on
    flip = N.new("GeometryNodeTransform")
    flip.inputs["Scale"].default_value = (1, 1, -1)
    L.new(setpos.outputs["Geometry"], flip.inputs["Geometry"])
    sw = N.new("GeometryNodeSwitch"); sw.input_type = "GEOMETRY"
    L.new(gin.outputs["Mirror"], sw.inputs["Switch"])
    L.new(flip.outputs["Geometry"], sw.inputs["True"])
    join = N.new("GeometryNodeJoinGeometry")
    L.new(setpos.outputs["Geometry"], join.inputs["Geometry"])
    L.new(sw.outputs["Output"], join.inputs["Geometry"])

    circle = N.new("GeometryNodeCurvePrimitiveCircle")
    circle.inputs["Resolution"].default_value = 8
    circle.inputs["Radius"].default_value = THICKNESS
    tomesh = N.new("GeometryNodeCurveToMesh")
    L.new(join.outputs["Geometry"], tomesh.inputs["Curve"])
    L.new(circle.outputs["Curve"], tomesh.inputs["Profile Curve"])

    setmat = N.new("GeometryNodeSetMaterial")
    L.new(tomesh.outputs["Mesh"], setmat.inputs["Geometry"])
    L.new(gin.outputs["Material"], setmat.inputs["Material"])
    L.new(setmat.outputs["Geometry"], gout.inputs["Geometry"])

    # tidy layout
    for i, node in enumerate(N):
        node.location = (i * 180, 0)
    return ng


def emission_material(name, color, strength):
    old = bpy.data.materials.get(name)
    if old:
        bpy.data.materials.remove(old)
    mat = bpy.data.materials.new(name)
    if hasattr(mat, "use_nodes"):
        mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    em.inputs["Strength"].default_value = strength
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return mat


# --------------------------------------------------------------------------
# 3. SCENE: clean up, camera, world, audio, render settings
# --------------------------------------------------------------------------
def clear_old():
    for ob in [o for o in bpy.data.objects if o.name.startswith(PREFIX)]:
        bpy.data.objects.remove(ob, do_unlink=True)
    col = bpy.data.collections.get(PREFIX + "Visualizer")
    if col:
        bpy.data.collections.remove(col)


def hide_default_cube():
    cube = bpy.data.objects.get("Cube")
    if HIDE_DEFAULT_CUBE and cube and cube.type == "MESH":
        cube.hide_render = True
        cube.hide_set(True) if bpy.context.view_layer.objects.get("Cube") else None


def get_collection():
    col = bpy.data.collections.new(PREFIX + "Visualizer")
    bpy.context.scene.collection.children.link(col)
    return col


def new_empty_mesh_object(name, col):
    mesh = bpy.data.meshes.new(name)
    ob = bpy.data.objects.new(name, mesh)
    col.objects.link(ob)
    return ob


def setup_camera(col, scene):
    cam_data = bpy.data.cameras.new(PREFIX + "Camera")
    cam_data.type = "ORTHO"
    # ortho_scale covers the longer side, so fit the wave width with a little margin
    cam_data.ortho_scale = WAVE_WIDTH * 1.15 * ((16 / 9) if VERTICAL else 1.0)
    cam = bpy.data.objects.new(PREFIX + "Camera", cam_data)
    cam.location = (0, -20, 0)
    cam.rotation_euler = (math.radians(90), 0, 0)
    col.objects.link(cam)
    scene.camera = cam


def setup_logo(col):
    if not LOGO_PATH or not os.path.exists(bpy.path.abspath(LOGO_PATH)):
        return
    img = bpy.data.images.load(bpy.path.abspath(LOGO_PATH), check_existing=True)
    w, h = img.size
    size = 2.2
    sx, sz = (size, size * h / w) if w >= h else (size * w / h, size)
    mesh = bpy.data.meshes.new(PREFIX + "Logo")
    mesh.from_pydata([(-sx / 2, 0, -sz / 2), (sx / 2, 0, -sz / 2), (sx / 2, 0, sz / 2), (-sx / 2, 0, sz / 2)],
                     [], [(0, 1, 2, 3)])
    uv = mesh.uv_layers.new()
    for i, co in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]):
        uv.data[i].uv = co
    ob = bpy.data.objects.new(PREFIX + "Logo", mesh)
    ob.location = (0, 0.5, WAVE_HEIGHT + sz / 2 + 0.8)
    col.objects.link(ob)
    mat = bpy.data.materials.new(PREFIX + "LogoMat")
    if hasattr(mat, "use_nodes"):
        mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = img
    em = nt.nodes.new("ShaderNodeEmission")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(t.outputs["Color"], em.inputs["Color"])
    nt.links.new(t.outputs["Alpha"], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    mesh.materials.append(mat)


def setup_world(scene):
    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    if hasattr(world, "use_nodes"):
        world.use_nodes = True
    bg = next((n for n in world.node_tree.nodes if n.type == "BACKGROUND"), None)
    if bg:
        bg.inputs["Color"].default_value = (*BACKGROUND, 1)
        bg.inputs["Strength"].default_value = 1.0


def setup_glow(scene):
    """Bloom using the compositor Glare node (Blender 5 node-group compositor)."""
    if not GLOW:
        return
    try:
        name = PREFIX + "Compositor"
        old = bpy.data.node_groups.get(name)
        if old:
            bpy.data.node_groups.remove(old)
        tree = bpy.data.node_groups.new(name, "CompositorNodeTree")
        tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        rl = tree.nodes.new("CompositorNodeRLayers")
        glare = tree.nodes.new("CompositorNodeGlare")
        out = tree.nodes.new("NodeGroupOutput")
        for sock_name, val in (("Type", "Bloom"), ("Quality", "High")):
            if sock_name in glare.inputs:
                glare.inputs[sock_name].default_value = val
        for sock_name, val in (("Threshold", 0.6), ("Strength", 1.0), ("Size", 0.7)):
            if sock_name in glare.inputs:
                glare.inputs[sock_name].default_value = val
        tree.links.new(rl.outputs["Image"], glare.inputs["Image"])
        tree.links.new(glare.outputs["Image"], out.inputs[0])
        scene.compositing_node_group = tree
        scene.render.use_compositing = True
    except Exception as e:  # older/newer API - glow is optional
        print("Zyvrok: glow skipped ->", e)


def setup_audio(scene, path, frames):
    se = scene.sequence_editor or scene.sequence_editor_create()
    strips = se.strips if hasattr(se, "strips") else se.sequences
    for s in [s for s in strips if s.name.startswith(PREFIX)]:
        strips.remove(s)
    strips.new_sound(PREFIX + "Audio", path, channel=1, frame_start=scene.frame_start)
    scene.frame_end = scene.frame_start + frames - 1
    scene.sync_mode = "AUDIO_SYNC"


def setup_render(scene):
    r = scene.render
    for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            r.engine = engine
            break
        except TypeError:
            continue
    r.fps = FPS
    r.resolution_x, r.resolution_y = (1080, 1920) if VERTICAL else (1920, 1080)
    r.resolution_percentage = 100
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Punchy" if "AgX - Punchy" in [
        i.identifier for i in scene.view_settings.bl_rna.properties["look"].enum_items] else "None"
    try:
        r.image_settings.media_type = "VIDEO"
    except Exception:
        pass
    try:
        r.image_settings.file_format = "FFMPEG"
        r.ffmpeg.format = "MPEG4"
        r.ffmpeg.codec = "H264"
        r.ffmpeg.constant_rate_factor = "HIGH"
        r.ffmpeg.audio_codec = "AAC"
        r.ffmpeg.audio_bitrate = 320
    except Exception as e:
        print("Zyvrok: video output settings skipped ->", e)
    if not r.filepath or r.filepath == "/tmp/":
        r.filepath = "//renders/wave_"


# --------------------------------------------------------------------------
def main():
    render = parse_cli()
    path = bpy.path.abspath(AUDIO_PATH)
    if not AUDIO_PATH or not os.path.exists(path):
        raise FileNotFoundError("Zyvrok: set AUDIO_PATH at the top of the script to your song file.")

    scene = bpy.context.scene
    scene.render.fps = FPS
    print("Zyvrok: analysing audio ...")
    data, frames = analyse_audio(path, FPS)
    img = bake_to_image(data)

    clear_old()
    hide_default_cube()
    col = get_collection()
    ng = build_node_group(img, frames)

    for i, (color, height, delay, strength) in enumerate(LAYERS):
        ob = new_empty_mesh_object(f"{PREFIX}Wave_{i + 1}", col)
        ob.location.y = i * 0.3          # echoes sit slightly behind
        mod = ob.modifiers.new("ZV Wave", "NODES")
        mod.node_group = ng
        mat = emission_material(f"{PREFIX}WaveMat_{i + 1}", color, strength)
        for item in ng.interface.items_tree:
            if item.in_out != "INPUT":
                continue
            if item.name == "Height":
                mod[item.identifier] = WAVE_HEIGHT * height
            elif item.name == "Delay":
                mod[item.identifier] = float(delay)
            elif item.name == "Material":
                mod[item.identifier] = mat
            elif item.name == "Mirror":
                mod[item.identifier] = MIRROR

    setup_camera(col, scene)
    setup_logo(col)
    setup_world(scene)
    setup_render(scene)
    setup_glow(scene)
    setup_audio(scene, path, frames)
    print(f"Zyvrok: wave visualizer ready - {frames} frames at {FPS} fps.")

    if render:
        bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
