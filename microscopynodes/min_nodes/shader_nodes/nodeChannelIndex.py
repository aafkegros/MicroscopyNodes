import bpy


def channel_index_node():
    node_group = bpy.data.node_groups.get("Channel index")
    if node_group:
        return node_group

    node_group = bpy.data.node_groups.new(type='ShaderNodeTree', name="Channel index")
    links = node_group.links
    interface = node_group.interface
    nodes = node_group.nodes

    interface.new_socket("Shader", in_out="OUTPUT", socket_type='NodeSocketShader')
    interface.items_tree[-1].attribute_domain = 'POINT'

    interface.new_socket("Shader", in_out="INPUT", socket_type='NodeSocketShader')
    interface.items_tree[-1].attribute_domain = 'POINT'

    interface.new_socket("Index", in_out="INPUT", socket_type='NodeSocketInt')
    interface.items_tree[-1].default_value = 0
    interface.items_tree[-1].min_value = -2147483648
    interface.items_tree[-1].max_value = 2147483647
    interface.items_tree[-1].attribute_domain = 'POINT'

    group_input = nodes.new("NodeGroupInput")
    group_input.location = (-380, 0)

    attr = nodes.new("ShaderNodeAttribute")
    attr.location = (-180, 75)
    attr.attribute_name = "channel ix"
    attr.attribute_type = 'GEOMETRY'

    compare = nodes.new("ShaderNodeMath")
    compare.location = (-20, 90)
    compare.operation = 'COMPARE'
    compare.inputs[2].default_value = 0.1
    links.new(attr.outputs["Fac"], compare.inputs[0])
    links.new(group_input.outputs["Index"], compare.inputs[1])

    transparent = nodes.new("ShaderNodeBsdfTransparent")
    transparent.location = (-20, -90)
    transparent.inputs[0].default_value = (0.0, 0.0, 0.0, 1.0)

    mix = nodes.new("ShaderNodeMixShader")
    mix.location = (180, 78)
    links.new(compare.outputs[0], mix.inputs[0])
    links.new(transparent.outputs[0], mix.inputs[1])
    links.new(group_input.outputs["Shader"], mix.inputs[2])

    group_output = nodes.new("NodeGroupOutput")
    group_output.location = (370, 0)
    group_output.is_active_output = True
    links.new(mix.outputs[0], group_output.inputs["Shader"])

    return node_group
