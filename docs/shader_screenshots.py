import bpy
from pathlib import Path

LOC = Path(bpy.path.abspath("//"))
OUT_DIR = LOC / Path("shader_screenshots")
INPUT_FILE = "/Users/oanegros/Documents/werk/blender_workshop/timenuc/nuc10_eugene.tif"


def ensure_out_dir():
    OUT_DIR.mkdir(parents=True, exist_ok=True)


def purge_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    if hasattr(bpy.context.scene, "MiN_reload"):
        bpy.context.scene.MiN_reload = None


def find_node_editor():
    window = bpy.context.window
    screen = window.screen
    for area in screen.areas:
        if area.type == "NODE_EDITOR":
            region = next(r for r in area.regions if r.type == "WINDOW")
            return window, screen, area, region, area.spaces.active
    raise RuntimeError("No NODE_EDITOR area open")


def set_active_material_context(obj, mat):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    obj.active_material = mat


def set_shader_editor_context(obj, mat):
    window, screen, area, region, space = find_node_editor()
    area.ui_type = "ShaderNodeTree"
    space.shader_type = "OBJECT"
    if hasattr(space, "pin"):
        space.pin = False

    set_active_material_context(obj, mat)
    
    return window, screen, area, region, space


def deselect_all_nodes(node_tree):
    for node in node_tree.nodes:
        node.select = False


def frame_selected_nodes(obj, mat, node_names):
    node_tree = mat.node_tree
    window, screen, area, region, space = set_shader_editor_context(obj, mat)
    deselect_all_nodes(node_tree)

    active = None
    for name in node_names:
        node = node_tree.nodes.get(name)
        if node is None:
            continue
        node.select = True
        active = node

    if active is None:
        raise RuntimeError(f"No nodes found to frame: {node_names}")

    node_tree.nodes.active = active
    with bpy.context.temp_override(
        window=window,
        screen=screen,
        area=area,
        region=region,
        space_data=space,
    ):
        bpy.ops.node.view_selected()
        bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=8)


def screenshot_shader(filepath, obj, mat, node_names):
    frame_selected_nodes(obj, mat, node_names)
    window, screen, area, region, space = set_shader_editor_context(obj, mat)
    with bpy.context.temp_override(
        window=window,
        screen=screen,
        area=area,
        region=region,
        space_data=space,
    ):
        bpy.ops.screen.screenshot_area(filepath=str(filepath))
        bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=2)


def set_channel_load_modes():
    for ch in bpy.context.scene.MiN_channelList:
        ch["volume"] = True
        ch["surface"] = True
        ch["labelmask"] = (ch.ix == 1)


def load_dataset():
    bpy.context.scene.MiN_input_file = INPUT_FILE
    set_channel_load_modes()
    bpy.ops.microscopynodes.load_background()
    holder = bpy.context.scene.MiN_reload
    if holder is None:
        raise RuntimeError("Load finished without MiN_reload being set")
    return holder


def child_by_name(holder, name):
    for child in holder.children:
        if name in child.name:
            return child
    return None


def channel_frame_nodes(node_tree):
    return sorted(
        [node.name for node in node_tree.nodes if node.name.startswith("[frame_")]
    )


def channel_id_from_frame_name(frame_name):
    return frame_name.removeprefix("[frame_").removesuffix("]")


def existing_nodes(node_tree, names):
    return [name for name in names if node_tree.nodes.get(name) is not None]


def screenshot_material_set(obj, label):
    if obj is None or obj.data is None or not obj.data.materials or obj.data.materials[0] is None:
        return

    mat = obj.data.materials[0]
    node_tree = mat.node_tree
    if node_tree is None:
        return

    all_node_names = [node.name for node in node_tree.nodes]
    screenshot_shader(OUT_DIR / f"{label}_dummy.png", obj, mat, all_node_names)
    all_node_names = [node.name for node in node_tree.nodes]
    screenshot_shader(OUT_DIR / f"{label}_full.png", obj, mat, all_node_names)

    frame_node_names = channel_frame_nodes(node_tree)
    for frame_name in frame_node_names:
        safe_name = frame_name.replace("[", "").replace("]", "")
        screenshot_shader(OUT_DIR / f"{label}_{safe_name}.png", obj, mat, [frame_name])

    slice_pair = existing_nodes(node_tree, ["Slice Cube", "Texture Coordinate"])
    if slice_pair:
        screenshot_shader(OUT_DIR / f"{label}_slicecube_texcoord.png", obj, mat, slice_pair)


