import bpy
import numpy as np

AXIS_ITEM_NAMES = [
    "frontface culling",
    "xy bottom",
    "yz bottom",
    "zx bottom",
    "xy top",
    "yz top",
    "zx top",
]


def _add_bundle_items(bundle_node, item_names, socket_type='BOOLEAN'):
    for name in item_names:
        bundle_node.bundle_items.new(socket_type, name)


def scalebox_node_group():
    node_group = bpy.data.node_groups.get("_scalebox")
    if node_group:
        return node_group

    node_group = bpy.data.node_groups.new(type='GeometryNodeTree', name="_scalebox")
    links = node_group.links
    interface = node_group.interface

    interface.new_socket("Extent (unit)", in_out="INPUT", socket_type='NodeSocketVector')
    interface.items_tree[-1].default_value = (7.0, 5.0, 4.0)
    interface.items_tree[-1].min_value = 0.0
    interface.items_tree[-1].max_value = 10000000.0
    interface.items_tree[-1].attribute_domain = 'POINT'

    interface.new_socket("World per Unit", in_out="INPUT", socket_type='NodeSocketVector')
    interface.items_tree[-1].default_value = (1e-6, 1e-6, 1e-6)
    interface.items_tree[-1].min_value = 0.0
    interface.items_tree[-1].max_value = 3.4028234663852886e+38
    interface.items_tree[-1].attribute_domain = 'POINT'

    interface.new_socket("Tick Step (unit)", in_out="INPUT", socket_type='NodeSocketFloat')
    interface.items_tree[-1].default_value = 1.0
    interface.items_tree[-1].min_value = 0.0
    interface.items_tree[-1].max_value = 3.4028234663852886e+38
    interface.items_tree[-1].attribute_domain = 'POINT'

    interface.new_socket("Axis Bundle", in_out="INPUT", socket_type='NodeSocketBundle')
    interface.items_tree[-1].attribute_domain = 'POINT'

    interface.new_socket("Geometry", in_out="OUTPUT", socket_type='NodeSocketGeometry')
    interface.items_tree[-1].attribute_domain = 'POINT'

    group_input = node_group.nodes.new("NodeGroupInput")
    group_input.location = (-1400, 0)

    group_output = node_group.nodes.new("NodeGroupOutput")
    group_output.location = (3100, 0)

    join_geo = node_group.nodes.new("GeometryNodeJoinGeometry")
    join_geo.location = (2200, 100)

    separate_axes = node_group.nodes.new("NodeSeparateBundle")
    separate_axes.location = (-1050, -760)
    _add_bundle_items(separate_axes, AXIS_ITEM_NAMES, 'BOOLEAN')
    links.new(group_input.outputs["Axis Bundle"], separate_axes.inputs["Bundle"])

    tick_step_xyz = node_group.nodes.new("ShaderNodeCombineXYZ")
    tick_step_xyz.location = (-1100, -170)
    links.new(group_input.outputs["Tick Step (unit)"], tick_step_xyz.inputs["X"])
    links.new(group_input.outputs["Tick Step (unit)"], tick_step_xyz.inputs["Y"])
    links.new(group_input.outputs["Tick Step (unit)"], tick_step_xyz.inputs["Z"])

    extent_world = node_group.nodes.new("ShaderNodeVectorMath")
    extent_world.operation = "MULTIPLY"
    extent_world.location = (-900, -430)
    links.new(group_input.outputs["Extent (unit)"], extent_world.inputs[0])
    links.new(group_input.outputs["World per Unit"], extent_world.inputs[1])

    loc_0 = node_group.nodes.new("ShaderNodeVectorMath")
    loc_0.operation = "MULTIPLY"
    loc_0.location = (-700, -300)
    links.new(extent_world.outputs[0], loc_0.inputs[0])
    loc_0.inputs[1].default_value = (-0.5, -0.5, -0.5)

    loc_max = node_group.nodes.new("ShaderNodeVectorMath")
    loc_max.operation = "MULTIPLY"
    loc_max.location = (-540, -300)
    links.new(extent_world.outputs[0], loc_max.inputs[0])
    loc_max.inputs[1].default_value = (0.5, 0.5, 0.5)

    ticks_float = node_group.nodes.new("ShaderNodeVectorMath")
    ticks_float.operation = "DIVIDE"
    ticks_float.location = (-900, 200)
    links.new(group_input.outputs["Extent (unit)"], ticks_float.inputs[0])
    links.new(tick_step_xyz.outputs[0], ticks_float.inputs[1])

    n_ticks_int = node_group.nodes.new("ShaderNodeVectorMath")
    n_ticks_int.operation = "CEIL"
    n_ticks_int.location = (-740, 200)
    links.new(ticks_float.outputs[0], n_ticks_int.inputs[0])

    ticks_offset = node_group.nodes.new("ShaderNodeVectorMath")
    ticks_offset.operation = "ADD"
    ticks_offset.location = (-580, 200)
    links.new(n_ticks_int.outputs[0], ticks_offset.inputs[0])
    ticks_offset.inputs[1].default_value = (1.0, 1.0, 1.0)

    overshoot_unit = node_group.nodes.new("ShaderNodeVectorMath")
    overshoot_unit.operation = "MULTIPLY"
    overshoot_unit.location = (-740, 10)
    links.new(n_ticks_int.outputs[0], overshoot_unit.inputs[0])
    links.new(tick_step_xyz.outputs[0], overshoot_unit.inputs[1])

    overshoot_world = node_group.nodes.new("ShaderNodeVectorMath")
    overshoot_world.operation = "MULTIPLY"
    overshoot_world.location = (-580, 10)
    links.new(overshoot_unit.outputs[0], overshoot_world.inputs[0])
    links.new(group_input.outputs["World per Unit"], overshoot_world.inputs[1])

    overshoot_world_xyz = node_group.nodes.new("ShaderNodeSeparateXYZ")
    overshoot_world_xyz.location = (-420, 10)
    links.new(overshoot_world.outputs[0], overshoot_world_xyz.inputs[0])

    n_ticks_xyz = node_group.nodes.new("ShaderNodeSeparateXYZ")
    n_ticks_xyz.location = (-420, 200)
    links.new(ticks_offset.outputs[0], n_ticks_xyz.inputs[0])

    planes = [
        ("xy", "bottom"),
        ("yz", "bottom"),
        ("zx", "bottom"),
        ("xy", "top"),
        ("yz", "top"),
        ("zx", "top"),
    ]

    finals = []

    for plane_index, (ax, side) in enumerate(planes):
        grid = node_group.nodes.new("GeometryNodeMeshGrid")
        grid.location = (80, 850 - plane_index * 280)

        for which, axis in enumerate("xyz"):
            if axis in ax:
                links.new(overshoot_world_xyz.outputs[which], grid.inputs[ax.find(axis)])
                links.new(n_ticks_xyz.outputs[which], grid.inputs[ax.find(axis) + 2])

        transform = node_group.nodes.new("GeometryNodeTransform")
        transform.location = (280, 850 - plane_index * 280)
        links.new(grid.outputs[0], transform.inputs[0])

        if side == "top":
            pretransform = node_group.nodes.new("ShaderNodeVectorMath")
            pretransform.operation = 'MULTIPLY'
            pretransform.location = (280, 790 - plane_index * 280)
            links.new(extent_world.outputs[0], pretransform.inputs[0])
            links.new(pretransform.outputs[0], transform.inputs["Translation"])
            shift = np.array([float(axis not in ax) for axis in "xyz"])
            pretransform.inputs[1].default_value = tuple(shift)
        else:
            pretransform = node_group.nodes.new("GeometryNodeFlipFaces")
            pretransform.location = (120, 790 - plane_index * 280)
            links.new(grid.outputs[0], pretransform.inputs[0])
            links.new(pretransform.outputs[0], transform.inputs[0])

        rot = [0, 0, 0]
        if ax == "yz":
            rot = [0.5, 0, 0.5]
        elif ax == "zx":
            rot = [0, -0.5, -0.5]
        transform.inputs["Rotation"].default_value = tuple(np.array(rot) * np.pi)

        bbox = node_group.nodes.new("GeometryNodeBoundBox")
        bbox.location = (500, 850 - plane_index * 280)
        links.new(transform.outputs[0], bbox.inputs[0])

        find_0 = node_group.nodes.new("ShaderNodeVectorMath")
        find_0.operation = "SUBTRACT"
        find_0.location = (700, 850 - plane_index * 280)
        links.new(loc_0.outputs[0], find_0.inputs[0])
        links.new(bbox.outputs[1], find_0.inputs[1])

        if side == "top":
            top_adjust = node_group.nodes.new("ShaderNodeVectorMath")
            top_adjust.operation = "MULTIPLY"
            top_adjust.location = (700, 790 - plane_index * 280)
            links.new(bbox.outputs[1], top_adjust.inputs[0])
            top_adjust.inputs[1].default_value = tuple(float(axis in ax) for axis in "xyz")
            links.new(top_adjust.outputs[0], find_0.inputs[1])

        set_pos = node_group.nodes.new("GeometryNodeSetPosition")
        set_pos.location = (900, 850 - plane_index * 280)
        links.new(transform.outputs[0], set_pos.inputs[0])
        links.new(find_0.outputs[0], set_pos.inputs["Offset"])

        enabled_socket_name = f"{ax} {side}"

        notnode = node_group.nodes.new("FunctionNodeBooleanMath")
        notnode.operation = "NOT"
        notnode.location = (1100, 850 - plane_index * 280)
        links.new(separate_axes.outputs[enabled_socket_name], notnode.inputs[0])

        delete = node_group.nodes.new("GeometryNodeDeleteGeometry")
        delete.location = (1300, 850 - plane_index * 280)
        links.new(set_pos.outputs[0], delete.inputs[0])
        links.new(notnode.outputs[0], delete.inputs["Selection"])

        finals.append(delete)

    for node in finals:
        links.new(node.outputs[0], join_geo.inputs[0])

    pos = node_group.nodes.new("GeometryNodeInputPosition")
    pos.location = (2200, -100)

    min_axis = node_group.nodes.new("ShaderNodeVectorMath")
    min_axis.operation = "MINIMUM"
    min_axis.location = (2380, -100)
    links.new(pos.outputs[0], min_axis.inputs[0])
    links.new(loc_max.outputs[0], min_axis.inputs[1])

    clip_axis = node_group.nodes.new("GeometryNodeSetPosition")
    clip_axis.location = (2600, 0)
    links.new(join_geo.outputs[0], clip_axis.inputs[0])
    links.new(min_axis.outputs[0], clip_axis.inputs["Position"])

    merge = node_group.nodes.new("GeometryNodeMergeByDistance")
    merge.location = (2850, 0)
    links.new(clip_axis.outputs[0], merge.inputs[0])

    links.new(merge.outputs[0], group_output.inputs["Geometry"])

    return node_group
