import bpy

def remap_oid_node():
    node_group = bpy.data.node_groups.get("Labelmask Remap Switch")
    if node_group:
        return node_group
    node_group= bpy.data.node_groups.new(type = 'ShaderNodeTree', name = "Labelmask Remap Switch")
    links = node_group.links
    interface = node_group.interface

    interface.new_socket("Value", in_out="INPUT",socket_type='NodeSocketFloat')
    interface.items_tree[-1].attribute_domain = 'POINT'
    interface.new_socket("Revolving Colormap", in_out="INPUT",socket_type='NodeSocketBool')
    interface.items_tree[-1].default_value = True
    interface.items_tree[-1].attribute_domain = 'POINT'
    interface.new_socket("# Colors", in_out="INPUT",socket_type='NodeSocketInt')
    interface.items_tree[-1].default_value = 10
    interface.items_tree[-1].attribute_domain = 'POINT'
    interface.items_tree[-1].min_value = 0
    interface.items_tree[-1].max_value = 32
    interface.new_socket("# Objects", in_out="INPUT",socket_type='NodeSocketInt')
    interface.items_tree[-1].default_value = 100
    interface.items_tree[-1].attribute_domain = 'POINT'
    interface.items_tree[-1].min_value = 0

    interface.new_socket("Fac", in_out="OUTPUT",socket_type='NodeSocketFloat')
    interface.items_tree[-1].attribute_domain = 'POINT'
    
    group_input = node_group.nodes.new("NodeGroupInput")
    group_input.location = (0,0)

    mod = node_group.nodes.new("ShaderNodeMath")
    mod.location = (200, 0)
    mod.operation = "MODULO"
    links.new(group_input.outputs.get("Value"), mod.inputs[0])
    links.new(group_input.outputs.get("# Colors"), mod.inputs[1])
    
    add = node_group.nodes.new("ShaderNodeMath")
    add.location = (200, -200)
    add.operation = "ADD"
    links.new(group_input.outputs.get("# Colors"), add.inputs[0])
    add.inputs[1].default_value = 1

    map_range = node_group.nodes.new("ShaderNodeMapRange")
    map_range.location = (400, 0)
    links.new(mod.outputs[0], map_range.inputs[0])
    links.new(add.outputs[0], map_range.inputs[2])

    map_range2 = node_group.nodes.new("ShaderNodeMapRange")
    map_range2.location = (400, -300)
    links.new(group_input.outputs.get('Value'), map_range2.inputs[0])
    links.new(group_input.outputs.get('# Objects'), map_range2.inputs[2])
    
    mix = node_group.nodes.new("ShaderNodeMix")
    mix.location = (600, -100)
    links.new(group_input.outputs.get('Revolving Colormap'), mix.inputs[0])
    links.new(map_range.outputs[0], mix.inputs[3])
    links.new(map_range2.outputs[0], mix.inputs[2])

    group_output = node_group.nodes.new("NodeGroupOutput")
    group_output.location = (800, -100)
    links.new(mix.outputs[0], group_output.inputs[0])
    return node_group