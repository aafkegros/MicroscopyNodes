import bpy
from .nodeIgnoreExtremes import ignore_extremes_node_group
import cmap


def volume_alpha_node():
    node_group = bpy.data.node_groups.get("Volume Transparency")
    if node_group and node_group.interface.items_tree.get("Alpha-Intensity Coupling"):
        return node_group
    node_group= bpy.data.node_groups.new(type = 'ShaderNodeTree', name = "Volume Transparency")
    links = node_group.links
    interface = node_group.interface

    interface.new_socket("Value", in_out="INPUT",socket_type='NodeSocketFloat')
    interface.items_tree[-1].attribute_domain = 'POINT'
    interface.new_socket("Clip Min", in_out="INPUT",socket_type='NodeSocketBool')
    interface.items_tree[-1].default_value = True
    interface.items_tree[-1].attribute_domain = 'POINT'
    interface.new_socket("Clip Max", in_out="INPUT",socket_type='NodeSocketBool')
    interface.items_tree[-1].default_value = False
    interface.items_tree[-1].attribute_domain = 'POINT'
    interface.new_socket("Alpha", in_out="INPUT",socket_type='NodeSocketFloat')
    interface.items_tree[-1].default_value = 1.0
    interface.items_tree[-1].attribute_domain = 'POINT'
    interface.items_tree[-1].min_value = 0.0
    interface.items_tree[-1].max_value = 100.0
    interface.new_socket("Alpha-Intensity Coupling", in_out="INPUT",socket_type='NodeSocketFloat')
    interface.items_tree[-1].default_value = 1.0
    interface.items_tree[-1].attribute_domain = 'POINT'
    interface.items_tree[-1].min_value = 0.0
    interface.items_tree[-1].max_value = 1.0
    interface.items_tree[-1].subtype = 'FACTOR'

    interface.new_socket("Alpha", in_out="OUTPUT",socket_type='NodeSocketFloat')
    interface.items_tree[-1].attribute_domain = 'POINT'
    interface.new_socket("Alpha-Intensity Coupling", in_out="OUTPUT",socket_type='NodeSocketFloat')
    interface.items_tree[-1].attribute_domain = 'POINT'
    
    group_input = node_group.nodes.new("NodeGroupInput")
    group_input.location = (0,0)

    # -- ALPHA extremes/mult -- 
    ignore_extremes = node_group.nodes.new('ShaderNodeGroup')
    ignore_extremes.node_tree = ignore_extremes_node_group()
    ignore_extremes.location = (200, -260)
    ignore_extremes.show_options = False
    links.new(group_input.outputs.get('Value'), ignore_extremes.inputs.get('Value'))
    links.new(group_input.outputs.get('Clip Min'), ignore_extremes.inputs.get('Ignore 0'))
    links.new(group_input.outputs.get('Clip Max'), ignore_extremes.inputs.get('Ignore 1'))

    value_by_influence = node_group.nodes.new("ShaderNodeMath")
    value_by_influence.location = (200, -20)
    value_by_influence.operation = "MULTIPLY"
    links.new(group_input.outputs.get("Value"), value_by_influence.inputs[0])
    links.new(group_input.outputs.get("Alpha-Intensity Coupling"), value_by_influence.inputs[1])

    inverse_influence = node_group.nodes.new("ShaderNodeMath")
    inverse_influence.location = (200, 120)
    inverse_influence.operation = "SUBTRACT"
    inverse_influence.inputs[0].default_value = 1.0
    links.new(group_input.outputs.get("Alpha-Intensity Coupling"), inverse_influence.inputs[1])

    constant_to_linear = node_group.nodes.new("ShaderNodeMath")
    constant_to_linear.location = (400, 20)
    constant_to_linear.operation = "ADD"
    links.new(inverse_influence.outputs[0], constant_to_linear.inputs[0])
    links.new(value_by_influence.outputs[0], constant_to_linear.inputs[1])

    alpha_mult = node_group.nodes.new("ShaderNodeMath")
    alpha_mult.location = (600, -50)
    alpha_mult.operation = "MULTIPLY"
    links.new(constant_to_linear.outputs[0], alpha_mult.inputs[0])
    links.new(group_input.outputs.get("Alpha"), alpha_mult.inputs[1])

    clip_mult = node_group.nodes.new("ShaderNodeMath")
    clip_mult.location = (800, -100)
    clip_mult.operation = "MULTIPLY"
    links.new(alpha_mult.outputs[0], clip_mult.inputs[0])
    links.new(ignore_extremes.outputs[0], clip_mult.inputs[1])

    group_output = node_group.nodes.new("NodeGroupOutput")
    group_output.location = (1000, -100)
    links.new(clip_mult.outputs[0], group_output.inputs.get("Alpha"))
    links.new(group_input.outputs.get("Alpha-Intensity Coupling"), group_output.inputs.get("Alpha-Intensity Coupling"))
    return node_group
