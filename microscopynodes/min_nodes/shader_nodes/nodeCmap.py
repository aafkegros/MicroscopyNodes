import bpy
from .nodeIgnoreExtremes import ignore_extremes_node_group
import cmap



def cmap_node(cmap_name):
    # decorates the color ramp with convenience functions especially useful for volumes
    # node_group = bpy.data.node_groups.get(cmap_name)
    # if node_group:
    #     return node_group
    node_group= bpy.data.node_groups.new(type = 'ShaderNodeTree', name = cmap_name)
    links = node_group.links
    interface = node_group.interface

    interface.new_socket("Value", in_out="INPUT",socket_type='NodeSocketFloat')
    interface.items_tree[-1].attribute_domain = 'POINT'
    interface.new_socket("Invert", in_out="INPUT",socket_type='NodeSocketBool')
    interface.items_tree[-1].default_value = False
    interface.items_tree[-1].attribute_domain = 'POINT'
    interface.new_socket("Alpha Multiplier", in_out="INPUT",socket_type='NodeSocketFloat')
    interface.items_tree[-1].default_value = 0.1
    interface.items_tree[-1].attribute_domain = 'POINT'
    interface.items_tree[-1].min_value = 0.0
    interface.items_tree[-1].max_value = 100.0
    interface.new_socket("Constant Alpha", in_out="INPUT",socket_type='NodeSocketBool')
    interface.items_tree[-1].default_value = True
    interface.items_tree[-1].attribute_domain = 'POINT'
    interface.new_socket("Ignore 0", in_out="INPUT",socket_type='NodeSocketBool')
    interface.items_tree[-1].default_value = True
    interface.items_tree[-1].attribute_domain = 'POINT'
    interface.new_socket("Ignore 1", in_out="INPUT",socket_type='NodeSocketBool')
    interface.items_tree[-1].default_value = False
    interface.items_tree[-1].attribute_domain = 'POINT'

    interface.new_socket("Color", in_out="OUTPUT",socket_type='NodeSocketColor')
    interface.items_tree[-1].attribute_domain = 'POINT'
    interface.new_socket("Alpha", in_out="OUTPUT",socket_type='NodeSocketFloat')
    interface.items_tree[-1].attribute_domain = 'POINT'
    
    group_input = node_group.nodes.new("NodeGroupInput")
    group_input.location = (0,0)
    
    # -- COLOR -- 
    mul_add = node_group.nodes.new("ShaderNodeMath")
    mul_add.inputs[1].default_value = -1.0
    mul_add.location = (200, 100)
    mul_add.operation = "MULTIPLY_ADD"
    links.new(group_input.outputs.get('Value'), mul_add.inputs[0])
    links.new(group_input.outputs.get('Invert'), mul_add.inputs[2])

    absolute = node_group.nodes.new("ShaderNodeMath")
    absolute.location = (400,100)
    absolute.operation = "ABSOLUTE"
    links.new(mul_add.outputs[0], absolute.inputs[0])

    ramp_node = node_group.nodes.new(type="ShaderNodeValToRGB")
    ramp_node.location = (600, 100)
    ramp_node.width = 300
    set_color_ramp(cmap_name, ramp_node)
    links.new(absolute.outputs[0], ramp_node.inputs.get('Fac'))

    # -- ALPHA extremes/mult -- 
    ignore_extremes = node_group.nodes.new('ShaderNodeGroup')
    ignore_extremes.node_tree = ignore_extremes_node_group()
    ignore_extremes.location = (200, -100)
    ignore_extremes.show_options = False
    links.new(group_input.outputs.get('Value'), ignore_extremes.inputs.get('Value'))
    links.new(group_input.outputs.get('Ignore 0'), ignore_extremes.inputs.get('Ignore 0'))
    links.new(group_input.outputs.get('Ignore 1'), ignore_extremes.inputs.get('Ignore 1'))

    mult = node_group.nodes.new("ShaderNodeMath")
    mult.location = (400, -100)
    mult.operation = "MULTIPLY"
    links.new(group_input.outputs.get("Alpha Multiplier"), mult.inputs[0])
    links.new(ignore_extremes.outputs[0], mult.inputs[1])

    # -- Constant alpha -- 
    less = node_group.nodes.new("ShaderNodeMath")
    less.location = (200, -250)
    less.operation = "LESS_THAN"
    links.new(group_input.outputs.get("Constant Alpha"), less.inputs[0])

    mult2 = node_group.nodes.new("ShaderNodeMath")
    mult2.location = (400, -250)
    mult2.operation = "MULTIPLY_ADD"
    links.new(group_input.outputs.get("Value"), mult2.inputs[0])
    links.new(less.outputs[0], mult2.inputs[1])
    links.new(group_input.outputs.get("Constant Alpha"), mult2.inputs[2])


    mult3 = node_group.nodes.new("ShaderNodeMath")
    mult3.location = (600, -150)
    mult3.operation = "MULTIPLY"
    links.new(mult.outputs[0], mult3.inputs[0])
    links.new(mult2.outputs[0], mult3.inputs[1])

    group_output = node_group.nodes.new("NodeGroupOutput")
    group_output.location = (1000, 0)
    links.new(ramp_node.outputs[0], group_output.inputs[0])
    links.new(mult3.outputs[0], group_output.inputs[1])

    return node_group

def set_color_ramp(name, ramp_node):
    lut = cmap.Colormap(name).lut(min(len(cmap.Colormap(name).lut()), 32))
    linear = (cmap.Colormap(name) == 'linear')
    for ix, color in enumerate(lut):
        if len(ramp_node.color_ramp.elements) <= ix:
            ramp_node.color_ramp.elements.new(ix/(len(lut)-linear))
        ramp_node.color_ramp.elements[ix].position = ix/(len(lut)-linear)
        ramp_node.color_ramp.elements[ix].color = (color[0],color[1],color[2],color[3])
    if not linear:
        ramp_node.color_ramp.interpolation = "CONSTANT"
    ramp_node.label = name
    return
