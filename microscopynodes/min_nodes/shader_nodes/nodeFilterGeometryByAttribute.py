import bpy


def filter_geometry_by_attribute_node():
    node_group = bpy.data.node_groups.get("Filter Geometry by Attribute")
    if node_group:
        return node_group

    node_group = bpy.data.node_groups.new(
        type='ShaderNodeTree',
        name="Filter Geometry by Attribute",
    )
    links = node_group.links
    interface = node_group.interface
    nodes = node_group.nodes

    interface.new_socket("Attribute", in_out="OUTPUT", socket_type='NodeSocketFloat')
    interface.items_tree[-1].attribute_domain = 'POINT'

    interface.new_socket("Attribute", in_out="INPUT", socket_type='NodeSocketFloat')
    interface.items_tree[-1].default_value = 0.0
    interface.items_tree[-1].attribute_domain = 'POINT'

    group_input = nodes.new("NodeGroupInput")
    group_input.location = (-380, 0)

    compare = nodes.new("ShaderNodeMath")
    compare.location = (-120, 90)
    compare.operation = 'GREATER_THAN'
    compare.inputs[1].default_value = 0.5
    links.new(group_input.outputs["Attribute"], compare.inputs[0])

    group_output = nodes.new("NodeGroupOutput")
    group_output.location = (120, 0)
    group_output.is_active_output = True
    links.new(compare.outputs[0], group_output.inputs["Attribute"])

    return node_group
