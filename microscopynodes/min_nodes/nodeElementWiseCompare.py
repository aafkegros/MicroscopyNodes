import bpy 

def element_wise_compare_node_group(operation):
    node_group = bpy.data.node_groups.get(f"Element-wise {operation}")
    if node_group:
        return node_group
    node_group = bpy.data.node_groups.new(type = 'ShaderNodeTree', name = f"Element-wise {operation}")
    links = node_group.links
    interface = node_group.interface
    nodes = node_group.nodes

    interface.new_socket("Vector",in_out="INPUT",socket_type='NodeSocketVector')
    interface.items_tree[-1].attribute_domain = 'POINT'

    interface.new_socket("Value",in_out="INPUT",socket_type='NodeSocketFloat')
    interface.items_tree[-1].attribute_domain = 'POINT'

    interface.new_socket("Vector",in_out="OUTPUT",socket_type='NodeSocketVector')
    interface.items_tree[-1].attribute_domain = 'POINT'

    group_input = node_group.nodes.new("NodeGroupInput")
    group_input.location = (-200,0)
    
    sep = nodes.new(type='ShaderNodeSeparateXYZ')
    sep.location = (0, 0)
    links.new(group_input.outputs.get('Vector'), sep.inputs.get('Vector'))
    
    comb = nodes.new(type='ShaderNodeCombineXYZ')
    comb.location = (400, 0)

    for ix, dim in enumerate("XYZ"):
        compare = nodes.new(type='ShaderNodeMath')
        compare.location = (200, ix*-200)
        compare.operation = operation
#        print(group_input.outputs.get('Value'),group_input.outputs.get('Threshold'))
        links.new(group_input.outputs.get('Value'), compare.inputs[1])
        links.new(sep.outputs.get(dim), compare.inputs.get('Value'))
        links.new(compare.outputs[0], comb.inputs.get(dim))


    group_output = node_group.nodes.new("NodeGroupOutput")
    group_output.location = (600,0)
    links.new(comb.outputs.get('Vector'), group_output.inputs[0])
    return node_group

