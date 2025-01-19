import numpy as np
import bpy
import bmesh
from pathlib import Path
import json
import os

from ..handle_blender_structs import *
from .load_generic import *

class LabelmaskIO(DataIO):
    min_type = min_keys.LABELMASK

    def dissolve(self, obj, obj_id):
        m = obj.data
        bm = bmesh.new()
        bm.from_mesh(m)
        bmesh.ops.dissolve_limit(bm, angle_limit=0.0872665, verts=bm.verts, edges=bm.edges)
        bm.to_mesh(m)
        bm.free()
        m.update()
        return

    def export_ch(self, ch, cache_dir, remake, axes_order):
        from skimage.measure import marching_cubes
        from scipy.ndimage import find_objects, label
        axes_order = axes_order.replace('c', '') # only gets a single channel
        abcfiles = []
        mask = ch['data']

        parentcoll = get_current_collection()
        tmp_collection, _ = collection_by_name('tmp')

        mask_objects = {}  
        for timestep in range(0,bpy.context.scene.MiN_load_end_frame+1):
            bpy.ops.object.select_all(action='DESELECT')

            if timestep >= len_axis('t', axes_order, mask.shape):
                break

            fname = str(Path(cache_dir) / f"mask_ch{ch['ix']}_res_{ch['surf_resolution']}_t_{timestep:04}.abc")
            if timestep < bpy.context.scene.MiN_load_start_frame:
                if not Path(fname).exists(): #make dummy file for sequencing
                    open(fname, 'a').close()
                continue
            
            abcfiles.append(fname)
            if (Path(fname).exists() and os.path.getsize(fname) > 0):
                if remake:
                    Path(fname).unlink()
                else: 
                    # Allowing reloading of abc files could be done here, but this can cause strange issues
                    # That still need triage - for now, files are always overwritten.
                    pass
                    # continue
            
            timeframe_arr = take_index(mask, timestep, 't', axes_order).compute()
            timeframe_arr = expand_to_xyz(timeframe_arr, axes_order.replace('t', ''))

            for obj_id, objslice in enumerate(find_objects(timeframe_arr)):
                if objslice is None:
                    continue

                obj_id_val = obj_id + 1
                objarray = np.pad(timeframe_arr[objslice], 1, constant_values=0)
                
                size = objarray.shape[0]-2 * objarray.shape[1]-2 * objarray.shape[0]-2

                step_size = [1,2,4,8][ch['surf_resolution']]
                try:
                    verts, faces, normals, values = marching_cubes(objarray==obj_id+1, step_size=step_size)
                    verts = verts + np.array([objslice[0].start, objslice[1].start, objslice[2].start])
                except Exception as e:
                    print(f'excepted {e} in meshing')
                    if ch['surf_resolution'] != 0: # march throws with too small objects
                        continue
                
                if obj_id_val in mask_objects:
                    obj = mask_objects[obj_id_val]
                else: 
                    objname=f"ch{ch['ix']}_obj{obj_id_val}_" 
                    bpy.ops.mesh.primitive_cube_add()
                    obj=bpy.context.view_layer.objects.active
                    obj.name = objname
                    obj.data.name = objname
                    mask_objects[obj_id_val] = obj

                mesh = obj.data
                mesh.clear_geometry()
                mesh.from_pydata(verts,[], faces)
                bpy.ops.object.mode_set(mode = 'OBJECT')
                self.dissolve(obj, obj_id)
                # obj.select_set(True) #TODO see if this works
            
            for obj in tmp_collection.all_objects: 
                obj.select_set(True)
            
           
            bpy.ops.wm.alembic_export(filepath=fname,
                            visible_objects_only=False,
                            selected=True,
                            vcolors = False,
                            flatten=False,
                            orcos=True,
                            export_custom_properties=False,
                            start = 0,
                            end = 1,
                            evaluation_mode = "RENDER",
                            )
            for obj in tmp_collection.all_objects: 
                obj.data.clear_geometry()

        for obj in mask_objects.values():
            obj.select_set(True)
        bpy.ops.object.delete(use_global=False)
        bpy.data.collections.remove(tmp_collection)
        collection_activate(*parentcoll)
        return [{'abcfiles':abcfiles}]
    

    def import_data(self, ch, scale):
        mask_objs = []
        mask_coll, mask_lcoll = make_subcollection(f"{ch['name']}_{self.min_type.name.lower()}", duplicate=True)
        
        maskfiles = ch['local_files'][self.min_type][0]
        bpy.ops.wm.alembic_import(filepath=maskfiles['abcfiles'][0], is_sequence=(len(maskfiles['abcfiles']) >1))

        locnames_newnames = {}
        oids = []
        for obj in mask_coll.all_objects: # for blender renaming
            oid = int(obj.name.split('_')[1].removeprefix('obj'))
            ch = int(obj.name.split('_')[0].removeprefix('ch'))
            obj.modifiers.new(type='NODES', name=f'object id + channel {oid}')
            obj.modifiers[-1].node_group = self.gn_oid_tree(oid, ch)
            obj.scale = scale
            oids.append(oid)

        return mask_coll, {'max': max(oids)}


    def gn_oid_tree(self, oid, ch):
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


class LabelmaskObject(ChannelObject):
    min_type = min_keys.LABELMASK

    def add_material(self, ch):
        # do not check whether it exists, so a new load will force making a new mat
        mat = super().add_material(ch)
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
        links.new(tab10.outputs[0], princ.inputs[27])
        
        # make optional linear colormap
        map_range_lin = nodes.new(type='ShaderNodeMapRange')
        map_range_lin.location = (-450, 0)
        map_range_lin.inputs[1].default_value = 0
        map_range_lin.inputs[2].default_value = ch['metadata'][self.min_type]['max']
        links.new(idnode.outputs.get('Color'),map_range_lin.inputs[0])
        
        vir = nodes.new(type="ShaderNodeValToRGB")
        vir.location = (-300, 0)
        get_cmap('mpl-viridis', ramp=vir)
        links.new(map_range_lin.outputs[0], vir.inputs.get('Fac'))
        return mat


    def update_material(self, mat, ch):
        try:
            princ = mat.node_tree.nodes.get(f"[{ch['identifier']}] principled")
            if ch['emission'] and princ.inputs[28].default_value == 0.0:
                princ.inputs[28].default_value = 0.5
            elif not ch['emission'] and princ.inputs[28].default_value == 0.5:
                princ.inputs[28].default_value = 0
        except:
            pass
        return
        