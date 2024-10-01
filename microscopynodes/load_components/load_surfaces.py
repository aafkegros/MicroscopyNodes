import bpy

from .load_generic import *
from ..handle_blender_structs import *
    
class SurfaceIO(DataIO):
    def import_data(self, ch, scale):
        if min_keys.VOLUME in ch['collections']:
            return ch['collections'][min_keys.VOLUME], ch['metadata'][min_keys.VOLUME]
        from .load_volume import VolumeIO
        return VolumeIO().import_data(ch, scale)


class SurfaceObject(ChannelObject):
    min_type = min_keys.SURFACE

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
            princ = nodes.new("ShaderNodeBsdfPrincipled")
            links.new(princ.outputs[0], nodes.get('Material Output').inputs[0])
        
        princ = nodes.get("Principled BSDF")
        princ.name = f"[{ch['identifier']}] principled"
        color = get_cmap('default_ch')[ch['ix'] % len(get_cmap('default_ch'))]
        princ.inputs.get('Base Color').default_value = color
        princ.inputs[26].default_value = color

        colornode = nodes.new("ShaderNodeRGB")
        colornode.location = (princ.location[0]-200, princ.location[1])
        colornode.outputs[0].default_value = color
        links.new(colornode.outputs[0], princ.inputs.get('Base Color'))
        links.new(colornode.outputs[0], princ.inputs[26])

        princ.inputs.get('Alpha').default_value = 0.5
        return mat

    def append_channel_to_holder(self, ch):
        super().append_channel_to_holder(ch)
        in_node = get_safe_node_input(self.node_group)
        nodes = self.node_group.nodes
        links = self.node_group.links
        # can be explicitly named as this should only be called upon appending a channel
        edit_in = nodes[f"edit_in_{ch['identifier']}"]
        edit_out = nodes[f"edit_out_{ch['identifier']}"]
        editframe = nodes[f"editframe_{ch['identifier']}"]

        v2m = nodes.new('GeometryNodeVolumeToMesh')
        v2m.name = f"VOL_TO_MESH_{ch['identifier']}"
        v2m.location = (edit_in.location[0] + 400, edit_in.location[1])
        v2m.parent = editframe
        links.new(edit_in.outputs[0], v2m.inputs.get('Volume'))
        links.new(v2m.outputs.get('Mesh'), edit_out.inputs[0])
        
        socket_ix = get_socket(self.node_group, ch, return_ix=True, min_type="SWITCH")[1]
        threshold_socket = new_socket(self.node_group, ch, 'NodeSocketFloat', min_type='THRESHOLD',  ix=socket_ix+1)
        threshold_socket.min_value = 0.0
        threshold_socket.max_value = 1.001
        threshold_socket.attribute_domain = 'POINT'
        self.gn_mod[threshold_socket.identifier] =  ch['metadata'][self.min_type]['threshold']

        normnode = self.node_group.nodes.new(type="ShaderNodeMapRange")
        normnode.location =(edit_in.location[0] + 200, edit_in.location[1]-150)
        normnode.label = "Normalize data"
        normnode.inputs[3].default_value = ch['metadata'][self.min_type]['range'][0]       
        normnode.inputs[4].default_value = ch['metadata'][self.min_type]['range'][1]       
        links.new(in_node.outputs.get(threshold_socket.name), normnode.inputs[0])  
        links.new(normnode.outputs[0], v2m.inputs.get("Threshold"))  
        normnode.hide = True
        return

    def update_gn(self, ch):
        if f"VOL_TO_MESH_{ch['identifier']}" not in [node.name for node in self.node_group.nodes]:
            return
        v2m = self.node_group.nodes[f"VOL_TO_MESH_{ch['identifier']}"]

        if ch['surf_resolution'] == 0:
            v2m.resolution_mode='GRID'
            return
        else:
            v2m.resolution_mode='VOXEL_SIZE'
        
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


    def update_shader(self, mat, ch):
        try:
            princ = mat.node_tree.nodes.get(f"[{ch['identifier']}] principled")
            if ch['emission'] and princ.inputs[27].default_value == 0.0:
                princ.inputs[27].default_value = 0.5
            elif not ch['emission'] and princ.inputs[27].default_value == 0.5:
                princ.inputs[27].default_value = 0
        except:
            pass
        return
        