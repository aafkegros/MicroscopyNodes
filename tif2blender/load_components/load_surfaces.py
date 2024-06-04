import bpy

from .load_generic import init_holder
from ..handle_blender_structs import *
    
def surf_material(ch, maxval):
    # do not check whether it exists, so a new load will force making a new mat
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
    nodes.get("Principled BSDF").inputs.get('Base Color').default_value = get_cmap('hue-wheel', maxval=maxval)[ch]
    return mat

def load_surfaces(volume_collection, otsus, scale, cache_coll, base_coll):
    ch_names = []
    for ix, val in enumerate(otsus):
        if val > -1:
            ch_names.append(ix)
    
    collection_activate(*base_coll)
    volumes = [vol for ix, vol in enumerate(volume_collection.children) if ix in ch_names]
    surf_obj = init_holder('surface', volumes, [surf_material(ch_name, len(otsus)) for ch_name in ch_names])
    node_group = surf_obj.modifiers[-1].node_group 
    nodes = node_group.nodes
    links = node_group.links
    interface = node_group.interface

    inputnode = nodes.get('Group Input')
    inputnode.location = (-1200, 0)

    for ix, ch in enumerate(ch_names):
        vol = volumes[ix]
        volnode = nodes.get(vol.name)
        v2m = nodes.new('GeometryNodeVolumeToMesh')
        v2m.location = volnode.location
        volnode.location = (volnode.location[0] - 300, volnode.location[1])    
        links.new(volnode.outputs[0], v2m.inputs.get('Volume'))
        links.new(v2m.outputs.get('Mesh'), nodes.get('Set Material '+ vol.name).inputs.get('Geometry'))
        
        interface.new_socket(f"Channel {ch} Threshold",in_out="INPUT",socket_type='NodeSocketFloat')
        interface.items_tree[-1].min_value = 0.0
        interface.items_tree[-1].max_value = 1.001
        interface.items_tree[-1].attribute_domain = 'POINT'
        interface.items_tree[-1].default_value = otsus[ch]
        # interface.items_tree[-1].default_value = 1
        interface.items_tree[-1].name = f"Channel {ch} Threshold"

        # set correct otsu value
        identifier= interface.items_tree[-1].identifier
        surf_obj.modifiers[-1][identifier] = float(otsus[ch])
        
        node_group.interface.move(node_group.interface.items_tree[f"Channel {ch} Threshold"] , ix*2 + 2)
        links.new(inputnode.outputs.get(f"Channel {ch} Threshold"), v2m.inputs.get('Threshold'))


    surf_obj.hide_render = True
    bpy.context.active_object.hide_set(True)
    return surf_obj


