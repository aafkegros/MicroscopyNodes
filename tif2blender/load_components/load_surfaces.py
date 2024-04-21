import bpy

from .load_generic import init_holder
from ..handle_blender_structs import *

def gn_ch_tree(ch):
    node_group = bpy.data.node_groups.get(f"{ch} gn")
    if node_group:
        return node_group
    node_group= bpy.data.node_groups.new(type = 'GeometryNodeTree', name =f"{ch} gn")
    links = node_group.links
    nodes = node_group.nodes
    interface = node_group.interface
    interface.new_socket("Geometry", in_out="INPUT",socket_type='NodeSocketGeometry')
    group_input = node_group.nodes.new("NodeGroupInput")
    group_input.location = (-400, 0)
    
    chnode = nodes.new('FunctionNodeInputInt')
    chnode.integer = ch
    chnode.label = 'channel'
    chnode.location = (-100, -400)

    store2 =  node_group.nodes.new("GeometryNodeStoreNamedAttribute")
    store2.data_type = 'FLOAT_COLOR'
    store2.domain = 'CORNER'
    store2.location =(350, 0)
    store2.inputs.get("Name").default_value = "channel"
    links.new(group_input.outputs[0], store2.inputs[0])
    links.new(chnode.outputs[0], store2.inputs.get("Value"))

    interface.new_socket("Geometry", in_out="OUTPUT",socket_type='NodeSocketGeometry')
    group_output = node_group.nodes.new("NodeGroupOutput")
    group_output.location = (500, 0)
    links.new(store2.outputs[0], group_output.inputs[0])
    return node_group
    
def surf_material(ch_names):
    # do not check whether it exists, so a new load will force making a new mat
    mat = bpy.data.materials.new(f'surface')
    mat.blend_method = "BLEND"
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
    
    idnode =  nodes.new("ShaderNodeVertexColor")
    idnode.layer_name = 'channel'
    idnode.location = (-800, 300)

    map_range = nodes.new(type='ShaderNodeMapRange')
    map_range.location = (-450, 300)
    map_range.inputs[1].default_value = 0
    map_range.inputs[2].default_value = max(ch_names)
    links.new(idnode.outputs.get('Color'),map_range.inputs[0])
    
    cmap = nodes.new(type="ShaderNodeValToRGB")
    cmap.location = (-300, 300)
    get_cmap('hue-wheel',maxval=len(ch_names), ramp=cmap)
    links.new(map_range.outputs[0], cmap.inputs.get('Fac'))
    links.new(cmap.outputs[0], nodes.get("Principled BSDF").inputs.get("Base Color"))
    
    return mat
    
def load_surfaces(volume_collection, thresholds, scale, cache_coll, base_coll):
    ch_names, otsus = [], []
    for ix, val in enumerate(thresholds):
        if val > -1:
            ch_names.append(ix)
            otsus.append(val)
    
    surf_collections = []
    for ch_name, otsu in zip(ch_names, otsus):
        collection_activate(*cache_coll)
        surf_collection, _ = make_subcollection(f'channel {ch_name} surface')
        for vol in volume_collection.all_objects:
            bpy.ops.mesh.primitive_cube_add()
            obj = bpy.context.view_layer.objects.active

            obj.name = 'surface of ' + vol.name 

            bpy.ops.object.modifier_add(type='VOLUME_TO_MESH')
            obj.modifiers[-1].object = vol
            obj.modifiers[-1].grid_name = f'channel {ch_name}'
            obj.modifiers[-1].threshold = otsu

            obj.modifiers.new(type='NODES', name=f'ch {ch_name}')
            obj.modifiers[-1].node_group = gn_ch_tree(ch_name)

        surf_collections.append(surf_collection)
    
    collection_activate(*base_coll)
    surf_obj = init_holder('surface',surf_collections, [surf_material(ch_names)]*len(surf_collections), shared_shader=True)
    surf_obj.hide_render = True
    # surf_obj.hide_viewport = True
    bpy.context.active_object.hide_set(True)
    return surf_obj


