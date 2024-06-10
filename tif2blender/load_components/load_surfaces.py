import bpy

from .load_generic import init_holder
from ..handle_blender_structs import *
    
def surf_material(volume_inputs):
    # do not check whether it exists, so a new load will force making a new mat
    mats = []
    for ix, ch in enumerate(volume_inputs):
        mat = bpy.data.materials.new(f'surface {ch} shader')
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
        nodes.get("Principled BSDF").inputs.get('Base Color').default_value = get_cmap('hue-wheel', maxval=len(volume_inputs))[ix]
        mats.append(mat)
    return mats

def load_surfaces(volume_inputs, scale, cache_coll, base_coll):

    collection_activate(*base_coll)
    volume_colls = [volume_inputs[ch]['collection'] for ch in volume_inputs]
    surf_obj = init_holder('surface', volume_colls, surf_material(volume_inputs))
    node_group = surf_obj.modifiers[-1].node_group 
    nodes = node_group.nodes
    links = node_group.links
    interface = node_group.interface

    inputnode = nodes.get('Group Input')
    inputnode.location = (-1200, 0)

    for ix, ch in enumerate(volume_inputs):
        volnode = nodes.get(volume_inputs[ch]['collection'].name)
        v2m = nodes.new('GeometryNodeVolumeToMesh')
        v2m.location = volnode.location
        volnode.location = (volnode.location[0] - 300, volnode.location[1])    
        links.new(volnode.outputs[0], v2m.inputs.get('Volume'))
        links.new(v2m.outputs.get('Mesh'), nodes.get('Set Material '+ volume_inputs[ch]['collection'].name).inputs.get('Geometry'))
        
        interface.new_socket(f"Channel {ch} Threshold",in_out="INPUT",socket_type='NodeSocketFloat')
        interface.items_tree[-1].min_value = 0.0
        interface.items_tree[-1].max_value = 1.001
        interface.items_tree[-1].attribute_domain = 'POINT'
        # interface.items_tree[-1].default_value = float(volume_inputs[ch]['otsu'])
        interface.items_tree[-1].name = f"Channel {ch} Threshold"

        # set correct otsu value
        identifier= interface.items_tree[-1].identifier
        surf_obj.modifiers[-1][identifier] = float(volume_inputs[ch]['otsu'])
        
        node_group.interface.move(node_group.interface.items_tree[f"Channel {ch} Threshold"] , ix*2 + 2)
        links.new(inputnode.outputs.get(f"Channel {ch} Threshold"), v2m.inputs.get('Threshold'))


    surf_obj.hide_render = True
    bpy.context.active_object.hide_set(True)
    return surf_obj


