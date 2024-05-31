import bpy 
from .nodeElementWiseCompare import element_wise_compare_node_group

def slice_cube_node_group():
    node_group = bpy.data.node_groups.get("Slice Cube")
    if node_group:
        return node_group
    node_group = bpy.data.node_groups.new(type = 'ShaderNodeTree', name = "Slice Cube")
    links = node_group.links
    interface = node_group.interface
    nodes = node_group.nodes

    interface.new_socket("Shader",in_out="INPUT",socket_type='NodeSocketShader')
    interface.items_tree[-1].attribute_domain = 'POINT'

    interface.new_socket("Slicing Object",in_out="INPUT",socket_type='NodeSocketVector')
    interface.items_tree[-1].attribute_domain = 'POINT'
    
    interface.new_socket("Shader",in_out="OUTPUT",socket_type='NodeSocketShader')
    interface.items_tree[-1].attribute_domain = 'POINT'

    group_input = node_group.nodes.new("NodeGroupInput")
    group_input.location = (-200,0)
    
    less_than = nodes.new('ShaderNodeGroup')
    less_than.node_tree = element_wise_compare_node_group("LESS_THAN")
    less_than.width = 250
    less_than.location = (0, 150)
    links.new(group_input.outputs.get('Slicing Object'),less_than.inputs.get('Vector'))
    less_than.inputs.get('Value').default_value = -1

    greater_than = nodes.new('ShaderNodeGroup')
    greater_than.node_tree = element_wise_compare_node_group("GREATER_THAN")
    greater_than.width = 250
    greater_than.location = (0, -150)
    links.new(group_input.outputs.get('Slicing Object'),greater_than.inputs.get('Vector'))
    greater_than.inputs.get('Value').default_value = 1

    add = nodes.new('ShaderNodeVectorMath')
    add.location = (300, 100)
    add.operation = "ADD"
    links.new(less_than.outputs[0], add.inputs[0])
    links.new(greater_than.outputs[0], add.inputs[1])

    comp = nodes.new("ShaderNodeMath")
    comp.location = (450, 100)
    comp.operation = 'COMPARE'
    links.new(add.outputs[0], comp.inputs[0])
    comp.inputs[1].default_value = 0
    comp.inputs[2].default_value = 0.1

    transparent = nodes.new(type='ShaderNodeBsdfTransparent')
    transparent.location = (450, -200)
    
    mix = nodes.new(type='ShaderNodeMixShader')
    mix.location =(650, -200)
    links.new(group_input.outputs.get("Shader"), mix.inputs[2])
    links.new(transparent.outputs[0], mix.inputs[1])
    links.new(comp.outputs[0], mix.inputs[0])
    

    group_output = node_group.nodes.new("NodeGroupOutput")
    group_output.location = (800,-100)
    links.new(mix.outputs[0], group_output.inputs[0])
    return node_group
    