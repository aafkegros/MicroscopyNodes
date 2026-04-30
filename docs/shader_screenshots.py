import bpy
from pathlib import Path

LOC = Path(bpy.path.abspath("//"))
OUT_DIR = loc / Path("screenshots")
INPUT_FILE = "/Users/oanegros/Documents/werk/blender_workshop/timenuc/nuc10_eugene.tif"


def ensure_out_dir():
    OUT_DIR.mkdir(parents=True, exist_ok=True)


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


def warmup_screenshot_system(obj, mat):
    node_tree = mat.node_tree
    if node_tree is None or len(node_tree.nodes) == 0:
        return
    first_node = next(iter(node_tree.nodes))
    screenshot_shader(
        OUT_DIR / "_warmup.png",
        obj,
        mat,
        [first_node.name],
    )


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

    frame_node_names = sorted(
        [node.name for node in node_tree.nodes if node.name.startswith("[frame_")]
    )
    for frame_name in frame_node_names:
        safe_name = frame_name.replace("[", "").replace("]", "")
        screenshot_shader(OUT_DIR / f"{label}_{safe_name}.png", obj, mat, [frame_name])

    slice_pair = [name for name in ["Slice Cube", "Texture Coordinate"] if node_tree.nodes.get(name) is not None]
    if slice_pair:
        screenshot_shader(OUT_DIR / f"{label}_slicecube_texcoord.png", obj, mat, slice_pair)


def main():
    ensure_out_dir()
    holder = load_dataset()
    volume_obj = child_by_name(holder, "volume")
    surface_obj = child_by_name(holder, "surface")
    labelmask_obj = child_by_name(holder, "labelmask")

    screenshot_material_set(volume_obj, "volume")
    screenshot_material_set(surface_obj, "surface")
    screenshot_material_set(labelmask_obj, "labelmask")

    print(f"Saved screenshots to {OUT_DIR}")


if __name__ == "__main__":
    main()
