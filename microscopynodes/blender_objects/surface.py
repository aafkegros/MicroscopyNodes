import bpy

from .base import MeshChannelObject
from ..handle_blender_structs.node_handling import get_socket, group_input_output_for_socket, new_socket
from ..handle_blender_structs.min_keys import min_keys
from ..min_nodes.geo_nodes.import_microscopy_volume import import_microscopy_volume_node_group
from ..min_nodes.shader_nodes import set_color_ramp_from_ch


class SurfaceObject(MeshChannelObject):
    min_type = min_keys.SURFACE

    # identical to VolumeObject but annoyign to import
    def update_import_node(self, import_node, file_constructors, ch):
        super().update_import_node(import_node, file_constructors, ch)
        ch_to_node = {"VDB Maximum":"vdb_max","VDB Minimum":"vdb_min", "Original Maximum":"data_max"}
        for key, val in ch_to_node.items():
            import_node.inputs.get(key).default_value = ch.metadata[self.min_type][val]
        import_node.inputs.get('Grid Name').default_value = 'data' # TEMPORARY

        for input_field in import_node.inputs: 
            if input_field.name not in ['Include', 'Normalized', 'Frame']:
                input_field.hide = True
        return 

    def init_shader(self, mat):
        super().init_shader(mat)
        mat.blend_method = "HASHED"
        return

    def add_ch_to_gn(self, ch):
        nodes = self.node_group.nodes
        links = self.node_group.links

        in_node = nodes.get('Group Input')
        join_node = nodes.get("Join")
        x, y = self.next_channel_location(in_node, join_node)
        socket = new_socket(self.node_group, ch, 'NodeSocketBool', min_type="SWITCH")

        import_node = nodes.new("GeometryNodeGroup")
        import_node.node_tree = import_microscopy_volume_node_group()
        import_node.location = (x, y + 100)
        import_node.name = f"IMPORT_{ch.identifier}"
        import_node.label = ch.name
        for input_field in import_node.inputs:
            if input_field.name not in ['Include', 'Normalized', 'Frame']:
                input_field.hide = True

        affine_node = nodes.new("FunctionNodeCombineMatrix")
        affine_node.name = f"channel_affine_{ch.identifier}"
        affine_node.label = f"{ch.name} affine"
        affine_node.location = (x - 180, y - 90)
        for affine_socket in affine_node.inputs:
            if not affine_socket.is_linked:
                affine_socket.hide = True
        links.new(in_node.outputs["Frame"], import_node.inputs["Frame"])
        links.new(affine_node.outputs["Matrix"], import_node.inputs["Channel Affine Matrix"])
        links.new(group_input_output_for_socket(in_node, socket), import_node.inputs.get("Include"))

        masked_grid = self.mask_grid_for_slice_cube(x, y, ch, import_node.outputs["Grid"])

        socket_ix = get_socket(self.node_group, ch, return_ix=True, min_type="SWITCH")[1]
        threshold_socket = new_socket(self.node_group, ch, 'NodeSocketFloat', min_type='THRESHOLD',  ix=socket_ix+1)
        threshold_socket.min_value = 0.0
        threshold_socket.max_value = 1.001
        threshold_socket.attribute_domain = 'POINT'

        self.gn_mod[threshold_socket.identifier] =  ch.metadata[self.min_type]['threshold']      
        threshold = group_input_output_for_socket(nodes.get('Group Input'), threshold_socket)

        grid_to_mesh = nodes.new('GeometryNodeGridToMesh')
        grid_to_mesh.name = f"GRID_TO_MESH_{ch.identifier}"
        grid_to_mesh.location = (x + 750, y)
        links.new(masked_grid, grid_to_mesh.inputs.get('Grid'))
        links.new(threshold, grid_to_mesh.inputs.get("Threshold"))

        out_ch = self.store_channel_attribute(x + 1000, y, ch, grid_to_mesh.outputs.get('Mesh'))
        links.new(out_ch, join_node.inputs["Geometry"])
        return

    def update_gn(self, ch):
        for i in range(4):
            socket = get_socket(self.node_group, ch, min_type='VOXEL_SIZE', internal_append=str(i))
            if socket is not None:
                self.node_group.interface.remove(item=socket)
        return


    def update_material(self, mat, ch):
        try:
            princ = mat.node_tree.nodes.get(f"[{ch.identifier}] principled")
            colornode = mat.node_tree.nodes.get(f"[color_lut_{ch.identifier}]")
            set_color_ramp_from_ch(ch, colornode)
            if princ is not None and ch.viz.emission and princ.inputs[28].default_value == 0.0:
                princ.inputs[28].default_value = 0.5
            elif princ is not None and not ch.viz.emission and princ.inputs[28].default_value == 0.5:
                princ.inputs[28].default_value = 0
        except Exception as e:
            print(e, 'in update surface shader')
            pass
        return
