import bpy
from .nodeIgnoreExtremes import ignore_extremes_node_group
import cmap


def volume_alpha_node():
    node_group = bpy.data.node_groups.get("Volume Transparency")
    if node_group:
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
    interface.new_socket("Alpha Baseline", in_out="INPUT",socket_type='NodeSocketFloat')
    interface.items_tree[-1].default_value = 0.2
    interface.items_tree[-1].attribute_domain = 'POINT'
    interface.items_tree[-1].min_value = 0.0
    interface.items_tree[-1].max_value = 100.0
    interface.new_socket("Alpha Multiplier", in_out="INPUT",socket_type='NodeSocketFloat')
    interface.items_tree[-1].default_value = 0.0
    interface.items_tree[-1].attribute_domain = 'POINT'
    interface.items_tree[-1].min_value = 0.0
    interface.items_tree[-1].max_value = 100.0

    interface.new_socket("Alpha", in_out="OUTPUT",socket_type='NodeSocketFloat')
    interface.items_tree[-1].attribute_domain = 'POINT'
    
    group_input = node_group.nodes.new("NodeGroupInput")
    group_input.location = (0,0)

    # -- ALPHA extremes/mult -- 
    ignore_extremes = node_group.nodes.new('ShaderNodeGroup')
    ignore_extremes.node_tree = ignore_extremes_node_group()
    ignore_extremes.location = (200, -200)
    ignore_extremes.show_options = False
    links.new(group_input.outputs.get('Value'), ignore_extremes.inputs.get('Value'))
    links.new(group_input.outputs.get('Clip Min'), ignore_extremes.inputs.get('Ignore 0'))
    links.new(group_input.outputs.get('Clip Max'), ignore_extremes.inputs.get('Ignore 1'))

    mult_add = node_group.nodes.new("ShaderNodeMath")
    mult_add.location = (200, 0)
    mult_add.operation = "MULTIPLY_ADD"
    links.new(group_input.outputs.get("Value"), mult_add.inputs[0])
    links.new(group_input.outputs.get("Alpha Multiplier"), mult_add.inputs[1])
    links.new(group_input.outputs.get("Alpha Baseline"), mult_add.inputs[2])

    mult = node_group.nodes.new("ShaderNodeMath")
    mult.location = (400, -100)
    mult.operation = "MULTIPLY"
    links.new(mult_add.outputs[0], mult.inputs[0])
    links.new(ignore_extremes.outputs[0], mult.inputs[1])

#    mult3 = node_group.nodes.new("ShaderNodeMath")
#    mult3.location = (600, -150)
#    mult3.operation = "MULTIPLY"
#    links.new(mult.outputs[0], mult3.inputs[0])
#    links.new(group_input.outputs.get("Alpha Multiplier"), mult3.inputs[1])

    group_output = node_group.nodes.new("NodeGroupOutput")
    group_output.location = (600, -100)
    links.new(mult.outputs[0], group_output.inputs[0])
#    links.new(mult3.outputs[0], group_output.inputs[1])
    return node_group