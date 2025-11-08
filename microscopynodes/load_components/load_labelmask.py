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
            
            log(f"Meshing timepoint {constructor['t']}")

            mesher.mesh(timeframe_arr, close=True)
            
            vertex_offset = 0
            for obj_id in mesher.ids():
                log(f"Writing object {obj_id} at time {constructor['t']}")
                zmeshed = mesher.get(obj_id, 
                    normals=False,
                    reduction_factor=ch['surf_resolution']*30, 
                    max_error=ch['surf_resolution']*3,
                    voxel_centered=False, 
                    )

                obj_str = f"\no {obj_id}\n"
                for v in zmeshed.vertices:
                    obj_str += "v {:.5f} {:.5f} {:.5f}\n".format(v[0]-1, v[1]-1, v[2]-1)
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