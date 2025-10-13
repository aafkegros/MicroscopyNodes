import bpy

def generate_format_string(node_group, str_template, fmt_dcts):
    # if node_group is None:
    #     node_group = bpy.data.node_groups.new(type = 'GeometryNodeTree', name = "Generate Format String")
    links = node_group.links
    interface = node_group.interface
    nodes = node_group.nodes
    
    node_fmt = nodes.get("Format String")
    if node_fmt is None:
        node_fmt = nodes.new(type='FunctionNodeFormatString')
        node_fmt.location = (0, 0)
    node_fmt.inputs[0].default_value = str_template
    
    node_input = nodes.get("Group Input")
    if node_input is None:
        node_input = nodes.new("NodeGroupInput")
        node_input.location = (-200,0)
    
    template_keys = fmt_dcts[0].keys()
    for key in template_keys:
        values = [dct[key] for dct in fmt_dcts]
        if all(str(v).isdigit() for v in values):
            interface.new_socket(key,in_out="INPUT",socket_type='NodeSocketInt')
            item = node_fmt.format_items.new(socket_type='INT', name=key)
        else:
            interface.new_socket(key,in_out="INPUT",socket_type='NodeSocketString')
            item = node_fmt.format_items.new(socket_type='STRING',name=key)
        interface.items_tree[-1].attribute_domain = 'POINT'
        links.new(node_input.outputs[-2], node_fmt.inputs[-2])
    return node_fmt


# generate_format_string(None, "{aa}_b_{c}",[{'aa': '0', 'c':'hey'},{'aa': '1', 'c':'ho'}])