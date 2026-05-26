import bpy
import numpy as np

from .base import ChannelObject
from ..handle_blender_structs.node_handling import expand_node_ui, group_input_output_for_socket, new_socket
from ..handle_blender_structs.min_keys import min_keys
from ..min_nodes.geo_nodes.import_microscopy_volume import import_microscopy_volume_node_group
from ..min_nodes.geo_nodes.join_grids import join_grids_node_group
from ..min_nodes.shader_nodes.nodeMicroscopyShading import microscopy_shading_node
from ..min_nodes.shader_nodes import set_color_ramp_from_ch, volume_alpha_node


NR_HIST_BINS = 2**16

class VolumeObject(ChannelObject):
    min_type = min_keys.VOLUME
    shader_y_step = 750

    def init_shader(self, mat):
        super().init_shader(mat)
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        links.new(nodes["Add Shaders"].outputs[0], nodes["Material Output"].inputs["Volume"])
        return

    def init_gn(self):
        super().init_gn()
        nodes = self.node_group.nodes
        links = self.node_group.links

        join_node = nodes.new("GeometryNodeGroup")
        join_node.node_tree = join_grids_node_group(self.shader_count)
        join_node.name = "Join"
        join_node.location = (800, -100)
        join_node.hide = True
        join_node.inputs["Total channels"].default_value = self.shader_count

        set_material = nodes.new('GeometryNodeSetMaterial')
        set_material.name = "Set Material"
        set_material.location = (1100, -100)

        links.new(join_node.outputs[0], set_material.inputs['Geometry'])
        links.new(set_material.outputs[0], nodes["Group Output"].inputs["Geometry"])
        return

    def ensure_channel_capacity(self):
        super().ensure_channel_capacity()
        join_node = self.node_group.nodes.get("Join")
        if join_node is not None:
            join_node.node_tree = join_grids_node_group(self.shader_count)
            join_node.inputs["Total channels"].default_value = self.shader_count

    def add_ch_to_gn(self, ch):
        in_node = self.node_group.nodes.get('Group Input')
        join_node = self.node_group.nodes.get("Join")
        links = self.node_group.links
        x, y = self.next_channel_location(in_node, join_node)
        socket = new_socket(self.node_group, ch, 'NodeSocketBool', min_type="SWITCH")

        import_node = self.node_group.nodes.new("GeometryNodeGroup")
        import_node.node_tree = import_microscopy_volume_node_group()
        import_node.location = (x, y + 100)
        import_node.name = f"IMPORT_{ch.identifier}"
        import_node.label = ch.name
        for input_field in import_node.inputs:
            if input_field.name not in ['Include', 'Normalized', 'Frame']:
                input_field.hide = True

        affine_node = self.node_group.nodes.new("FunctionNodeCombineMatrix")
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

        join_node.inputs["Total channels"].default_value = max(
            join_node.inputs["Total channels"].default_value,
            min(ch.data.ix + 1, self.shader_count),
        )
        links.new(masked_grid, join_node.inputs[str(min(ch.data.ix, self.shader_count - 1))])
        return

    def update_import_node(self, import_node, file_constructors, ch):
        super().update_import_node(import_node, file_constructors, ch)
        ch_to_node = {"VDB Maximum":"vdb_max","VDB Minimum":"vdb_min", "Original Maximum":"data_max"}
        for key, val in ch_to_node.items():
            import_node.inputs.get(key).default_value = ch.metadata[self.min_type][val]
        import_node.inputs.get('Grid Name').default_value = 'data' # TEMPORARY
        return

    def draw_histogram(self, nodes, loc, width, hist):
        histnode =nodes.new(type="ShaderNodeFloatCurve")
        histnode.location = loc
        histmap = histnode.mapping
        histnode.width = width
        histnode.label = 'Histogram (non-interactive)' 
        histnode.name = '[Histogram]'
        histnode.inputs.get('Factor').hide = True
        histnode.inputs.get('Value').hide = True
        histnode.outputs.get('Value').hide = True

        histnorm = hist / np.max(hist)
        if len(histnorm) > 150:
            histnorm = binned_statistic_sum(np.arange(len(histnorm)), histnorm, bins=150)
            histnorm /= np.max(histnorm) 
        for ix, val in enumerate(histnorm):
            if ix == 0:
                histmap.curves[0].points[-1].location = ix/len(histnorm), val
                histmap.curves[0].points.new((ix + 0.9)/len(histnorm), val)
            if ix==len(histnorm)-1:
                histmap.curves[0].points[-1].location = ix/len(histnorm), val
            else:
                histmap.curves[0].points.new(ix/len(histnorm), val)
                histmap.curves[0].points.new((ix + 0.9)/len(histnorm), val)
            histmap.curves[0].points[ix].handle_type = 'VECTOR'
        return histnode

    def update_material(self, mat, ch):
        nodes = mat.node_tree.nodes

        color_lut = nodes.get(f'[color_lut_{ch.identifier}]')
        if color_lut is not None:
            set_color_ramp_from_ch(ch, color_lut)

        if self.min_type in ch.metadata:
            histnode = nodes.get(f'[Histogram_{ch.identifier}]')
            if ch.metadata[self.min_type] is not None and histnode is not None:
                new_histnode = self.draw_histogram(nodes, histnode.location, histnode.width, ch.metadata[self.min_type]['histogram'])
                new_histnode.name = histnode.name
                new_histnode.label = histnode.label
                new_histnode.parent = histnode.parent
                nodes.remove(histnode)

        microscopy_shading = nodes.get(f'[microscopy_shading_{ch.identifier}]')
        if microscopy_shading is not None:
            microscopy_shading.inputs["Emission / Scattering"].default_value = float(not ch.viz.emission)
        return

    def init_channel_shader(self, mat, ch):
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        y_offset = -self.shader_y_step * ch.data.ix

        node_attr = nodes.new(type='ShaderNodeAttribute')
        node_attr.location = (-1600, y_offset)
        node_attr.name = f"[channel_load_{ch.identifier}]"
        node_attr.attribute_name = f'Channel {ch.data.ix}'
        node_attr.label = ch.name
        node_attr.hide = True

        ramp_node = nodes.new(type="ShaderNodeValToRGB")
        ramp_node.location = (-1200, y_offset)
        ramp_node.width = 1000
        ramp_node.color_ramp.elements[0].position = ch.metadata[self.min_type]['threshold']
        ramp_node.color_ramp.elements[0].color = (1,1,1,0)
        ramp_node.color_ramp.elements[1].color = (1,1,1,1)
        ramp_node.color_ramp.elements[1].position = 1
        ramp_node.name = f'[alpha_ramp_{ch.identifier}]'
        ramp_node.label = "Pixel Intensities"
        ramp_node.show_options = True
        if 'threshold_upper' in ch.metadata[self.min_type]:
            ramp_node.color_ramp.elements[1].position = ch.metadata[self.min_type]['threshold_upper']
        ramp_node.outputs[0].hide = True
        links.new(node_attr.outputs.get('Fac'), ramp_node.inputs.get("Fac"))  

        histnode = self.draw_histogram(nodes, (-1200, y_offset + 300), 1000, ch.metadata[self.min_type]['histogram'])
        histnode.name = f'[Histogram_{ch.identifier}]'

        alphanode =  nodes.new('ShaderNodeGroup')
        alphanode.node_tree = volume_alpha_node()
        alphanode.name = f'[volume_alpha_{ch.identifier}]'
        alphanode.location = (-300, y_offset - 120)
        alphanode.inputs.get("Alpha").default_value = 1
        alphanode.inputs.get("Alpha-Intensity Coupling").default_value = 1
        links.new(ramp_node.outputs.get('Alpha'), alphanode.inputs.get("Value"))
        alphanode.width = 300
        expand_node_ui(alphanode)

        color_lut = nodes.new(type="ShaderNodeValToRGB")
        color_lut.location = (-300, y_offset + 120)
        color_lut.width = 300
        color_lut.name = f"[color_lut_{ch.identifier}]"
        color_lut.show_options = True
        color_lut.outputs[1].hide = True
        links.new(ramp_node.outputs[1], color_lut.inputs[0])

        microscopy_shading = nodes.new("ShaderNodeGroup")
        microscopy_shading.node_tree = microscopy_shading_node()
        microscopy_shading.name = f"[microscopy_shading_{ch.identifier}]"
        microscopy_shading.location = (150, y_offset)
        microscopy_shading.width = 300
        microscopy_shading.inputs["Emission / Scattering"].default_value = float(not ch.viz.emission)
        for socket_name in ("Color", "Alpha", "Alpha-Intensity Coupling"):
            microscopy_shading.inputs[socket_name].hide_value = True
        expand_node_ui(microscopy_shading)

        frame, _ = self.add_ch_to_shader(mat, ch, microscopy_shading.outputs["Shader"])
        for node in (node_attr, ramp_node, histnode, alphanode, color_lut, microscopy_shading):
            node.parent = frame

        links.new(color_lut.outputs[0], microscopy_shading.inputs["Color"])
        links.new(alphanode.outputs.get("Alpha"), microscopy_shading.inputs["Alpha"])
        links.new(alphanode.outputs.get("Alpha-Intensity Coupling"), microscopy_shading.inputs["Alpha-Intensity Coupling"])
        return

# simplified version of https://github.com/scipy/scipy/blob/v1.16.2/scipy/stats/_binned_statistic.py
def binned_statistic_sum(x, values, bins):
    x = np.asarray(x)
    values = np.asarray(values)
    bins = np.linspace(x.min(), x.max(), bins + 1)  # bin edges
    bin_indices = np.searchsorted(bins, x, side='right') - 1
    bin_indices = np.clip(bin_indices, 0, bins.size - 2)
    
    sums = np.zeros(bins.size - 1, dtype=values.dtype)
    np.add.at(sums, bin_indices, values)  # sum values in each bin
    return sums
    
