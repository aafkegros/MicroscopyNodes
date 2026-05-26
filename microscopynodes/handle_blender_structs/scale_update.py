import bpy

from .dependent_props import poll_empty
from .node_handling import get_min_gn
from ..parse_inputs import parse_output_unit


def update_scene_import_scale(context=None):
    context = context or bpy.context
    scene = getattr(context, "scene", None)
    if scene is None:
        return

    scale_name = _active_import_scale(context)
    if scale_name is None:
        return

    for holder in _holder_objects(scene):
        new_base = _scale_base(holder, scale_name)
        if new_base is None:
            continue

        old_base = float(holder.get("_MiN_world_scale_base", _uniform_scale(holder)))
        if old_base == 0:
            old_base = 1.0
        ratio = new_base / old_base

        holder.scale = tuple(float(value) * ratio for value in holder.scale)
        holder.location = tuple(float(value) * ratio for value in holder.location)
        holder["_MiN_world_scale_base"] = float(new_base)

        axis_unit_scale = _axis_unit_scale(holder, scale_name)
        for axes in _axes_children(holder):
            _set_axes_world_per_unit(axes, new_base)
            axes["_MiN_axis_unit_scale"] = float(axis_unit_scale)
            axes.data.update()


def _active_import_scale(context):
    from ..ui.preferences import addon_preferences

    prefs = addon_preferences(context)
    try:
        if context.scene.MiN_unit == "AU":
            return prefs.import_scale_no_unit_spoof
    except AttributeError:
        pass
    return getattr(prefs, "import_scale", None)


def _holder_objects(scene):
    return [
        obj
        for obj in scene.objects
        if obj.type == "EMPTY" and poll_empty(scene, obj)
    ]


def _scale_base(holder, scale_name):
    if scale_name == "DEFAULT":
        return 1e-2
    data_unit = holder.get("_MiN_data_unit")
    if data_unit is None:
        return None
    return float(data_unit) / float(parse_output_unit(scale_name))


def _axis_unit_scale(holder, scale_name):
    if scale_name == "DEFAULT":
        return float(holder.get("_MiN_default_axis_unit_scale", 1.0))
    return 1.0


def _axes_children(holder):
    for child in holder.children:
        min_gn = get_min_gn(child)
        if min_gn is not None and "axes" in min_gn.name.lower():
            yield child


def _set_axes_world_per_unit(axes, value):
    modifier = get_min_gn(axes)
    if modifier is None or modifier.node_group is None:
        return

    for item in modifier.node_group.interface.items_tree:
        if getattr(item, "item_type", None) == "SOCKET" and item.in_out == "INPUT" and item.name == "World per Unit":
            modifier[item.identifier] = float(value)
            return

    scale_node = modifier.node_group.nodes.get("Scale Bars")
    if scale_node is not None and scale_node.inputs.get("World per Unit") is not None:
        scale_node.inputs["World per Unit"].default_value = float(value)

def _uniform_scale(obj):
    values = [float(value) for value in obj.scale]
    return sum(values) / max(len(values), 1)
