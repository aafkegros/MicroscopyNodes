import bpy
from pathlib import Path
import re

LOC = Path(bpy.path.abspath("//"))
OUT_DIR = LOC / Path("geo_screenshots")


def ensure_out_dir():
    OUT_DIR.mkdir(parents=True, exist_ok=True)


def log_debug(message):
    print(f"[geo_screenshots] {message}")


def sanitize(text):
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", text.strip())
    return text.strip("_") or "unnamed"


def find_node_editor():
    window = bpy.context.window
    screen = window.screen
    for area in screen.areas:
        if area.type == "NODE_EDITOR":
            region = next(r for r in area.regions if r.type == "WINDOW")
            return window, screen, area, region, area.spaces.active
    raise RuntimeError("No NODE_EDITOR area open")


def active_geometry_object():
    obj = bpy.context.view_layer.objects.active
    if obj is None:
        raise RuntimeError("No active object")
    return obj


def active_geometry_modifier(obj):
    mod = obj.modifiers.active
    if mod is not None and mod.type == "NODES":
        return mod

    for mod in obj.modifiers:
        if mod.type == "NODES":
            return mod

    raise RuntimeError(f"No active Geometry Nodes modifier found on {obj.name}")


def selected_node_names(node_tree):
    names = [node.name for node in node_tree.nodes if node.select]
    if not names:
        raise RuntimeError("No selected nodes in the current Geometry Nodes tree")
    return names


def build_output_path(obj, node_tree, node_names):
    object_part = sanitize(obj.name)
    if len(node_names) == len(node_tree.nodes):
        node_part = "All"
    else:
        node_part = "__".join(sanitize(name) for name in node_names[:4])
        if len(node_names) > 4:
            node_part += f"__plus_{len(node_names) - 4}"
    return OUT_DIR / f"{object_part}__{node_part}.png"


def capture_current_geo_view():
    ensure_out_dir()

    obj = active_geometry_object()
    mod = active_geometry_modifier(obj)
    node_tree = mod.node_group
    if node_tree is None:
        raise RuntimeError(f"Active modifier on {obj.name} has no node group")

    node_names = selected_node_names(node_tree)
    filepath = build_output_path(obj, node_tree, node_names)

    window, screen, area, region, space = find_node_editor()
    area.ui_type = "GeometryNodeTree"
    if hasattr(space, "geometry_nodes_type"):
        space.geometry_nodes_type = "MODIFIER"
    if hasattr(space, "node_tree"):
        space.node_tree = node_tree

    with bpy.context.temp_override(
        window=window,
        screen=screen,
        area=area,
        region=region,
        space_data=space,
    ):
        bpy.ops.screen.screenshot_area(filepath=str(filepath))

    log_debug(f"Object: {obj.name}")
    log_debug(f"Nodes: {node_names}")
    log_debug(f"Saved screenshot: {filepath}")
    return filepath


def main():
    capture_current_geo_view()


if __name__ == "__main__":
    main()
