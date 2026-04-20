import bpy


def normalize_luminance_node():
    node_group = bpy.data.node_groups.get("Normalize Luminance")
    if node_group:
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

    interface.new_socket("Alpha Baseline", in_out="INPUT", socket_type='NodeSocketFloat')
    interface.items_tree[-1].default_value = 0.0
    interface.items_tree[-1].attribute_domain = 'POINT'

    interface.new_socket("Alpha Multiplier", in_out="INPUT", socket_type='NodeSocketFloat')
    interface.items_tree[-1].default_value = 0.0
    interface.items_tree[-1].attribute_domain = 'POINT'

    group_input = nodes.new("NodeGroupInput")
    group_input.location = (-440, 0)

    group_output = nodes.new("NodeGroupOutput")
    group_output.location = (335, 0)
    group_output.is_active_output = True

    alpha_plus_baseline = nodes.new("ShaderNodeMath")
    alpha_plus_baseline.location = (-265, -15)
    alpha_plus_baseline.operation = 'ADD'
    links.new(group_input.outputs["Alpha Baseline"], alpha_plus_baseline.inputs[0])
    links.new(group_input.outputs["Alpha Multiplier"], alpha_plus_baseline.inputs[1])

    mix_factor = nodes.new("ShaderNodeMath")
    mix_factor.location = (-95, 100)
    mix_factor.operation = 'DIVIDE'
    links.new(group_input.outputs["Alpha Multiplier"], mix_factor.inputs[0])
    links.new(alpha_plus_baseline.outputs[0], mix_factor.inputs[1])

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
    links.new(mix_factor.outputs[0], mix.inputs["Factor"])
    links.new(group_input.outputs["Color"], mix.inputs[4])
    links.new(full_value_color.outputs["Color"], mix.inputs[5])
    links.new(mix.outputs[1], group_output.inputs["Color"])

    return node_group
