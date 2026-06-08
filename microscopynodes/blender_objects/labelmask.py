from .base import MeshChannelObject
from ..handle_blender_structs.node_handling import group_input_output_for_socket, new_socket
from ..handle_blender_structs.min_keys import min_keys
from ..min_nodes.geo_nodes.import_microscopy_meshes import import_microscopy_meshes_node_group
from ..min_nodes.geo_nodes.masking.nodeMaskMesh import mask_mesh_node_group
from ..min_nodes.shader_nodes import remap_oid_node, set_color_ramp_from_ch

class LabelmaskObject(MeshChannelObject):
    min_type = min_keys.LABELMASK

    def update_import_node(self, import_node, file_constructors, ch):
        super().update_import_node(import_node, file_constructors, ch)

    def init_shader(self, mat):
        super().init_shader(mat)
        mat.blend_method = "BLEND"
        return

    def add_ch_to_gn(self, ch):
        nodes = self.node_group.nodes
        links = self.node_group.links

        in_node = nodes.get('Group Input')
        join_node = nodes.get("Join")
        x, y = self.next_channel_location(in_node, join_node)
        socket = new_socket(self.node_group, ch, 'NodeSocketBool', min_type="SWITCH")

        import_node = nodes.new("GeometryNodeGroup")
        import_node.node_tree = import_microscopy_meshes_node_group()
        import_node.location = (x, y + 100)
        import_node.name = f"IMPORT_{ch.identifier}"
        import_node.label = ch.name
        for input_field in import_node.inputs:
            if input_field.name != "Include":
                input_field.hide = True

        affine_node = nodes.new("FunctionNodeCombineMatrix")
        affine_node.name = f"channel_affine_{ch.identifier}"
        affine_node.label = f"{ch.name} affine"
        affine_node.location = (x - 180, y - 90)
        for affine_socket in affine_node.inputs:
            if not affine_socket.is_linked:
                affine_socket.hide = True
        links.new(affine_node.outputs["Matrix"], import_node.inputs["Channel Affine Matrix"])
        links.new(group_input_output_for_socket(in_node, socket), import_node.inputs.get("Include"))

        mask_mesh = nodes.new("GeometryNodeGroup")
        mask_mesh.node_tree = mask_mesh_node_group()
        mask_mesh.name = f"SLICE_CUBE_{ch.identifier}"
        mask_mesh.location = (x + 170, y)
        mask_mesh.show_options = False
        if mask_mesh.inputs.get("With") is not None:
            mask_mesh.inputs["With"].default_value = 'Box'

        links.new(import_node.outputs["Geometry"], mask_mesh.inputs["Mesh"])
        self.add_channel_to_bundle(ch, mask_mesh.outputs["Inside Mask"], "GEOMETRY")
        return

    def init_channel_shader(self, mat, ch):
        super().init_channel_shader(mat, ch)
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        y_offset = -self.shader_y_step * ch.data.ix
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
            if princ is not None and ch.viz.emission and princ.inputs[29].default_value == 0.0:
                princ.inputs[29].default_value = 0.5
            elif princ is not None and not ch.viz.emission and princ.inputs[29].default_value == 0.5:
                princ.inputs[29].default_value = 0
        except Exception as e:
            print(e)
            pass
        return
