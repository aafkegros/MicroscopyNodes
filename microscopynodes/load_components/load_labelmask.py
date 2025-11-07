import numpy as np
import bpy
import bmesh
from pathlib import Path
import json
import os

from ..handle_blender_structs import *
from .load_generic import *
from .. import min_nodes
import zmesh

class LabelmaskIO(DataIO):
    min_type = min_keys.LABELMASK
    MASK_TEMPLATE = Path("{cache_dir}") / "{dataset_hash}" / "mask_{scale}" / "c{channel_ix}_t{t}"

    def generate_file_constructors(self, ch, cache_dir):
        file_constructors = []
        for t in range(bpy.context.scene.MiN_load_start_frame,bpy.context.scene.MiN_load_end_frame+1):
            if t >= len_axis('t', ch['axes_order'], ch['data'].shape):
                break
            file_constructors.append( {
                "cache_dir": cache_dir,
                "dataset_hash": ch['dataset_hash'],
                "scale": ch['surf_resolution'],
                "t": t, 
                "channel_ix" : ch['ix'],
                "template_str" : str(self.MASK_TEMPLATE),
            })
        return file_constructors

    def export_ch(self, ch, file_constructors, remake):
        mesher = zmesh.Mesher((1,1,1))
        for constructor in file_constructors: # loops through time
            fname = Path(str(self.MASK_TEMPLATE).format(**constructor)).with_suffix('.obj')
            fname_ids = fname.with_suffix('.csv')
            fname.parent.mkdir(exist_ok=True)

            if Path(fname).exists():
                if remake:
                    Path(fname).unlink()
                else: 
                    continue
            with open(str(fname_ids), 'ab+') as ofs:
                ofs.write(f"oid\n".encode('utf-8'))
            
            timeframe_arr = take_index(ch['data'], constructor['t'], 't', ch['axes_order']).compute()
            timeframe_arr = to_xyz(timeframe_arr,  ch['axes_order'].replace('t', ''))
            
            mesher.mesh(timeframe_arr, close=True)
            
            vertex_offset = 0
            for obj_id in mesher.ids():
                zmeshed = mesher.get(obj_id, 
                    normals=False,
                    reduction_factor=ch['surf_resolution']*30, 
                    max_error=ch['surf_resolution']*3,
                    voxel_centered=False, 
                    )

                obj_str = f"\no {obj_id}\n"
                for v in zmeshed.vertices:
                    obj_str += "v {:.5f} {:.5f} {:.5f}\n".format(*v)
                for f in zmeshed.faces:
                    obj_str += "f {} {} {}\n".format(*(i + 1 + vertex_offset for i in f))
                vertex_offset += len(zmeshed.vertices)
                with open(str(fname), 'ab+') as ofs:
                    ofs.write(obj_str.encode('utf-8'))
                with open(str(fname_ids), 'ab+') as ofs:
                    ofs.write(f"{obj_id}\n".encode('utf-8'))

                mesher.erase(obj_id) 
            mesher.clear()
        return 
    
    def get_metadata(self, file_constructors):
        files = [Path(str(self.MASK_TEMPLATE).format(**constructor)).with_suffix('.csv') for constructor in file_constructors]
        max_oid = max(
                int(line)
                for filepath in files
                for i, line in enumerate(open(filepath))
                if i > 0 # skips header
            )
        return {'max': max_oid}



