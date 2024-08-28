import bpy, bpy_types
from ..handle_blender_structs import *

def init_holder(name):
    if name == 'volume':
        bpy.ops.object.volume_add(align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
    else:
        bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.view_layer.objects.active
    obj.name = name

    bpy.ops.object.modifier_add(type='NODES')

    node_group = bpy.data.node_groups.new(name, 'GeometryNodeTree')  
    obj.modifiers[-1].node_group = node_group
    obj.modifiers[-1].name = f"Microscopy Nodes {name}"
    node_group.interface.new_socket(name='Geometry', in_out="OUTPUT",socket_type='NodeSocketGeometry')

    inputnode = node_group.nodes.new('NodeGroupInput')
    inputnode.location = (-900, 0)
    outnode = node_group.nodes.new('NodeGroupOutput')
    outnode.location = (800, -100)

    for dim in range(3):
        obj.lock_location[dim] = True
        obj.lock_rotation[dim] = True
        obj.lock_scale[dim] = True
    return obj

def update_holder(obj, ch_dicts, activate_key):
    gn_mod = get_min_gn(obj)
    node_group = gn_mod.node_group
    for ch in ch_dicts:
        if ch_present(obj, ch['identifier']):
            update_channel(node_group, ch) # only changes name of data
        else: 
            append_channel_to_holder(node_group, ch)
        
        gn_mod[get_socket(node_group, ch['identifier'])[0]] = bool(ch[activate_key])
    return obj

def get_min_gn(obj):
    for mod in obj.modifiers:
        if 'Microscopy Nodes' in mod.name:
            return mod
    return None


def ch_present(obj, identifier):
    return f"channel_load_{identifier}" in [node.name for node in get_min_gn(obj).node_group.nodes]

def update_channel(node_group, ch_dict):
    loadnode = node_group.nodes[f"channel_load_{ch['identifier']}"]
    loadnode.label = ch_dict['name']
    if loadnode.parent is not None:
        loadnode.parent = f"{ch_dict['name']} data"
    return

def append_channel_to_holder(node_group, ch_dict):
    # assert that layout is reasonable or make this:
    joingeo, out_node, out_input = get_safe_nodes_last_output(node_group, make=True)
    in_node = get_safe_node_input(node_group, make=True)
    if joingeo is None or joingeo.type != "JOIN_GEOMETRY":
        joingeo = node_group.nodes.new('GeometryNodeJoinGeometry')
        insert_last_node(node_group, joingeo, safe=True)
    
    if out_node.location[0] - 1200 < in_node.location[0]: # make sure there is enough space
        out_node.location[0] = in_node.location[0]+1200

    # add switch socket
    socket = new_socket(node_group, ch_dict, 'NodeSocketBool')
    node_socket = in_node.outputs.get(socket.name)

    # make new channel
    min_y_loc = in_node.location[1] + 300
    for node in node_group.nodes:
        if node.name not in [in_node.name, out_node.name, joingeo.name]:
            min_y_loc = min(min_y_loc, node.location[1])
    in_ch, out_ch = channel_nodes(node_group, in_node.location[0] + 400, min_y_loc - 300, ch_dict)

    node_group.links.new(node_socket, in_ch)
    node_group.links.new(out_ch, joingeo.inputs[-1])
    return

def channel_nodes(node_group, x, y, ch):
    nodes = node_group.nodes
    links = node_group.links
    interface = node_group.interface
    
    loadnode = nodes.new('GeometryNodeCollectionInfo')
    loadnode.location = (x , y + 100)
    loadnode.hide = True
    loadnode.label = ch['name']
    loadnode.transform_space='RELATIVE'
    loadnode.inputs[0].default_value =ch['collection']
    
    # reload-func:
    loadnode.name = f"channel_load_{ch['identifier']}"
    
    switch = nodes.new('GeometryNodeSwitch')      
    switch.location = (x, y + 50)  
    switch.input_type = 'GEOMETRY'
    links.new(loadnode.outputs.get('Instances'), switch.inputs.get("True"))
    switch.hide = True
    switch.label = "Include channel"
    
    dataframe = nodes.new('NodeFrame')
    loadnode.parent = dataframe
    switch.parent = dataframe
    dataframe.label = f"{ch['name']} data"
    dataframe.name = f"dataframe_{ch['identifier']}"

    reroutes = [switch] 
    for x_, y_ in [(220, 40), (0, -150), (850,0), (0, 150)]:
        x += x_
        y += y_
        reroutes.append(nodes.new('NodeReroute'))
        reroutes[-1].location= (x, y)
        links.new(reroutes[-2].outputs[0], reroutes[-1].inputs[0])
    
    x += 50
    
    editframe = nodes.new('NodeFrame')
    reroutes[2].parent = editframe
    reroutes[2].name = f"edit_in_{ch['identifier']}"
    reroutes[3].parent = editframe
    reroutes[3].name = f"edit_out_{ch['identifier']}"
    editframe.label = f"edit geometry"
    editframe.name = f"editframe_{ch['identifier']}"
    
    setmat = nodes.new('GeometryNodeSetMaterial')
    setmat.inputs.get('Material').default_value = ch['material']
    links.new(reroutes[-1].outputs[0], setmat.inputs.get('Geometry'))
    setmat.location = (x, y)
    setmat.hide= True
    return switch.inputs.get("Switch"), setmat.outputs[0]


def init_container(objects, location, name):
    container = bpy.ops.object.empty_add(type="PLAIN_AXES",location=location)
    container = bpy.context.view_layer.objects.active
    container.name = name 

    for obj in objects:
        if obj is None:
            continue
        obj.parent = container
        obj.matrix_parent_inverse = container.matrix_world.inverted()

    container.location = (0,0,0)
    return container

