import numpy as np
import bpy
import bmesh
from pathlib import Path
import json

from ..handle_blender_structs import *
from .load_generic import init_holder


def labelmask_shader(maskchannel, maxval):
    # do not check whether it exists, so a new load will force making a new mat
    mat = bpy.data.materials.new(f'channel {maskchannel}')
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
    idnode.layer_name = 'object id'
    idnode.location = (-800, 300)
    
    mod = nodes.new("ShaderNodeMath")
    mod.operation = "MODULO"
    mod.location =(-600, 300)
    links.new(idnode.outputs.get('Color'), mod.inputs[0])
    mod.inputs[1].default_value = 10
    
    map_range = nodes.new(type='ShaderNodeMapRange')
    map_range.location = (-450, 300)
    map_range.inputs[1].default_value = 0
    map_range.inputs[2].default_value = 11
    links.new(mod.outputs[0],map_range.inputs[0])
    
    tab10 = nodes.new(type="ShaderNodeValToRGB")
    tab10.location = (-300, 300)
    get_cmap('mpl-tab10', ramp=tab10)
    links.new(map_range.outputs[0], tab10.inputs.get('Fac'))
    links.new(tab10.outputs[0], nodes.get("Principled BSDF").inputs.get("Base Color"))
    
    # make optional linear colormap
    map_range_lin = nodes.new(type='ShaderNodeMapRange')
    map_range_lin.location = (-450, 0)
    map_range_lin.inputs[1].default_value = 0
    map_range_lin.inputs[2].default_value = maxval
    links.new(idnode.outputs.get('Color'),map_range_lin.inputs[0])
    
    vir = nodes.new(type="ShaderNodeValToRGB")
    vir.location = (-300, 0)
    get_cmap('mpl-viridis', ramp=vir)
    links.new(map_range_lin.outputs[0], vir.inputs.get('Fac'))
    
    return mat

def gn_oid_tree(oid, ch):
    node_group = bpy.data.node_groups.get(f"object id {oid}, {ch}")
    if node_group:
        return node_group
    node_group= bpy.data.node_groups.new(type = 'GeometryNodeTree', name =f"object id {oid}")
    links = node_group.links
    nodes = node_group.nodes
    interface = node_group.interface
    interface.new_socket("Geometry", in_out="INPUT",socket_type='NodeSocketGeometry')
    group_input = node_group.nodes.new("NodeGroupInput")
    group_input.location = (-400, 0)
    
    oidnode = nodes.new('FunctionNodeInputInt')
    oidnode.integer = oid
    oidnode.label = 'object id'
    oidnode.location = (-100, -200)
    
    chnode = nodes.new('FunctionNodeInputInt')
    chnode.integer = ch
    chnode.label = 'channel'
    chnode.location = (-100, -400)

    store =  node_group.nodes.new("GeometryNodeStoreNamedAttribute")
    store.data_type = 'FLOAT_COLOR'
    store.domain = 'CORNER'
    store.location =(150, 0)
    store.inputs.get("Name").default_value = "object id"
    links.new(group_input.outputs.get('Geometry'), store.inputs[0])
    links.new(oidnode.outputs[0], store.inputs.get("Value"))

    store2 =  node_group.nodes.new("GeometryNodeStoreNamedAttribute")
    store2.data_type = 'FLOAT_COLOR'
    store2.domain = 'CORNER'
    store2.location =(350, 0)
    store2.inputs.get("Name").default_value = "channel"
    links.new(store.outputs[0], store2.inputs[0])
    links.new(chnode.outputs[0], store2.inputs.get("Value"))

    interface.new_socket("Geometry", in_out="OUTPUT",socket_type='NodeSocketGeometry')
    group_output = node_group.nodes.new("NodeGroupOutput")
    group_output.location = (500, 0)
    links.new(store2.outputs[0], group_output.inputs[0])
    return node_group

def dissolve(obj, obj_id):
    m = obj.data
    bm = bmesh.new()
    bm.from_mesh(m)
    bmesh.ops.dissolve_limit(bm, angle_limit=0.0872665, verts=bm.verts, edges=bm.edges)
    bm.to_mesh(m)
    bm.free()
    m.update()
    return

def abcfname(cache_dir, channel, timestep):
    return str(Path(cache_dir) / f"mask_ch{channel}_t_{timestep:04}.abc")
def jsonfname(cache_dir, channel):
    return str(Path(cache_dir) / f"mask_locs_ch{channel}.json")

