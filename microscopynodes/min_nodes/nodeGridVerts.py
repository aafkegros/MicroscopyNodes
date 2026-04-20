import bpy


def _combine_float_to_vector(node_group, source_socket, location):
    combine = node_group.nodes.new("ShaderNodeCombineXYZ")
    combine.location = location
    node_group.links.new(source_socket, combine.inputs["X"])
    node_group.links.new(source_socket, combine.inputs["Y"])
    node_group.links.new(source_socket, combine.inputs["Z"])
    return combine


def grid_verts_node_group():
    node_group = bpy.data.node_groups.get("_grid_verts")
    if node_group:
        return node_group

    node_group = bpy.data.node_groups.new(type='GeometryNodeTree', name="_grid_verts")
    links = node_group.links
    interface = node_group.interface

    interface.new_socket("Extent (unit)", in_out="INPUT", socket_type='NodeSocketVector')
    interface.items_tree[-1].default_value = (7.0, 5.0, 4.0)
    interface.items_tree[-1].min_value = 0.0
    interface.items_tree[-1].max_value = 10000000.0
    interface.items_tree[-1].attribute_domain = 'POINT'

    interface.new_socket("World per Unit", in_out="INPUT", socket_type='NodeSocketFloat')
    interface.items_tree[-1].default_value = 1e-6
    interface.items_tree[-1].min_value = 0.0
    interface.items_tree[-1].max_value = 3.4028234663852886e+38
    interface.items_tree[-1].attribute_domain = 'POINT'

    interface.new_socket("Boolean", in_out="OUTPUT", socket_type='NodeSocketBool')
    interface.items_tree[-1].attribute_domain = 'POINT'

    group_input = node_group.nodes.new("NodeGroupInput")
    group_input.location = (-1000, 0)

    group_output = node_group.nodes.new("NodeGroupOutput")
    group_output.location = (850, 100)

    world_per_unit_xyz = _combine_float_to_vector(
        node_group,
        group_input.outputs["World per Unit"],
        (-820, -260),
    )

    extent_world = node_group.nodes.new("ShaderNodeVectorMath")
    extent_world.operation = "MULTIPLY"
    extent_world.location = (-620, -220)
    links.new(group_input.outputs["Extent (unit)"], extent_world.inputs[0])
    links.new(world_per_unit_xyz.outputs[0], extent_world.inputs[1])

    pos = node_group.nodes.new("GeometryNodeInputPosition")
    pos.location = (-620, 140)

    pos_xyz = node_group.nodes.new("ShaderNodeSeparateXYZ")
    pos_xyz.location = (-420, 140)
    links.new(pos.outputs[0], pos_xyz.inputs[0])

    boundary_compares = [[], [], []]

    for ix, side in enumerate(["min", "max"]):
        loc = node_group.nodes.new("ShaderNodeVectorMath")
        loc.operation = "MULTIPLY"
        loc.location = (-620, -80 - 170 * ix)
        links.new(extent_world.outputs[0], loc.inputs[0])
        loc.inputs[1].default_value = (-0.5, -0.5, 0.0) if side == "min" else (0.5, 0.5, 1.0)

        loc_xyz = node_group.nodes.new("ShaderNodeSeparateXYZ")
        loc_xyz.location = (-420, -80 - 170 * ix)
        links.new(loc.outputs[0], loc_xyz.inputs[0])

        for axix in range(3):
            compare = node_group.nodes.new("FunctionNodeCompare")
            compare.data_type = 'FLOAT'
            compare.operation = 'EQUAL'
            compare.mode = 'ELEMENT'
            compare.location = (-210, 320 - (ix * 3 + axix) * 140)
            links.new(pos_xyz.outputs[axix], compare.inputs[0])
            links.new(loc_xyz.outputs[axix], compare.inputs[1])
            boundary_compares[axix].append(compare)

    on_boundary = []
    for axix in range(3):
        ornode = node_group.nodes.new("FunctionNodeBooleanMath")
        ornode.operation = 'OR'
        ornode.location = (10, 100 - axix * 140)
        links.new(boundary_compares[axix][0].outputs[0], ornode.inputs[0])
        links.new(boundary_compares[axix][1].outputs[0], ornode.inputs[1])
        on_boundary.append(ornode)

    edge_xy = node_group.nodes.new("FunctionNodeBooleanMath")
    edge_xy.operation = 'AND'
    edge_xy.location = (220, 120)
    links.new(on_boundary[0].outputs[0], edge_xy.inputs[0])
    links.new(on_boundary[1].outputs[0], edge_xy.inputs[1])

    edge_yz = node_group.nodes.new("FunctionNodeBooleanMath")
    edge_yz.operation = 'AND'
    edge_yz.location = (220, -20)
    links.new(on_boundary[1].outputs[0], edge_yz.inputs[0])
    links.new(on_boundary[2].outputs[0], edge_yz.inputs[1])

    edge_zx = node_group.nodes.new("FunctionNodeBooleanMath")
    edge_zx.operation = 'AND'
    edge_zx.location = (220, -160)
    links.new(on_boundary[2].outputs[0], edge_zx.inputs[0])
    links.new(on_boundary[0].outputs[0], edge_zx.inputs[1])

    edge_or_1 = node_group.nodes.new("FunctionNodeBooleanMath")
    edge_or_1.operation = 'OR'
    edge_or_1.location = (420, 80)
    links.new(edge_xy.outputs[0], edge_or_1.inputs[0])
    links.new(edge_yz.outputs[0], edge_or_1.inputs[1])

    edge_or_2 = node_group.nodes.new("FunctionNodeBooleanMath")
    edge_or_2.operation = 'OR'
    edge_or_2.location = (620, 80)
    links.new(edge_or_1.outputs[0], edge_or_2.inputs[0])
    links.new(edge_zx.outputs[0], edge_or_2.inputs[1])

    links.new(edge_or_2.outputs[0], group_output.inputs["Boolean"])

    return node_group