from .base import *
from ..min_nodes.geo_nodes.import_microscopy_meshes import import_microscopy_meshes_node_group
from ..min_nodes.shader_nodes import remap_oid_node, set_color_ramp_from_ch

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
        remap.node_tree = remap_oid_node()
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
            set_color_ramp_from_ch(ch, color_lut)
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