def export_alembic_and_loc(mask, maskchannel, cache_dir, remake, axes_order):
    from skimage.measure import marching_cubes
    from scipy.ndimage import find_objects
    axes_order = axes_order.replace("c","")
    mask= np.moveaxis(mask, [axes_order.find('t'), axes_order.find('x'),axes_order.find('y'),axes_order.find('z')],[0,1,2,3])

    parentcoll = get_current_collection()
    tmp_collection, _ = collection_by_name('tmp')
    objnames = {} # register objnames as dict at start value : name
    locations = {} 
    abcfiles = []

    for timestep in range(0,mask.shape[0]):
        bpy.ops.object.select_all(action='DESELECT')
        if timestep == 0:
            for obj_id_val in np.unique(mask)[1:]: #skip zero, register all objects with new names, need to be present in first frame
                objname=f"ch{maskchannel}_obj{obj_id_val}_" 
                bpy.ops.mesh.primitive_cube_add()
                obj=bpy.context.view_layer.objects.active
                obj.name = objname
                obj.data.name = objname
                # obj.scale = scale
                objnames[obj_id_val] = obj.name
                locations[obj.name]={}
                locations[obj.name][0] = {'x':-1,'y':-1,'z':-1}

        for obj_id, objslice in enumerate(find_objects(mask[timestep])):
            if objslice is None:
                continue
            obj_id_val = obj_id + 1
            objarray = np.pad(mask[timestep][objslice], 1, constant_values=0)
            verts, faces, normals, values = marching_cubes(objarray==obj_id+1, step_size=1)
            
            obj = bpy.data.objects.get(objnames[obj_id_val])

            mesh = obj.data
            mesh.clear_geometry()
            mesh.from_pydata(verts,[], faces)
            bpy.ops.object.mode_set(mode = 'OBJECT')

            loc = (objslice[0].start, objslice[1].start, objslice[2].start)
            obj.location = loc

            locations[obj.name][timestep] = {'x':loc[0],'y':loc[1],'z':loc[2]} 

            dissolve(obj, obj_id)
        

        for obj in tmp_collection.all_objects: 
            # if obj.name in objnames.values():
            obj.select_set(True)
        

        fname = abcfname(cache_dir, maskchannel, timestep)
        abcfiles.append(fname)
        if Path(fname).exists() and bpy.context.scene.remake:
            Path(fname).unlink() # this may fix an issue with subsequent loads
        bpy.ops.wm.alembic_export(filepath=fname,
                        visible_objects_only=False,
                        selected=True,
                        vcolors = True,
                        flatten=True,
                        orcos=True,
                        export_custom_properties=True,
                        start = 0,
                        end = 1,
                        evaluation_mode = "RENDER",
                        )
        for obj in tmp_collection.all_objects: 
            obj.data.clear_geometry()

    for objname in objnames.values():
        obj.select_set(True)
    bpy.ops.object.delete(use_global=False)
    bpy.data.collections.remove(tmp_collection)
    collection_activate(*parentcoll)

    with open(jsonfname(cache_dir, maskchannel), 'w') as fp:
        json.dump(locations, fp, indent=4)
    return 

def import_abc_and_loc(maskchannel, maxval, scale, cache_dir):
    mask_objs = []
    parentcoll = get_current_collection()
    
    channel_collection, _ = make_subcollection(f"channel {maskchannel} labelmask")
    bpy.ops.wm.alembic_import(filepath=abcfname(cache_dir, maskchannel, 0), is_sequence=True)

    shader_labelmask = labelmask_shader(maskchannel,maxval + 1)

    with open(jsonfname(cache_dir, maskchannel), 'r') as fp:
        locations = json.load(fp)

    locnames_newnames = {}
    for obj in channel_collection.all_objects: # for blender renaming
        oid = int(obj.name.split('_')[1].strip('obj'))
        ch = int(obj.name.split('_')[0].strip('ch'))
        locnames_newnames[(oid, ch)] = obj

    for objname in locations:
        oid = int(objname.split('_')[1].strip('obj'))
        ch = int(objname.split('_')[0].strip('ch'))
        obj = locnames_newnames[(oid, ch)]   
        obj.scale = scale
        mask_objs.append(obj)
        for time, loc in locations[objname].items():
            obj.location = (loc['x'], loc['y'], loc['z']) * scale
            obj.keyframe_insert(data_path="location", frame=int(time))
        obj.modifiers.new(type='NODES', name=f'object id + channel {oid}')
        obj.modifiers[-1].node_group = gn_oid_tree(oid, ch)

    collection_activate(*parentcoll)
    return mask_objs, channel_collection, shader_labelmask

def load_labelmask(mask_arrays, scale, cache_coll, base_coll, cache_dir, remake, axes_order):
    mask_objs = []
    mask_colls, mask_shaders = [], []
    locations = {}
    
    collection_activate(*cache_coll)
    for maskchannel, mask in mask_arrays.items():
        if not Path(abcfname(cache_dir, maskchannel,0)).exists() or remake:
            export_alembic_and_loc(mask, maskchannel, cache_dir, remake, axes_order)
        objs, coll, shader = import_abc_and_loc(maskchannel, np.max(mask), scale, cache_dir)
        
        mask_objs.extend(objs)
        mask_colls.append(coll)
        mask_shaders.append(shader)
    collection_activate(*base_coll)
    mask_obj = init_holder('masks' ,mask_colls, mask_shaders)
    return mask_obj, mask_colls