def screenshot_volume_extras(obj, label):
    if obj is None or obj.data is None or not obj.data.materials or obj.data.materials[0] is None:
        return
    mat = obj.data.materials[0]
    node_tree = mat.node_tree
    if node_tree is None:
        return

    for frame_name in channel_frame_nodes(node_tree):
        ch_id = channel_id_from_frame_name(frame_name)
        groups = {
            "channel_input": existing_nodes(node_tree, [f"[channel_load_{ch_id}]"]),
            "histogram_pixels": existing_nodes(node_tree, [f"[Histogram_{ch_id}]", f"[alpha_ramp_{ch_id}]"]),
            "cmap_transparency": existing_nodes(node_tree, [f"[color_lut_{ch_id}]", f"[volume_alpha_{ch_id}]"]),
            "microscopy_shading": existing_nodes(node_tree, [f"[microscopy_shading_{ch_id}]"]),
        }
        for suffix, node_names in groups.items():
            if node_names:
                screenshot_shader(OUT_DIR / f"{label}_{ch_id}_{suffix}.png", obj, mat, node_names)


def screenshot_labelmask_extras(obj, label):
    if obj is None or obj.data is None or not obj.data.materials or obj.data.materials[0] is None:
        return
    mat = obj.data.materials[0]
    node_tree = mat.node_tree
    if node_tree is None:
        return

    for frame_name in channel_frame_nodes(node_tree):
        ch_id = channel_id_from_frame_name(frame_name)
        node_names = existing_nodes(node_tree, [f"[oid_{ch_id}]", f"[remap_oid_{ch_id}]"])
        if node_names:
            screenshot_shader(OUT_DIR / f"{label}_{ch_id}_oid_remap.png", obj, mat, node_names)


def replace_labelmask_lut_tab10(obj):
    if obj is None or obj.data is None or not obj.data.materials or obj.data.materials[0] is None:
        return
    mat = obj.data.materials[0]
    node_tree = mat.node_tree
    if node_tree is None:
        return

    lut_node = next((node for node in node_tree.nodes if node.name.startswith("[color_lut_")), None)
    if lut_node is None:
        raise RuntimeError("Could not find labelmask color LUT node")

    window, screen, area, region, space = set_shader_editor_context(obj, mat)
    deselect_all_nodes(node_tree)
    lut_node.select = True
    node_tree.nodes.active = lut_node

    with bpy.context.temp_override(
        window=window,
        screen=screen,
        area=area,
        region=region,
        space_data=space,
    ):
        bpy.ops.microscopynodes.replace_lut(cmap_name="tab10")
        bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=4)

def main():
    ensure_out_dir()
    purge_scene()
    holder = load_dataset()
    volume_obj = child_by_name(holder, "volume")
    surface_obj = child_by_name(holder, "surface")
    labelmask_obj = child_by_name(holder, "labelmask")

    screenshot_material_set(volume_obj, "volume")
    screenshot_volume_extras(volume_obj, "volume")
    screenshot_material_set(surface_obj, "surface")
    screenshot_material_set(labelmask_obj, "labelmask")
    screenshot_labelmask_extras(labelmask_obj, "labelmask")

    replace_labelmask_lut_tab10(labelmask_obj)
    screenshot_material_set(labelmask_obj, "labelmask_tab10")
    screenshot_labelmask_extras(labelmask_obj, "labelmask_tab10")

    print(f"Saved screenshots to {OUT_DIR}")


if __name__ == "__main__":
    main()
