import bpy 

# This is a reskin of Map Range node to make it easier to understand for novice users
# by removing things unnecessary for microscopy data, and bounding values to tif2blender
# ranges
def bounded_map_range_node_group():
    node_group = bpy.data.node_groups.get("Bounded Map Range")
    if node_group:
        return node_group
    node_group = bpy.data.node_groups.new(type = 'ShaderNodeTree', name = "Bounded Map Range")
    links = node_group.links
    interface = node_group.interface
    nodes = node_group.nodes

    interface.new_socket("Data",in_out="INPUT",socket_type='NodeSocketFloat')
    interface.items_tree[-1].attribute_domain = 'POINT'

    interface.new_socket("Minimum",in_out="INPUT",socket_type='NodeSocketFloat')
    interface.items_tree[-1].default_value = 0.0
    interface.items_tree[-1].min_value = 0.0
    interface.items_tree[-1].max_value = 1.0
    interface.items_tree[-1].attribute_domain = 'POINT'

    interface.new_socket("Maximum",in_out="INPUT",socket_type='NodeSocketFloat')
    interface.items_tree[-1].default_value = 1.0
    interface.items_tree[-1].min_value = 0.0
    interface.items_tree[-1].max_value = 1.0
    interface.items_tree[-1].attribute_domain = 'POINT'
    
    interface.new_socket("Intensity",in_out="INPUT",socket_type='NodeSocketFloat')
    interface.items_tree[-1].default_value = 1
    interface.items_tree[-1].min_value = 0.0
    interface.items_tree[-1].max_value = 10000.0
    interface.items_tree[-1].attribute_domain = 'POINT'

    interface.new_socket("Rescaled Data",in_out="OUTPUT",socket_type='NodeSocketFloat')
    interface.items_tree[-1].attribute_domain = 'POINT'

    group_input = node_group.nodes.new("NodeGroupInput")
    group_input.location = (-200,0)
    
    map_range = nodes.new(type='ShaderNodeMapRange')
    map_range.location = (0, 0)
    links.new(group_input.outputs.get('Data'), map_range.inputs.get('Value'))
    links.new(group_input.outputs.get('Minimum'), map_range.inputs.get('From Min'))
    links.new(group_input.outputs.get('Maximum'), map_range.inputs.get('From Max'))
    links.new(group_input.outputs.get('Intensity'), map_range.inputs.get('To Max'))

    group_output = node_group.nodes.new("NodeGroupOutput")
    group_output.location = (200,0)
    links.new(map_range.outputs.get('Result'), group_output.inputs[0])
    return node_group