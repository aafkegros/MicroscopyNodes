import bpy 
import re

def expand_node_ui(node):
    if hasattr(node, "show_options"):
        node.show_options = True
    for socket in getattr(node, "inputs", []):
        if hasattr(socket, "show_expanded"):
            socket.show_expanded = True
    return node

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
        innode = group.nodes.new('NodeGroupInput')
        innode.location = (xval - 300, 0)
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

def get_interface_input(node_group, name):
    for item in node_group.interface.items_tree:
        if getattr(item, "item_type", None) == 'SOCKET' and item.in_out == 'INPUT' and item.name == name:
            return item
    raise KeyError(f"Input socket '{name}' not found")

def modifier_input(modifier, socket):
    return getattr(modifier.properties.inputs, socket.identifier)

def set_modifier_input_socket(modifier, socket, value):
    modifier_input(modifier, socket).value = value

def get_modifier_input_socket(modifier, socket):
    return modifier_input(modifier, socket).value

def set_modifier_input(modifier, name, value):
    item = get_interface_input(modifier.node_group, name)
    set_modifier_input_socket(modifier, item, value)

def get_readable_enum(enum_name, enum):
    return bpy.context.scene.bl_rna.properties[enum_name].enum_items[enum].name


MIN_SOCKET_TYPES = {
    'SWITCH' : "",
    'VOXEL_SIZE' : "Voxel Size",
    'THRESHOLD' : "Threshold"
}

# Specific for channel objects, so should move this code there at some point

def new_socket(node_group, ch, type, min_type, internal_append="", ix=None):
    node_group.interface.new_socket(name="socket name not set", in_out="INPUT",socket_type=type)
    socket = node_group.interface.items_tree[-1]

    internalname = f"{ch.identifier}_{min_type}_{internal_append}"
    socket.default_attribute_name = f"[{internalname}]"
    set_name_socket(socket, ch.name)
    if ix is not None:
        node_group.interface.move(socket, ix)
    return socket

def group_input_output_for_socket(group_input_node, interface_socket):
    for socket_key in (
        getattr(interface_socket, "identifier", None),
        getattr(interface_socket, "name", None),
    ):
        if socket_key is None:
            continue
        output = group_input_node.outputs.get(socket_key)
        if output is not None:
            return output
    raise ValueError(
        f"Could not find group input output for socket "
        f"{getattr(interface_socket, 'name', None)!r} "
        f"({getattr(interface_socket, 'identifier', None)!r})"
    )

def set_name_socket(socket, ch_name):
    for min_type in MIN_SOCKET_TYPES:
        if min_type in getattr(socket, "default_attribute_name", ""):
            socket.name =  " ".join([ch_name, MIN_SOCKET_TYPES[min_type]])
    return

def get_socket(node_group, ch, min_type, return_ix=False, internal_append=""):
    for ix, socket in enumerate(node_group.interface.items_tree):
        default_attribute_name = getattr(socket, "default_attribute_name", "")
        if re.search(string=default_attribute_name, pattern=f"{ch.identifier}_{min_type}_{internal_append}+") is not None:
            if return_ix:
                return node_group.interface.items_tree[ix], ix
            return node_group.interface.items_tree[ix]
    if return_ix:
        return None, None
    return None

def get_socket_by_name(node_group, name, return_ix=False):
    for ix, socket in enumerate(node_group.interface.items_tree):
        default_attribute_name = getattr(socket, "default_attribute_name", "")
        if re.search(string=default_attribute_name, pattern=f"{name}") is not None:
            if return_ix:
                return node_group.interface.items_tree[ix], ix
            return node_group.interface.items_tree[ix]

SLICE_CUBE_SHADER_NODE = "[Microscopy Nodes Slice Cube]"
SLICE_CUBE_TEXCOORD_NODE = "[Microscopy Nodes Slice Cube Coordinates]"


def layout_slicing_nodes(slicecube, texcoord, source_node, output_node):
    common_parent = source_node.parent
    if output_node.parent != common_parent:
        common_parent = None
    slicecube.parent = common_parent
    texcoord.parent = common_parent

    previous_shift = float(slicecube.get("output_shift_x", 0.0))
    if previous_shift:
        output_node.location = (
            output_node.location[0] - previous_shift,
            output_node.location[1],
        )
        del slicecube["output_shift_x"]

    source_right = source_node.location[0] + source_node.width
    output_left = output_node.location[0]
    gap = output_left - source_right
    center_y = (source_node.location[1] + output_node.location[1]) / 2
    slicecube.location = (
        source_right + (gap - slicecube.width) / 2,
        center_y,
    )
    texcoord.location = (
        source_right + (gap - texcoord.width) / 2,
        center_y + 220,
    )


def insert_slicing(group, slice_obj):
    from ..min_nodes.shader_nodes import slice_cube_node_group

    nodes = group.nodes
    links = group.links
    existing = nodes.get(SLICE_CUBE_SHADER_NODE)
    if existing is not None:
        texcoord = nodes.get(SLICE_CUBE_TEXCOORD_NODE)
        if texcoord is not None:
            texcoord.object = slice_obj
            shader_input = existing.inputs.get("Shader")
            shader_output = existing.outputs.get("Shader")
            if shader_input.links and shader_output.links:
                layout_slicing_nodes(
                    existing,
                    texcoord,
                    shader_input.links[0].from_node,
                    shader_output.links[0].to_node,
                )
        return existing

    lastnode, outnode, output_input = get_nodes_last_output(group)
    source_socket = output_input.links[0].from_socket

    texcoord = nodes.new('ShaderNodeTexCoord')
    texcoord.name = SLICE_CUBE_TEXCOORD_NODE
    texcoord.label = "Slice Cube Coordinates"
    texcoord.object = slice_obj
    texcoord.width = 200
    for output in texcoord.outputs:
        output.hide = output.name != 'Object'

    slicecube = nodes.new('ShaderNodeGroup')
    slicecube.node_tree = slice_cube_node_group()
    slicecube.name = SLICE_CUBE_SHADER_NODE
    slicecube.label = "Slice Cube"
    slicecube.width = 250
    links.new(texcoord.outputs.get('Object'),slicecube.inputs.get('Slicing Object'))
    
    slicecube.inputs[0].show_expanded = True
    if len(lastnode.inputs) > 0: 
        lastnode.inputs[0].show_expanded = True

    links.remove(output_input.links[0])
    links.new(source_socket, slicecube.inputs.get("Shader"))
    links.new(slicecube.outputs.get("Shader"), output_input)
    layout_slicing_nodes(slicecube, texcoord, lastnode, outnode)
    return slicecube


def remove_slicing(group):
    nodes = group.nodes
    links = group.links
    slicecube = nodes.get(SLICE_CUBE_SHADER_NODE)
    if slicecube is None:
        return

    shader_input = slicecube.inputs.get("Shader")
    shader_output = slicecube.outputs.get("Shader")
    source_socket = shader_input.links[0].from_socket if shader_input.links else None
    target_sockets = [link.to_socket for link in shader_output.links]
    output_shift_x = float(slicecube.get("output_shift_x", 0.0))
    if source_socket is not None:
        for target_socket in target_sockets:
            links.new(source_socket, target_socket)
            target_node = target_socket.node
            target_node.location = (
                target_node.location[0] - output_shift_x,
                target_node.location[1],
            )

    nodes.remove(slicecube)
    texcoord = nodes.get(SLICE_CUBE_TEXCOORD_NODE)
    if texcoord is not None:
        nodes.remove(texcoord)
