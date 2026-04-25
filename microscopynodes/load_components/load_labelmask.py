import numpy as np
import bpy
import bmesh
from pathlib import Path
import json
import os

from ..handle_blender_structs import *
from .base import *
from .. import min_nodes
from ..min_nodes.geo_nodes.import_microscopy_meshes import import_microscopy_meshes_node_group
import zmesh

class LabelmaskIO(DataIO):
    min_type = min_keys.LABELMASK
    MASK_TEMPLATE = Path("{cache_dir}") / "{dataset_hash}" / "mask_{resolution}" / "c{channel_ix}_t{t}"

    def generate_file_constructors(self, ch):
        file_constructors = []
        for t in range(ch.frame_start, ch.frame_end + 1):
            if t >= len_axis('t', ch.axes_order, ch.data.shape):
                break
            file_constructors.append({
                **self.base_constructor(ch),
                "resolution": ch.surf_resolution,
                "t": t, 
                "channel_ix" : ch.ix,
                "template_str" : str(self.MASK_TEMPLATE),
            })
        return file_constructors

    def export_ch(self, ch, file_constructors):
        mesher = zmesh.Mesher((1,1,1))
        for constructor in file_constructors: # loops through time
            fname = Path(str(self.MASK_TEMPLATE).format(**constructor)).with_suffix('.obj')
            fname_ids = fname.with_suffix('.csv')
            fname.parent.mkdir(parents=True, exist_ok=True)

            if Path(fname).exists():
                if ch.force_remaking_files:
                    Path(fname).unlink()
                else: 
                    continue
            with open(str(fname_ids), 'ab+') as ofs:
                ofs.write(f"oid\n".encode('utf-8'))
            
            timeframe_arr = take_index(ch.data, constructor['t'], 't', ch.axes_order).compute()
            timeframe_arr = to_xyz(timeframe_arr,  ch.axes_order.replace('t', ''))
            
            log(f"Meshing timepoint {constructor['t']}")

            mesher.mesh(timeframe_arr, close=True)
            
            vertex_offset = 0
            for obj_id in mesher.ids():
                log(f"Writing object {obj_id} at time {constructor['t']}")
                zmeshed = mesher.get(obj_id, 
                    normals=False,
                    reduction_factor=ch.surf_resolution*30, 
                    max_error=ch.surf_resolution*3,
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
            (
                int(line)
                for filepath in files
                if filepath.exists()
                for i, line in enumerate(open(filepath))
                if i > 0 # skips header
            ),
            default=0,
        )
        return {'max': max_oid}



class LabelmaskObject(MeshChannelObject):
    min_type = min_keys.LABELMASK

    def import_node_tree(self):
        return import_microscopy_meshes_node_group()

    def init_shader(self, mat):
        super().init_shader(mat)
        mat.blend_method = "BLEND"
        return

    def init_channel_shader(self, mat, ch):
        super().init_channel_shader(mat, ch)
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        y_offset = -self.shader_y_step() * ch.ix
        frame = nodes[f"[frame_{ch.identifier}]"]
        color_lut = nodes[f"[color_lut_{ch.identifier}]"]

        idnode = nodes.new("ShaderNodeAttribute")
        idnode.name = f"[oid_{ch.identifier}]"
        idnode.attribute_name = 'oid'
        idnode.attribute_type = 'GEOMETRY'
        idnode.location = (-760, y_offset - 35)
        idnode.parent = frame

        remap = nodes.new('ShaderNodeGroup')
        remap.node_tree = min_nodes.shader_nodes.remap_oid_node()
        remap.name = f"[remap_oid_{ch.identifier}]"
        remap.location = (-420, y_offset - 35)
        remap.show_options = False
        remap.inputs.get('# Objects').default_value = ch.metadata[self.min_type]['max']
        remap.parent = frame

        links.new(idnode.outputs.get('Fac'), remap.inputs.get('Value'))
        links.new(remap.outputs[0], color_lut.inputs[0])
        return


    def update_material(self, mat, ch):
        try:
            nodes =  mat.node_tree.nodes
            color_lut = nodes.get(f'[color_lut_{ch.identifier}]')
            remap = nodes.get(f'[remap_oid_{ch.identifier}]')
            min_nodes.shader_nodes.set_color_ramp_from_ch(ch, color_lut)
            if remap is not None and color_lut is not None:
                remap.inputs.get('# Objects').default_value = ch.metadata[self.min_type]['max']
                remap.inputs.get('Revolving Colormap').default_value = (color_lut.color_ramp.interpolation == 'CONSTANT')
                remap.inputs.get('# Colors').default_value = max(len(color_lut.color_ramp.elements), 5)
            princ = mat.node_tree.nodes.get(f"[{ch.identifier}] principled")
            if princ is not None and ch.emission and princ.inputs[28].default_value == 0.0:
                princ.inputs[28].default_value = 0.5
            elif princ is not None and not ch.emission and princ.inputs[28].default_value == 0.5:
                princ.inputs[28].default_value = 0
        except Exception as e:
            print(e)
            pass
        return
