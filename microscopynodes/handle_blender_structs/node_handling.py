import bpy 
from .. import min_nodes
import re

def  get_nodes_last_output(group):
    # fast function for tests and non-user changed trees
    try:
        output = group.nodes['Group Output']
    except:
        output = group.nodes['Material Output']
    try:
        last = output.inputs[0].links[0].from_node
        out_input = output.inputs[0]
    except:
        last = output.inputs[1].links[0].from_node
        out_input = output.inputs[1]
    return last, output, out_input

def get_safe_nodes_last_output(group, make=False):
    # safer function for getting last node for user changable trees
    # still does not handle multiple output nodes
    try:
        return get_nodes_last_output(group)
    except:
        pass
    xval = 0
    output = None
    for node in reversed(group.nodes): 
        if node.type == "GROUP_OUTPUT":
            output = node
        xval = max(xval, node.location[0])
    if output is None and make == False:
        return None, None, None
    if output is None and make == True:
        output = group.nodes.new('NodeGroupOutput')
        output.location = (xval + 200, 0)
    if len(output.inputs[0].links) == 0:
        return None, output, None
    try:
        last = output.inputs[0].links[0].from_node
        out_input = output.inputs[0]
    except:
        last = output.inputs[1].links[0].from_node
        out_input = output.inputs[1]
    return last, output, out_input

def get_safe_node_input(group, make=False):
    innode = None
    xval = 100
    for node in reversed(group.nodes): 
        if node.type == "GROUP_INPUT":
            innode = node
        xval = min(xval, node.location[0])
    if innode is None and make==True:
        output = group.nodes.new('NodeGroupInput')
        output.location = (xval - 300, 0)
    return innode

def insert_last_node(group, node, move = True, safe=False):
    if safe:
        last, output, out_input = get_safe_nodes_last_output(group, make=True)
    else:
        last, output, out_input = get_nodes_last_output(group)
    link = group.links.new
    location = output.location
    output.location = [location[0] + 300, location[1]]
    node.location = [location[0] - 300, location[1]]
    if last is not None:
        link(last.outputs[0], node.inputs[0])
    link(node.outputs[0], output.inputs[0])

def realize_instances(obj):
    group = obj.modifiers['GeometryNodes'].node_group
    realize = group.nodes.new('GeometryNodeRealizeInstances')
    insert_last_node(group, realize)

def append(node_name, link = False):
    node = bpy.data.node_groups.get(node_name)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if not node or link:
            bpy.ops.wm.append(
                directory = os.path.join(mn_data_file, 'NodeTree'), 
                filename = node_name, 
                link = link
            )
    
    return bpy.data.node_groups[node_name]

def get_min_gn(obj):
    for mod in obj.modifiers:
        if 'Microscopy Nodes' in mod.name:
            return mod
    return None



MIN_SOCKET_TYPES = {
    'SWITCH' : "",
    'VOXEL_SIZE' : "Voxel Size",
    'THRESHOLD' : "Threshold"
}

def new_socket(node_group, ch, type, min_type, internal_append="", ix=None):
    node_group.interface.new_socket(name="socket name not set", in_out="INPUT",socket_type=type)
    socket = node_group.interface.items_tree[-1]

    internalname = f"{ch['identifier']}_{min_type}_{internal_append}"
    socket.default_attribute_name = f"[{internalname}]"
    set_name_socket(socket, ch['name'])
    if ix is not None:
        node_group.interface.move(socket, ix)
    return socket

def set_name_socket(socket, ch_name):
    for min_type in MIN_SOCKET_TYPES:
        if min_type in socket.default_attribute_name:
            socket.name =  " ".join([ch_name, MIN_SOCKET_TYPES[min_type]])
    return

def get_socket(node_group, ch, min_type, return_ix=False, internal_append=""):
    for ix, socket in enumerate(node_group.interface.items_tree):
        if re.search(string=socket.default_attribute_name, pattern=f"{ch['identifier']}_{min_type}_{internal_append}+") is not None:
            if return_ix:
                return node_group.interface.items_tree[ix], ix
            return node_group.interface.items_tree[ix]
    if return_ix:
        return None, None
    return None


def insert_slicing(group, slice_obj):
    nodes = group.nodes
    links = group.links
    lastnode, outnode, output_input = get_nodes_last_output(group)
    texcoord = nodes.new('ShaderNodeTexCoord')
    texcoord.object = slice_obj
    texcoord.width = 200
    texcoord.location = (outnode.location[0], outnode.location[1]+100)

    slicecube = nodes.new('ShaderNodeGroup')
    slicecube.node_tree = min_nodes.slice_cube_node_group()
    slicecube.name = "Slice Cube"
    slicecube.width = 250
    slicecube.location = (outnode.location[0]+ 270, outnode.location[1])
    links.new(texcoord.outputs.get('Object'),slicecube.inputs.get('Slicing Object'))


    links.new(lastnode.outputs[0], slicecube.inputs.get("Shader"))
    links.new(slicecube.outputs.get("Shader"), output_input)
    outnode.location = (outnode.location[0]+550, outnode.location[1])
    return

