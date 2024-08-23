import bpy

from .load_generic import init_holder
from ..handle_blender_structs import *
    
def surf_material(ch_dicts):
    # do not check whether it exists, so a new load will force making a new mat
    mats = []
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
        nodes.get("Principled BSDF").inputs.get('Base Color').default_value = get_cmap('hue-wheel', maxval=len(ch_dicts))[ix]
        mats.append(mat)
    return mats

def load_surfaces(ch_dicts, scale, cache_coll, base_coll):
    print('setting surface')
    collection_activate(*base_coll)
    
    surf_dicts = [ch for ch in ch_dicts if ch['surface'] or ch['volume']]
    volume_colls = [ch['collection'] for ch in surf_dicts]
    surf_obj = init_holder('surface', volume_colls, surf_material(surf_dicts))
    if surf_obj is not None:
        node_group = surf_obj.modifiers[-1].node_group 
        nodes = node_group.nodes
        links = node_group.links
        interface = node_group.interface

        inputnode = nodes.get('Group Input')
        inputnode.location = (-1200, 0)

    for ix, ch in enumerate(surf_dicts):
        volnode = nodes.get(ch['collection'].name)
        volnode.label = ch['name']
        v2m = nodes.new('GeometryNodeVolumeToMesh')
        v2m.location = volnode.location
        volnode.location = (volnode.location[0] - 300, volnode.location[1])    
        links.new(volnode.outputs[0], v2m.inputs.get('Volume'))
        links.new(v2m.outputs.get('Mesh'), nodes.get('Set Material '+ ch['collection'].name).inputs.get('Geometry'))
        
        interface.new_socket(name=f"{ch['name']} Threshold",in_out="INPUT",socket_type='NodeSocketFloat')
        interface.items_tree[-1].min_value = 0.0
        interface.items_tree[-1].max_value = 1.001
        interface.items_tree[-1].attribute_domain = 'POINT'
        interface.items_tree[-1].name = f"{ch['name']} Threshold"

        # set threshold value
        identifier= interface.items_tree[-1].identifier
        surf_obj.modifiers[-1][identifier] = float(ch['threshold'])
        
        if not ch['surface']:
            for socket in interface.items_tree:
                if socket.name == ch['name']:
                    surf_obj.modifiers[-1][socket.identifier] = False

        normnode = nodes.new(type="ShaderNodeMapRange")
        normnode.location = (volnode.location[0] - 200, volnode.location[1] - 100)    
        normnode.label = "Normalize data"
        normnode.inputs[3].default_value = ch['min_val']       
        normnode.inputs[4].default_value = ch['max_val']    
        links.new(inputnode.outputs.get(f"{ch['name']} Threshold"), normnode.inputs[0])  
        normnode.hide = True

        node_group.interface.move(node_group.interface.items_tree[f"{ch['name']} Threshold"] , ix*2 + 2)

        links.new(normnode.outputs[0], v2m.inputs.get('Threshold'))

    print('set surface')
    if not any([ch['surface'] for ch in ch_dicts]) and surf_obj is not None:
        surf_obj.hide_render = True
        bpy.context.active_object.hide_set(True)
    return surf_obj


