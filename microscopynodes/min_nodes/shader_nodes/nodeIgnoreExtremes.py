import bpy


def ignore_extremes_node_group():
    node_group = bpy.data.node_groups.get("Ignore Extremes")
    if node_group:
        return node_group
    node_group= bpy.data.node_groups.new(type = 'ShaderNodeTree', name = "Ignore Extremes")
    links = node_group.links
    interface = node_group.interface
    
    interface.new_socket("Value", in_out="INPUT",socket_type='NodeSocketFloat')
    interface.items_tree[-1].attribute_domain = 'POINT'
    interface.new_socket("Ignore 0", in_out="INPUT",socket_type='NodeSocketBool')
    interface.items_tree[-1].default_value = True
    interface.items_tree[-1].attribute_domain = 'POINT'
    interface.new_socket("Ignore 1", in_out="INPUT",socket_type='NodeSocketBool')
    interface.items_tree[-1].default_value = False
    interface.items_tree[-1].attribute_domain = 'POINT'

    group_input = node_group.nodes.new("NodeGroupInput")
    group_input.location = (0,0)

    # ignore 0
    sub = node_group.nodes.new("ShaderNodeMath")
    sub.inputs[1].default_value = 1.0
    sub.location = (400, 100)
    sub.operation = "SUBTRACT"
    links.new(group_input.outputs[1], sub.inputs[0])
    
    great = node_group.nodes.new("ShaderNodeMath")
    great.location = (600, 100)
    great.operation = "GREATER_THAN"
    links.new(group_input.outputs[0], great.inputs[0])
    links.new(sub.outputs[0], great.inputs[1])
    
    # ignore 1
    less = node_group.nodes.new("ShaderNodeMath")
    less.location = (200, -100)
    less.operation = "LESS_THAN"
    links.new(group_input.outputs[2], less.inputs[0])
    
    add = node_group.nodes.new("ShaderNodeMath")
    add.inputs[1].default_value = 1.0
    add.location = (400, -100)
    add.operation = "ADD"
    links.new(less.outputs[0], add.inputs[0])

    less2 = node_group.nodes.new("ShaderNodeMath")
    less2.location = (600, -100)
    less2.operation = "LESS_THAN"
    links.new(group_input.outputs[0], less2.inputs[0])
    links.new(add.outputs[0], less2.inputs[1])

    # combine 
    mult = node_group.nodes.new("ShaderNodeMath")
    mult.location = (800, 0)
    mult.operation = "MULTIPLY"
    links.new(great.outputs[0], mult.inputs[0])
    links.new(less2.outputs[0], mult.inputs[1])

    interface.new_socket("Value", in_out="OUTPUT",socket_type='NodeSocketFloat')
    interface.items_tree[0].attribute_domain = 'POINT'
    group_output = node_group.nodes.new("NodeGroupOutput")

    group_output.location = (1000, 0)
    links.new(mult.outputs[0], group_output.inputs[0])
    return node_group
