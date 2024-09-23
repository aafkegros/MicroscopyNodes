import bpy

from .load_generic import *
from ..handle_blender_structs import *
    
def surf_material(surf_obj, ch_dicts):
    # do not check whether it exists, so a new load will force making a new mat
    mod = get_min_gn(surf_obj)
    all_ch_present = len([node.name for node in mod.node_group.nodes if f"channel_load" in node.name])

    for ix, ch in enumerate(ch_dicts):
        mat = bpy.data.materials.new(f"{ch['name']} surface")
        mat.blend_method = "HASHED"
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        if nodes.get("Principled BSDF") is None:
            try: 
                nodes.remove(nodes.get("Principled Volume"))
            except Exception as e:
                print(e)
            princ = nodes.new("ShaderNodeBsdfPrincipled")
            links.new(princ.outputs[0], nodes.get('Material Output').inputs[0])
        
        princ = nodes.get("Principled BSDF")
        princ.name = f"[{ch['identifier']}] principled"
        color = get_cmap('default_ch')[all_ch_present % len(get_cmap('default_ch'))]
        all_ch_present += 1
        princ.inputs.get('Base Color').default_value = color
        princ.inputs[26].default_value = color

        colornode = nodes.new("ShaderNodeRGB")
        colornode.location = (princ.location[0]-200, princ.location[1])
        colornode.outputs[0].default_value = color
        links.new(colornode.outputs[0], princ.inputs.get('Base Color'))
        links.new(colornode.outputs[0], princ.inputs[26])

        princ.inputs.get('Alpha').default_value = 0.5
        ch['material'] = mat
    return 

def insert_vol_to_surf(surf_obj, ch):
    gn_mod = get_min_gn(surf_obj)
    node_group = gn_mod.node_group
    in_node = get_safe_node_input(node_group)

    # can be explicitly named as this should only be called upon appending a channel
    edit_in = node_group.nodes[f"edit_in_{ch['identifier']}"]
    edit_out = node_group.nodes[f"edit_out_{ch['identifier']}"]
    editframe = node_group.nodes[f"editframe_{ch['identifier']}"]

    v2m = node_group.nodes.new('GeometryNodeVolumeToMesh')
    v2m.name = f"VOL_TO_MESH_{ch['identifier']}"
    v2m.location = (edit_in.location[0] + 400, edit_in.location[1])
    v2m.parent = editframe
    node_group.links.new(edit_in.outputs[0], v2m.inputs.get('Volume'))
    node_group.links.new(v2m.outputs.get('Mesh'), edit_out.inputs[0])
    
    socket_ix = get_socket(node_group, ch, return_ix=True, min_type="SWITCH")[1]
    threshold_socket = new_socket(node_group, ch, 'NodeSocketFloat', min_type='THRESHOLD',  ix=socket_ix+1)
    threshold_socket.min_value = 0.0
    threshold_socket.max_value = 1.001
    threshold_socket.attribute_domain = 'POINT'
    gn_mod[threshold_socket.identifier] = ch['threshold']

    normnode = node_group.nodes.new(type="ShaderNodeMapRange")
    normnode.location =(edit_in.location[0] + 200, edit_in.location[1]-150)
    normnode.label = "Normalize data"
    normnode.inputs[3].default_value = ch['min_val']       
    normnode.inputs[4].default_value = ch['max_val']    
    node_group.links.new(in_node.outputs.get(threshold_socket.name), normnode.inputs[0])  
    node_group.links.new(normnode.outputs[0], v2m.inputs.get("Threshold"))  
    normnode.hide = True

    update_resolution(gn_mod, ch)
    return

def update_resolution(gn_mod, ch):
    node_group = gn_mod.node_group
    
    if f"VOL_TO_MESH_{ch['identifier']}" not in [node.name for node in node_group.nodes]:
        return
    v2m = node_group.nodes[f"VOL_TO_MESH_{ch['identifier']}"]

    if ch['surf_resolution'] == 0:
        v2m.resolution_mode='GRID'
        return
    else:
        v2m.resolution_mode='VOXEL_SIZE'
    
    for i in range(4):
        socket = get_socket(node_group, ch, min_type='VOXEL_SIZE', internal_append=str(i))
        if socket is not None:
            if i == ch['surf_resolution']:
                return
            node_group.interface.remove(item=socket)

    socket_ix = get_socket(node_group, ch, min_type="SWITCH",return_ix=True)[1]
    socket = new_socket(node_group, ch, 'NodeSocketFloat', min_type='VOXEL_SIZE',internal_append=f"{ch['surf_resolution']}", ix=socket_ix+1)

    default_settings = [None, 0.5, 4, 15]
    in_node = get_safe_node_input(node_group)
    node_group.links.new(in_node.outputs.get(socket.name), v2m.inputs.get('Voxel Size'))
    gn_mod[socket.identifier] = default_settings[ch['surf_resolution']]
    return

def load_surfaces(ch_dicts, scale, cache_coll, base_coll, surf_obj=None):
    collection_activate(*base_coll)

    vol_ch = [ch for ch in ch_dicts if ch['volume'] or ch['surface']]
    if len(vol_ch) > 0 and surf_obj is None:
        surf_obj = init_holder('surface')
    if surf_obj is None:
        return None

    new_channels = [ch for ch in vol_ch if not ch_present(surf_obj, ch['identifier'])]
    [ch.update({"material":None}) for ch in ch_dicts]
    surf_material(surf_obj, new_channels)
    surf_obj = update_holder(surf_obj, ch_dicts, 'surface')

    for ix, ch in enumerate(new_channels):
        insert_vol_to_surf(surf_obj, ch)
        
    return surf_obj