class LabelmaskObject(ChannelObject):
    min_type = min_keys.LABELMASK
    import_node_name = "Import Microscopy Meshes"    

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
                pass
            princ = nodes.new("ShaderNodeBsdfPrincipled")
            if nodes.get("Material Output") is None:
                outnode = nodes.new(type='ShaderNodeOutputMaterial')
                outnode.name = 'Material Output'
            links.new(princ.outputs[0], nodes.get('Material Output').inputs[0])
        
        princ = nodes.get("Principled BSDF")
        princ.name = f"[{ch['identifier']}] principled"

        idnode =  nodes.new("ShaderNodeVertexColor")
        idnode.layer_name = 'oid'
        idnode.location = (-800, 300)

        remap = nodes.new('ShaderNodeGroup')
        remap.node_tree = min_nodes.shader_nodes.remap_oid_node()
        remap.name = '[remap_oid]'
        remap.location = (-600, 300)
        remap.show_options = False
        remap.inputs.get('# Objects').default_value = ch['metadata'][self.min_type]['max']
        links.new(idnode.outputs.get('Color'), remap.inputs.get('Value'))

        color_lut = nodes.new(type="ShaderNodeValToRGB")
        color_lut.location = (-350, 300)
        color_lut.width = 300
        color_lut.name = "[color_lut]"
        color_lut.outputs[1].hide = True
        links.new(remap.outputs[0], color_lut.inputs[0])

        links.new(color_lut.outputs[0], princ.inputs.get("Base Color"))
        links.new(color_lut.outputs[0], princ.inputs[27])
        return mat


    def update_material(self, mat, ch):
        try:
            nodes =  mat.node_tree.nodes
            min_nodes.shader_nodes.set_color_ramp_from_ch(ch, nodes.get('[color_lut]'))
            nodes.get('[remap_oid]').inputs.get('Revolving Colormap').default_value = (nodes.get('[color_lut]').color_ramp.interpolation == 'CONSTANT')
            nodes.get('[remap_oid]').inputs.get('# Colors').default_value =max(len(nodes.get('[color_lut]').color_ramp.elements), 5)
            princ = mat.node_tree.nodes.get(f"[{ch['identifier']}] principled")
            if ch['emission'] and princ.inputs[28].default_value == 0.0:
                princ.inputs[28].default_value = 0.5
            elif not ch['emission'] and princ.inputs[28].default_value == 0.5:
                princ.inputs[28].default_value = 0
        except Exception as e:
            print(e)
            pass
        return
        
    # def gn_oid_tree(self, oid, ch):
    #     node_group = bpy.data.node_groups.get(f"object id {oid}, {ch}")
    #     if node_group:
    #         return node_group
    #     node_group= bpy.data.node_groups.new(type = 'GeometryNodeTree', name =f"object id {oid}")
    #     links = node_group.links
    #     nodes = node_group.nodes
    #     interface = node_group.interface
    #     interface.new_socket("Geometry", in_out="INPUT",socket_type='NodeSocketGeometry')
    #     group_input = node_group.nodes.new("NodeGroupInput")
    #     group_input.location = (-400, 0)
        
    #     oidnode = nodes.new('FunctionNodeInputInt')
    #     oidnode.integer = oid
    #     oidnode.label = 'object id'
    #     oidnode.location = (-100, -200)
        
    #     chnode = nodes.new('FunctionNodeInputInt')
    #     chnode.integer = ch
    #     chnode.label = 'channel'
    #     chnode.location = (-100, -400)

    #     store =  node_group.nodes.new("GeometryNodeStoreNamedAttribute")
    #     store.data_type = 'FLOAT_COLOR'
    #     store.domain = 'CORNER'
    #     store.location =(150, 0)
    #     store.inputs.get("Name").default_value = "object id"
    #     links.new(group_input.outputs.get('Geometry'), store.inputs[0])
    #     links.new(oidnode.outputs[0], store.inputs.get("Value"))

    #     store2 =  node_group.nodes.new("GeometryNodeStoreNamedAttribute")
    #     store2.data_type = 'FLOAT_COLOR'
    #     store2.domain = 'CORNER'
    #     store2.location =(350, 0)
    #     store2.inputs.get("Name").default_value = "channel"
    #     links.new(store.outputs[0], store2.inputs[0])
    #     links.new(chnode.outputs[0], store2.inputs.get("Value"))

    #     interface.new_socket("Geometry", in_out="OUTPUT",socket_type='NodeSocketGeometry')
    #     group_output = node_group.nodes.new("NodeGroupOutput")
    #     group_output.location = (500, 0)
    #     links.new(store2.outputs[0], group_output.inputs[0])
    #     return node_group
        # def dissolve(self, obj, obj_id):
    #     m = obj.data
    #     bm = bmesh.new()
    #     bm.from_mesh(m)
    #     bmesh.ops.dissolve_limit(bm, angle_limit=0.0872665, verts=bm.verts, edges=bm.edges)
    #     bm.to_mesh(m)
    #     bm.free()
    #     m.update()
    #     return

    # for obj in tmp_collection.all_objects: 
            #     obj.select_set(True)
            
            
            # bpy.ops.wm.alembic_export(filepath=fname,
            #                 selected=True,
            #                 vcolors = False,
            #                 flatten=False,
            #                 orcos=True,
            #                 export_custom_properties=False,
            #                 start = 0,
            #                 end = 1,
            #                 evaluation_mode = "RENDER",
            #                 )
            # for obj in tmp_collection.all_objects: 
            #     obj.data.clear_geometry()

        # for obj in mask_objects.values():
        #     obj.select_set(True)
        # bpy.ops.object.delete(use_global=False)
        # bpy.data.collections.remove(tmp_collection)
        # collection_activate(*parentcoll)

        # if not Path(fname).exists(): #make dummy file for sequencing
                #     open(fname, 'a').close()
                #     open(fname_ids, 'a').close()

     # obj_id_val = obj_id + 1
                
                # if obj_id_val in mask_objects:
                #     obj = mask_objects[obj_id_val]
                # else: 
                #     objname=f"ch{ch['ix']}_obj{obj_id_val}_" 
                #     bpy.ops.mesh.primitive_cube_add()
                #     obj=bpy.context.view_layer.objects.active
                #     obj.name = objname
                #     obj.data.name = objname
                #     mask_objects[obj_id_val] = obj

                # mesh = obj.data
                # mesh.clear_geometry()
                # mesh.from_pydata(zmeshed.vertices,[], zmeshed.faces)
                # bpy.ops.object.mode_set(mode = 'OBJECT')
                # self.dissolve(obj, obj_id)
                # obj.select_set(True) #TODO see if this works