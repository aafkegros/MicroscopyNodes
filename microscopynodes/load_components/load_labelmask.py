import numpy as np
import bpy
import bmesh
from pathlib import Path
import json

from ..handle_blender_structs import *
from .load_generic import init_holder, update_holder, clear_updating_collections, ch_present


def labelmask_shader(ch, maxval):
    # do not check whether it exists, so a new load will force making a new mat
    mat = bpy.data.materials.new(f"{ch['name']} labelmasks")
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
        if nodes.get("Material Output") is None:
            outnode = nodes.new(type='ShaderNodeOutputMaterial')
            outnode.name = 'Material Output'
        links.new(princ.outputs[0], nodes.get('Material Output').inputs[0])
    
    princ = nodes.get("Principled BSDF")
    princ.name = f"[{ch['identifier']}] principled"

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
    links.new(tab10.outputs[0], princ.inputs.get("Base Color"))
    links.new(tab10.outputs[0], princ.inputs[26])
    
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

def abcfname(cache_dir, channel, timestep, resolution):
    return str(Path(cache_dir) / f"mask_ch{channel}_res_{resolution}_t_{timestep:04}.abc")
def jsonfname(cache_dir, channel, resolution):
    return str(Path(cache_dir) / f"mask_locs_ch{channel}_{resolution}.json")

def export_alembic_and_loc(ch, cache_dir, remake, axes_order):
    from skimage.measure import marching_cubes
    from scipy.ndimage import find_objects, label
    axes_order = axes_order.replace("c","")

    mask = ch['data']
    mask = mask.compute()

    for dim in 'txyz': # essential for mask loading
        if dim not in axes_order:
            mask = np.expand_dims(mask,axis=0)
            axes_order = dim + axes_order

    mask= np.moveaxis(mask, [axes_order.find('t'), axes_order.find('x'),axes_order.find('y'),axes_order.find('z')],[0,1,2,3])
    
    parentcoll = get_current_collection()
    tmp_collection, _ = collection_by_name('tmp')
    objnames = {} # register objnames as dict at start value : name
    locations = {} 

    unique_vals_all = np.unique(mask)
    if len(unique_vals_all) == 2: 
        # if binary mask, do connected components, to save memory when meshing if a lot of objects are present
        try: 
            mask = mask.astype(np.uint16)
            for timepoint, time_arr in enumerate(mask):
                new_unique_vals = label(time_arr,structure=np.ones((3,3,3)) ,output=time_arr)
                if new_unique_vals > len(unique_vals_all):
                    unique_vals_all = [uni for uni in range(new_unique_vals + 1)]
                mask[timepoint] = time_arr
        except RuntimeError as e:
            # this catches binary masks with > 65k objects
            raise ValueError("This binary mask seems to be too complicated (>65k separate obj/timepoint) to load as a label mask. Consider loading it as a volume and using the 'Surfaces' visualization or applying a new Volume to Surface Blender node")        

    for timestep in range(0,mask.shape[0]):
        bpy.ops.object.select_all(action='DESELECT')
        if timestep == 0:
            
            for obj_id_val in unique_vals_all[1:]: 
                #skip zero, register all object with new names, need to be present in first frame
                objname=f"ch{ch['ix']}_obj{obj_id_val}_" 
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
            
            size = objarray.shape[0]-2 * objarray.shape[1]-2 * objarray.shape[0]-2

            step_size = [1,2,4,8][ch['surf_resolution']]
            try:
                verts, faces, normals, values = marching_cubes(objarray==obj_id+1, step_size=step_size)
            except:
                if ch['surf_resolution'] != 0: # march throws with too small objects
                    continue
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
            obj.select_set(True)
        

        fname = abcfname(cache_dir, ch['ix'], timestep, ch['surf_resolution'])

        if Path(fname).exists() and remake:
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

    with open(jsonfname(cache_dir, ch['ix'], ch['surf_resolution']), 'w') as fp:
        json.dump(locations, fp, indent=4)
    return 

def import_abc_and_loc(ch, scale, cache_dir, is_sequence):
    mask_objs = []
    parentcoll = get_current_collection()
    
    activate_or_make_channel_collection(ch, "labelmask")
    bpy.ops.wm.alembic_import(filepath=abcfname(cache_dir, ch['ix'], 0, ch['surf_resolution']), is_sequence=is_sequence)
    
    with open(jsonfname(cache_dir, ch['ix'], ch['surf_resolution']), 'r') as fp:
        locations = json.load(fp)

    locnames_newnames = {}
    for obj in ch['collection'].all_objects: # for blender renaming
        oid = int(obj.name.split('_')[1].removeprefix('obj'))
        ch = int(obj.name.split('_')[0].removeprefix('ch'))
        locnames_newnames[(oid, ch)] = obj
    
    for objname in locations:
        oid = int(objname.split('_')[1].removeprefix('obj'))
        ch = int(objname.split('_')[0].removeprefix('ch'))
        obj = locnames_newnames[(oid, ch)]   
        obj.scale = scale
        mask_objs.append(obj)
        for time, loc in locations[objname].items():
            obj.location = (loc['x'], loc['y'], loc['z']) * scale
            obj.keyframe_insert(data_path="location", frame=int(time))
        obj.modifiers.new(type='NODES', name=f'object id + channel {oid}')
        obj.modifiers[-1].node_group = gn_oid_tree(oid, ch)

    collection_activate(*parentcoll)
    return mask_objs

def load_labelmask(ch_dicts, scale, cache_coll, base_coll, cache_dir, remake, axes_order, mask_obj=None):
    locations = {}
    
    # update_holder reads these aspects to set
    [ch.update({"material":None, "collection":None}) for ch in ch_dicts]
    mask_ch = [ch for ch in ch_dicts if ch['labelmask']]
    if mask_obj is not None:
        clear_updating_collections(mask_obj, ch_dicts, 'labelmask')

    collection_activate(*cache_coll)
    for ch in mask_ch:
        if not Path(abcfname(cache_dir, ch['ix'], 0, ch['surf_resolution'])).exists() or remake:
            export_alembic_and_loc(ch, cache_dir, remake, axes_order)
        import_abc_and_loc(ch, scale, cache_dir,is_sequence=('t' in axes_order))
    collection_activate(*base_coll)

    
    if len(mask_ch) > 0 and mask_obj is None:
        mask_obj = init_holder('labelmasks')

    if mask_obj is not None:
        for ch in ch_dicts:
            if ch['collection'] is None or ch_present(mask_obj, ch['identifier']):
                continue
            ch['material'] = labelmask_shader(ch,np.max(ch['data']) + 1)

        mask_obj = update_holder(mask_obj ,ch_dicts, 'labelmask')
    return mask_obj



