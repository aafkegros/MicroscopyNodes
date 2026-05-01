import bpy


def normalize_luminance_node():
    node_group = bpy.data.node_groups.get("Normalize Luminance")
    if node_group and node_group.interface.items_tree.get("Alpha-Intensity Coupling"):
        return node_group

    node_group = bpy.data.node_groups.new(type='ShaderNodeTree', name="Normalize Luminance")
    node_group.color_tag = 'VECTOR'
    node_group.description = ""
    node_group.default_group_node_width = 140

    links = node_group.links
    interface = node_group.interface
    nodes = node_group.nodes

    interface.new_socket("Color", in_out="OUTPUT", socket_type='NodeSocketColor')
    interface.items_tree[-1].default_value = (0.0, 0.0, 0.0, 1.0)
    interface.items_tree[-1].attribute_domain = 'POINT'

    interface.new_socket("Color", in_out="INPUT", socket_type='NodeSocketColor')
    interface.items_tree[-1].default_value = (0.0, 0.0, 0.0, 1.0)
    interface.items_tree[-1].attribute_domain = 'POINT'

    interface.new_socket("Alpha-Intensity Coupling", in_out="INPUT", socket_type='NodeSocketFloat')
    interface.items_tree[-1].default_value = 1.0
    interface.items_tree[-1].attribute_domain = 'POINT'
    interface.items_tree[-1].min_value = 0.0
    interface.items_tree[-1].max_value = 1.0
    interface.items_tree[-1].subtype = 'FACTOR'

    group_input = nodes.new("NodeGroupInput")
    group_input.location = (-440, 0)

    group_output = nodes.new("NodeGroupOutput")
    group_output.location = (335, 0)
    group_output.is_active_output = True

    separate_color = nodes.new("ShaderNodeSeparateColor")
    separate_color.location = (-150, -115)
    separate_color.mode = 'HSV'
    links.new(group_input.outputs["Color"], separate_color.inputs["Color"])

    full_value_color = nodes.new("ShaderNodeCombineColor")
    full_value_color.location = (15, -60)
    full_value_color.mode = 'HSV'
    full_value_color.inputs["Blue"].default_value = 1.0
    links.new(separate_color.outputs["Red"], full_value_color.inputs["Red"])
    links.new(separate_color.outputs["Green"], full_value_color.inputs["Green"])

    mix = nodes.new("ShaderNodeMix")
    mix.location = (160, 130)
    mix.blend_type = 'MIX'
    mix.clamp_factor = True
    mix.clamp_result = False
    mix.data_type = 'VECTOR'
    mix.factor_mode = 'UNIFORM'
    links.new(group_input.outputs["Alpha-Intensity Coupling"], mix.inputs["Factor"])
    links.new(group_input.outputs["Color"], mix.inputs[4])
    links.new(full_value_color.outputs["Color"], mix.inputs[5])
    links.new(mix.outputs[1], group_output.inputs["Color"])

    return node_group
