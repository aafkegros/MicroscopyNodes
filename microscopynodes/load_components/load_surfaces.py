import bpy

from .load_generic import *
from ..handle_blender_structs import *
from .. import min_nodes

    
class SurfaceIO(DataIO):
    def import_data(self, ch, scale):
        if min_keys.VOLUME in ch['collections']:
            return ch['collections'][min_keys.VOLUME], ch['metadata'][min_keys.VOLUME]
        from .load_volume import VolumeIO
        return VolumeIO().import_data(ch, scale)

class SurfaceObject(ChannelObject):
    min_type = min_keys.SURFACE
    import_node_name = "Import Microscopy Volume"   

    # identical to VolumeObject but annoyign to import
    def update_import_node(self, import_node, file_constructors, ch):
        super().update_import_node(import_node, file_constructors, ch)
        ch_to_node = {"VDB Maximum":"vdb_max","VDB Minimum":"vdb_min", "Original Maximum":"data_max"}
        for key, val in ch_to_node.items():
            import_node.inputs.get(key).default_value = ch['metadata'][self.min_type][val]
        import_node.inputs.get('Grid Name').default_value = 'data' # TEMPORARY

        for input_field in import_node.inputs: 
            if input_field.name not in ['Include', 'Normalized', 'Frame']:
                input_field.hide = True
        return 

    def add_material(self, ch):
        mat = super().add_material(ch)
        mat.blend_method = "HASHED"
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
                out = nodes.new(type="ShaderNodeOutputMaterial")
                out.location = (400,0)
            links.new(princ.outputs[0], nodes.get('Material Output').inputs[0])
        
        princ = nodes.get("Principled BSDF")
        princ.name = f"[{ch['identifier']}] principled"

        color_lut = nodes.new(type="ShaderNodeValToRGB")
        color_lut.location = (princ.location[0]-400, princ.location[1])
        color_lut.width = 300
        color_lut.name = "[color_lut]"
        color_lut.outputs[1].hide = True
        color_lut.inputs[0].default_value = 1

        links.new(color_lut.outputs[0], princ.inputs.get('Base Color'))
        links.new(color_lut.outputs[0], princ.inputs[27])

        princ.inputs.get('Alpha').default_value = 0.8
        return mat

    def channel_nodes(self, x, y, ch, in_ch, out_ch):
        mat_in, mat_out = super().channel_nodes(x, y, ch, in_ch, out_ch)
        nodes = self.node_group.nodes
        links = self.node_group.links

        v2m = nodes.new('GeometryNodeVolumeToMesh')
        v2m.name = f"VOL_TO_MESH_{ch['identifier']}"
        v2m.location = (x + 400, y)
        links.new(in_ch, v2m.inputs.get('Volume'))
        links.new(v2m.outputs.get('Mesh'), mat_in)
        
        socket_ix = get_socket(self.node_group, ch, return_ix=True, min_type="SWITCH")[1]
        threshold_socket = new_socket(self.node_group, ch, 'NodeSocketFloat', min_type='THRESHOLD',  ix=socket_ix+1)
        threshold_socket.min_value = 0.0
        threshold_socket.max_value = 1.001
        threshold_socket.attribute_domain = 'POINT'

        self.gn_mod[threshold_socket.identifier] =  ch['metadata'][self.min_type]['threshold']      
        links.new(self.node_group.nodes.get('Group Input').outputs.get(threshold_socket.name), v2m.inputs.get("Threshold"))  
        return

    def update_gn(self, ch):
        if f"VOL_TO_MESH_{ch['identifier']}" not in [node.name for node in self.node_group.nodes]:
            return
        v2m = self.node_group.nodes[f"VOL_TO_MESH_{ch['identifier']}"]

        if ch['surf_resolution'] == 0:
            v2m.inputs[1].default_value='Grid'
            return
        else:
            v2m.inputs[1].default_value='Size'
        
        for i in range(4):
            socket = get_socket(self.node_group, ch, min_type='VOXEL_SIZE', internal_append=str(i))
            if socket is not None:
                if i == ch['surf_resolution']:
                    return
                self.node_group.interface.remove(item=socket)

        socket_ix = get_socket(self.node_group, ch, min_type="SWITCH",return_ix=True)[1]
        socket = new_socket(self.node_group, ch, 'NodeSocketFloat', min_type='VOXEL_SIZE',internal_append=f"{ch['surf_resolution']}", ix=socket_ix+1)

        default_settings = [None, 0.5, 4, 15] # resolution step sizes
        in_node = get_safe_node_input(self.node_group)
        self.node_group.links.new(in_node.outputs.get(socket.name), v2m.inputs.get('Voxel Size'))
        self.gn_mod[socket.identifier] = default_settings[ch['surf_resolution']]
        return


    def update_material(self, mat, ch):
        try:
            princ = mat.node_tree.nodes.get(f"[{ch['identifier']}] principled")
            color = min_nodes.shader_nodes.get_lut(ch['cmap'], ch['single_color'])[-1]
            colornode = mat.node_tree.nodes.get(f"[color_lut]")
            min_nodes.shader_nodes.set_color_ramp_from_ch(ch, colornode)
            if ch['emission'] and princ.inputs[28].default_value == 0.0:
                princ.inputs[28].default_value = 0.5
            elif not ch['emission'] and princ.inputs[28].default_value == 0.5:
                princ.inputs[28].default_value = 0
        except Exception as e:
            print(e, 'in update surface shader')
            pass
        return
        