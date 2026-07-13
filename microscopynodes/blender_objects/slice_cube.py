import bpy
import numpy as np

from .base import MiNObject
from ..handle_blender_structs.min_keys import min_keys
from ..handle_blender_structs.node_handling import (
    expand_node_ui,
)
from ..min_nodes.geo_nodes.annotation.nodeScaleBox import AXIS_ITEM_NAMES, scalebox_node_group
from ..min_nodes.geo_nodes.measure.nodeSampleGridOnMesh import sample_grid_on_mesh_node_group
from ..min_nodes.geo_nodes.utilities.import_microscopy_volume import import_microscopy_volume_node_group
from ..min_nodes.shader_nodes import (
    add_shaders_node,
    colormap_to_lut,
    set_color_ramp_from_ch,
)
from ..min_nodes.shader_nodes.handle_cmap import set_color_ramp

class SliceCubeObject(MiNObject):
    min_type = min_keys.SLICECUBE
    shader_count = 10
    shader_y_step = 700
    projection_frame_name = "[Slice Cube Projection Frame]"
    projection_frame_label = "Slice Cube Projection: Only Used If Show Slice Projection Is On"
    projection_frame_color = (0.663, 0.506, 0.506)
    
    def init_obj(self): 
        super().init_obj()
        slicecube = self.object
        slicecube.name = "slice cube"

        bpy.ops.object.modifier_add(type='NODES')
        slicecube.modifiers[-1].name = f"[Microscopy Nodes slicecube]"
        slicecube.modifiers[-1].node_group = bpy.data.node_groups.new("slice cube", 'GeometryNodeTree')
        self.init_gn()

        mat = bpy.data.materials.new(f'Slice Cube')
        mat.blend_method = "HASHED"
        self.init_shader(mat)
        self.ensure_material_slot(mat)
        return slicecube

    def ensure_gn(self):
        mod = self.gn_mod
        if mod is None:
            bpy.context.view_layer.objects.active = self.object
            self.object.select_set(True)
            bpy.ops.object.modifier_add(type='NODES')
            mod = self.object.modifiers[-1]
            mod.name = f"[Microscopy Nodes slicecube]"
        if mod.node_group is None:
            mod.node_group = bpy.data.node_groups.new("slice cube", 'GeometryNodeTree')
            self.init_gn()
            return
        if mod.node_group.nodes.get("Show Slice Projection Switch") is None:
            self.init_gn()
            return
        if self.interface_socket("Sampling Pixel Spacing") is None:
            self.init_gn()

    def init_gn(self):
        node_group = self.node_group
        nodes = node_group.nodes
        links = node_group.links
        nodes.clear()
        self.clear_interface(node_group)
        node_group.interface.new_socket(name='Geometry', in_out="INPUT", socket_type='NodeSocketGeometry')
        show_data_socket = node_group.interface.new_socket(
            name='Show Slice Projection',
            in_out="INPUT",
            socket_type='NodeSocketBool',
        )
        show_data_socket.default_value = False
        pixel_spacing_socket = node_group.interface.new_socket(
            name='Sampling Pixel Spacing',
            in_out="INPUT",
            socket_type='NodeSocketFloat',
        )
        pixel_spacing_socket.default_value = 0.1
        pixel_spacing_socket.min_value = 1e-6
        if hasattr(pixel_spacing_socket, "subtype"):
            pixel_spacing_socket.subtype = 'DISTANCE'
        node_group.interface.new_socket(name='Geometry', in_out="OUTPUT", socket_type='NodeSocketGeometry')

        inputnode = nodes.new('NodeGroupInput')
        inputnode.location = (-900, 0)

        outputnode = nodes.new('NodeGroupOutput')
        outputnode.location = (700, 0)
        outputnode.is_active_output = True

        projection_grid = self.build_projection_grid_nodes(nodes, links, inputnode)

        projection_switch = nodes.new("GeometryNodeSwitch")
        projection_switch.name = "Show Slice Projection Switch"
        projection_switch.input_type = 'GEOMETRY'
        projection_switch.location = (350, 0)

        capture_show_data = nodes.new("GeometryNodeStoreNamedAttribute")
        capture_show_data.name = "Store Show Slice Projection"
        capture_show_data.data_type = 'BOOLEAN'
        capture_show_data.domain = 'POINT'
        capture_show_data.location = (520, 0)
        capture_show_data.inputs["Name"].default_value = "Show Slice Projection"

        set_material = nodes.new("GeometryNodeSetMaterial")
        set_material.name = "Set Projection Material"
        set_material.location = (650, 0)

        links.new(inputnode.outputs["Geometry"], projection_switch.inputs["False"])
        links.new(projection_grid.outputs["Geometry"], projection_switch.inputs["True"])
        links.new(inputnode.outputs["Show Slice Projection"], projection_switch.inputs["Switch"])
        links.new(projection_switch.outputs["Output"], capture_show_data.inputs["Geometry"])
        links.new(inputnode.outputs["Show Slice Projection"], capture_show_data.inputs["Value"])
        links.new(capture_show_data.outputs["Geometry"], set_material.inputs["Geometry"])
        links.new(set_material.outputs["Geometry"], outputnode.inputs["Geometry"])
        self.frame_projection_nodes(nodes)

    def build_projection_grid_nodes(self, nodes, links, inputnode):
        projection_box = nodes.new("GeometryNodeGroup")
        projection_box.node_tree = slice_projection_box_node_group()
        projection_box.name = "Slice Projection Grid"
        projection_box.location = (inputnode.location[0] + 260, inputnode.location[1] - 320)
        links.new(inputnode.outputs["Sampling Pixel Spacing"], projection_box.inputs["Sampling Pixel Spacing"])
        return projection_box

    def projection_frame(self, nodes):
        frame = nodes.get(self.projection_frame_name)
        if frame is None:
            frame = nodes.new("NodeFrame")
            frame.name = self.projection_frame_name
        frame.label = self.projection_frame_label
        frame.label_size = 50
        frame.shrink = True
        frame.use_custom_color = True
        frame.color = self.projection_frame_color
        return frame

    def frame_projection_nodes(self, nodes, extra_nodes=()):
        frame = self.projection_frame(nodes)
        for node in list(nodes) + list(extra_nodes):
            if node is frame:
                continue
            node.parent = frame
        return frame

    def clear_interface(self, node_group):
        try:
            node_group.interface.clear()
            return
        except AttributeError:
            pass
        for item in reversed(node_group.interface.items_tree):
            node_group.interface.remove(item=item)

    def interface_socket(self, name):
        if self.node_group is None:
            return None
        for item in self.node_group.interface.items_tree:
            if getattr(item, "item_type", None) == 'SOCKET' and item.in_out == 'INPUT' and item.name == name:
                return item
        return None

    def set_data(self, dataset_model):
        self.ensure_gn()
        self.ensure_material()
        self.dataset_name = dataset_model.name
        self.shader_count = max(len(dataset_model.channels) + 2, 1)
        self.ensure_shader_capacity()
        for ch in dataset_model.channels:
            if not self._channel_source_type(ch):
                continue
            self.update_ch_data(ch)

    def update_ch_data(self, ch):
        source_type = self._channel_source_type(ch)
        file_constructors = ch.files_for(source_type).constructors
        if not file_constructors:
            return
        if not self.ch_present(ch):
            self.add_ch_to_gn(ch, source_type)
            self.init_channel_shader(self.object.data.materials[0], ch, source_type)
        self.update_import_node(self.node_group.nodes[f"IMPORT_{ch.identifier}"], file_constructors, ch, source_type)

    def _channel_source_type(self, ch):
        for source_type in (min_keys.VOLUME, min_keys.SURFACE):
            if getattr(ch.viz, source_type.name.lower(), False):
                return source_type
        return None

    def ch_present(self, ch):
        return f"IMPORT_{ch.identifier}" in [node.name for node in self.node_group.nodes]

    def add_ch_to_gn(self, ch, source_type):
        nodes = self.node_group.nodes
        links = self.node_group.links
        inputnode = nodes.get('Group Input')
        projection_switch = nodes.get("Show Slice Projection Switch")
        x, y = self.next_channel_location()

        import_node = nodes.new("GeometryNodeGroup")
        import_node.node_tree = import_microscopy_volume_node_group()
        import_node.location = (x, y + 100)
        import_node.name = f"IMPORT_{ch.identifier}"
        import_node.label = ch.name
        for input_field in import_node.inputs:
            if input_field.name not in ("Include", "Normalized"):
                input_field.hide = True

        affine_node = nodes.new("FunctionNodeCombineMatrix")
        affine_node.name = f"channel_affine_{ch.identifier}"
        affine_node.label = f"{ch.name} affine"
        affine_node.location = (x - 180, y - 90)
        for affine_socket in affine_node.inputs:
            if not affine_socket.is_linked:
                affine_socket.hide = True
        links.new(affine_node.outputs["Matrix"], import_node.inputs["Channel Affine Matrix"])
        links.new(inputnode.outputs["Show Slice Projection"], import_node.inputs.get("Include"))

        sampler = nodes.new("GeometryNodeGroup")
        sampler.node_tree = sample_grid_on_mesh_node_group()
        sampler["channel_identifier"] = ch.identifier
        true_input = projection_switch.inputs["True"]
        previous_geometry = true_input.links[0].from_socket
        previous_node = previous_geometry.node
        channel_load_x = import_node.location[0] + import_node.width
        previous_x = max(previous_node.location[0], channel_load_x)
        sampler.location = (
            previous_x + 260,
            nodes["Slice Projection Grid"].location[1],
        )
        sampler.inputs["Name"].default_value = ch.name.replace("-", "_")
        sampler.inputs["Mesh parented by holder"].default_value = False

        links.remove(true_input.links[0])
        links.new(import_node.outputs["Grid"], sampler.inputs["Grid"])
        links.new(previous_geometry, sampler.inputs["Mesh"])
        links.new(sampler.outputs["Mesh"], true_input)
        self.frame_projection_nodes(nodes, (import_node, affine_node, sampler))
        self.move_projection_tail(sampler.location[0])

    def move_projection_tail(self, after_x):
        nodes = self.node_group.nodes
        tail_positions = {
            "Show Slice Projection Switch": (after_x + 320, 0),
            "Store Show Slice Projection": (after_x + 540, 0),
            "Set Projection Material": (after_x + 720, 0),
            "Group Output": (after_x + 940, 0),
        }
        for name, location in tail_positions.items():
            node = nodes.get(name)
            if node is not None:
                node.location = location

    def update_import_node(self, import_node, file_constructors, ch, source_type):
        metadata = ch.files_for(source_type).metadata
        for key, val in file_constructors[0].items():
            if key == 't':
                key = 'Frame'
            if import_node.inputs.get(key) is None:
                continue
            if import_node.inputs.get(key).type == "STRING":
                import_node.inputs.get(key).default_value = str(val)
                continue
            try:
                import_node.inputs.get(key).default_value = int(val)
            except Exception:
                import_node.inputs.get(key).default_value = str(val)
        ch_to_node = {"VDB Maximum": "vdb_max", "VDB Minimum": "vdb_min", "Original Maximum": "data_max"}
        for key, val in ch_to_node.items():
            import_node.inputs.get(key).default_value = metadata[val]
        import_node.inputs.get('Grid Name').default_value = 'data'
        import_node.label = ch.name
        self.update_import_affine(ch)

    def update_import_affine(self, ch):
        affine = np.array(ch.data.affine, dtype=float)
        affine_node = self.node_group.nodes.get(f"channel_affine_{ch.identifier}")
        if affine_node is None:
            return
        for row in range(4):
            for column in range(4):
                affine_node.inputs[column * 4 + row].default_value = float(affine[row, column])

    def set_holder(self, holder):
        for node in self.node_group.nodes:
            if node.inputs.get("Holder") is not None:
                node.inputs["Holder"].default_value = holder
                node.inputs["Holder"].hide = True

    def set_settings(self, dataset_model):
        self.ensure_gn()
        self.ensure_material()
        initialize = self.object.parent is None
        _, _, dataset_extents = dataset_model.intermediate_bbox
        if initialize:
            self.object.location = dataset_extents / 2.0
            self.object.scale = np.maximum(dataset_extents / 2.0 + 1e-5, 1e-5)
        self.object.display_type = 'TEXTURED'
        for ch in dataset_model.channels:
            if not self.ch_present(ch):
                continue
            self.update_channel_names(ch)
            source_type = self._channel_source_type(ch)
            mat = self.object.data.materials[0]
            self.update_material(mat, ch, source_type)
        self.ensure_shader_capacity()

    def ensure_material(self):
        if len(self.object.data.materials) == 0 or self.object.data.materials[0] is None:
            mat = bpy.data.materials.new(f'Slice Cube')
            self.init_shader(mat)
            self.ensure_material_slot(mat)
            self.set_projection_material(mat)
            return

        mat = self.object.data.materials[0]
        if not mat.use_nodes or mat.node_tree.nodes.get("Add Shaders") is None:
            self.init_shader(mat)
        self.set_projection_material(mat)

    def set_projection_material(self, mat):
        set_material = self.node_group.nodes.get("Set Projection Material")
        if set_material is not None:
            set_material.inputs["Material"].default_value = mat

    def next_channel_location(self):
        min_y_loc = 300
        skip_names = {
            "Group Input",
            "Group Output",
            "Show Slice Projection Switch",
            "Store Show Slice Projection",
            "Set Projection Material",
            "Slice Projection Grid",
            self.projection_frame_name,
        }
        for node in self.node_group.nodes:
            if node.name not in skip_names:
                min_y_loc = min(min_y_loc, node.location[1])
        return -500, min_y_loc - 300

    def init_shader(self, mat):
        mat.use_nodes = True
        mat.blend_method = "HASHED"
        nodes = mat.node_tree.nodes
        nodes.clear()

        output = nodes.new("ShaderNodeOutputMaterial")
        output.name = "Material Output"
        output.location = (1300, 0)
        output.is_active_output = True

        show_data_attr = nodes.new(type='ShaderNodeAttribute')
        show_data_attr.location = (620, -180)
        show_data_attr.name = "[show_slice_projection]"
        show_data_attr.attribute_name = "Show Slice Projection"
        show_data_attr.label = "Show Slice Projection"

        transparent = nodes.new("ShaderNodeBsdfTransparent")
        transparent.name = "[transparent_when_not_using_show_slice_projection]"
        transparent.location = (860, -220)

        show_data_mix = nodes.new("ShaderNodeMixShader")
        show_data_mix.name = "[mix_show_slice_projection]"
        show_data_mix.location = (1080, 0)

        add_shaders = nodes.new("ShaderNodeGroup")
        add_shaders.node_tree = add_shaders_node(self.shader_count)
        add_shaders.name = "Add Shaders"
        add_shaders.width = 100
        add_shaders.location = (760, 80)
        expand_node_ui(add_shaders)
        mat.node_tree.links.new(show_data_attr.outputs["Fac"], show_data_mix.inputs[0])
        mat.node_tree.links.new(transparent.outputs[0], show_data_mix.inputs[1])
        mat.node_tree.links.new(add_shaders.outputs[0], show_data_mix.inputs[2])
        mat.node_tree.links.new(show_data_mix.outputs[0], output.inputs["Surface"])
        self.frame_projection_nodes(nodes)

    def ensure_shader_capacity(self):
        for mat in self.object.data.materials:
            if mat is None or not mat.use_nodes:
                continue
            add_shaders = mat.node_tree.nodes.get("Add Shaders")
            if add_shaders is not None:
                add_shaders.node_tree = add_shaders_node(self.shader_count)

    def init_channel_shader(self, mat, ch, source_type):
        metadata = ch.files_for(source_type).metadata
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        y_offset = -self.shader_y_step * ch.data.ix

        node_attr = nodes.new(type='ShaderNodeAttribute')
        node_attr.location = (-1600, y_offset)
        node_attr.name = f"[channel_load_{ch.identifier}]"
        node_attr.attribute_name = ch.name.replace("-", "_")
        node_attr.label = ch.name.replace("-", "_")

        histnode = self.draw_histogram(
            nodes,
            (-1200, y_offset + 300),
            1000,
            metadata['histogram'],
        )
        histnode.name = f'[Histogram_{ch.identifier}]'

        contrast_limits = nodes.new(type="ShaderNodeValToRGB")
        contrast_limits.location = (-1200, y_offset + 40)
        contrast_limits.width = 1000
        contrast_limits.name = f'[contrast_limits_{ch.identifier}]'
        contrast_limits.label = "Color Contrast Limits"
        contrast_limits.color_ramp.elements[0].position = metadata['threshold']
        contrast_limits.color_ramp.elements[0].color = (1, 1, 1, 0)
        contrast_limits.color_ramp.elements[1].position = 1
        contrast_limits.color_ramp.elements[1].color = (1, 1, 1, 1)
        contrast_limits.outputs[0].hide = True

        color_lut = nodes.new(type="ShaderNodeValToRGB")
        color_lut.location = (-120, y_offset + 40)
        color_lut.width = 300
        color_lut.name = f"[color_lut_{ch.identifier}]"
        color_lut.show_options = True
        color_lut.outputs[1].hide = True

        principled = nodes.new("ShaderNodeBsdfPrincipled")
        principled.name = f"[{ch.identifier}] principled"
        principled.location = (320, y_offset + 190)
        principled.inputs.get('Alpha').default_value = 1.0
        if ch.viz.emission:
            principled.inputs[29].default_value = 0.5

        frame, add_shaders = self.add_ch_to_shader(mat, ch, principled.outputs["BSDF"])
        for node in (node_attr, histnode, contrast_limits, color_lut, principled):
            node.parent = frame

        links.new(node_attr.outputs.get('Fac'), contrast_limits.inputs.get("Fac"))
        links.new(contrast_limits.outputs[1], color_lut.inputs[0])
        links.new(color_lut.outputs[0], principled.inputs.get('Base Color'))
        links.new(color_lut.outputs[0], principled.inputs[28])
        self.set_slice_color_ramp(ch, color_lut)
        return frame, add_shaders

    def add_ch_to_shader(self, mat, ch, shader_socket):
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        add_shaders = nodes["Add Shaders"]

        frame = nodes.new("NodeFrame")
        frame.name = f"[frame_{ch.identifier}]"
        frame.label = ch.name
        master_frame = nodes.get(self.projection_frame_name)
        if master_frame is not None:
            frame.parent = master_frame
        frame.use_custom_color = True
        frame.color = (0.0, 0.0, 0.0)
        frame.label_size = 50
        frame.shrink = True

        links.new(shader_socket, add_shaders.inputs[min(ch.data.ix, self.shader_count - 1)])
        return frame, add_shaders

    def update_material(self, mat, ch, source_type):
        if source_type is None:
            return
        metadata = ch.files_for(source_type).metadata
        nodes = mat.node_tree.nodes
        color_lut = nodes.get(f'[color_lut_{ch.identifier}]')
        if color_lut is not None:
            self.set_slice_color_ramp(ch, color_lut)
        histnode = nodes.get(f'[Histogram_{ch.identifier}]')
        if metadata and histnode is not None:
            new_histnode = self.draw_histogram(
                nodes,
                histnode.location,
                histnode.width,
                metadata['histogram'],
            )
            new_histnode.name = histnode.name
            new_histnode.label = histnode.label
            new_histnode.parent = histnode.parent
            nodes.remove(histnode)
        contrast_limits = nodes.get(f'[contrast_limits_{ch.identifier}]')
        if contrast_limits is not None and metadata:
            contrast_limits.color_ramp.elements[0].position = metadata['threshold']
        principled = nodes.get(f"[{ch.identifier}] principled")
        if principled is not None:
            principled.inputs[29].default_value = 0.5 if ch.viz.emission else 0.0
            principled.inputs.get('Alpha').default_value = 1.0

    def update_channel_names(self, ch):
        name = ch.name.replace("-", "_")
        attr = self.object.data.materials[0].node_tree.nodes.get(f"[channel_load_{ch.identifier}]")
        if attr is not None:
            attr.attribute_name = name
            attr.label = name
        sampler = self.sample_node(ch)
        if sampler is not None:
            sampler.inputs["Name"].default_value = name

    def sample_node(self, ch):
        for node in self.node_group.nodes:
            if node.get("channel_identifier") == ch.identifier:
                return node
        return None

    def set_slice_color_ramp(self, ch, color_lut):
        lut, linear = colormap_to_lut(ch.viz.cmap)
        if len(lut) == 1:
            set_color_ramp(color_lut, [(0, 0, 0, 1), lut[0]], True, "Colormap")
            return
        set_color_ramp_from_ch(ch, color_lut)

    def draw_histogram(self, nodes, loc, width, hist):
        hist = np.asarray(hist)
        histnode = nodes.new(type="ShaderNodeFloatCurve")
        histnode.location = loc
        histmap = histnode.mapping
        histnode.width = width
        histnode.label = 'Histogram (non-interactive)'
        histnode.inputs.get('Factor').hide = True
        histnode.inputs.get('Value').hide = True
        histnode.outputs.get('Value').hide = True

        histmax = np.max(hist)
        if histmax == 0:
            histmax = 1
        histnorm = hist / histmax
        if len(histnorm) > 150:
            histnorm = binned_statistic_sum(np.arange(len(histnorm)), histnorm, bins=150)
            histnorm /= np.max(histnorm)
        for ix, val in enumerate(histnorm):
            if ix == 0:
                histmap.curves[0].points[-1].location = ix/len(histnorm), val
                histmap.curves[0].points.new((ix + 0.9)/len(histnorm), val)
            if ix == len(histnorm) - 1:
                histmap.curves[0].points[-1].location = ix/len(histnorm), val
            else:
                histmap.curves[0].points.new(ix/len(histnorm), val)
                histmap.curves[0].points.new((ix + 0.9)/len(histnorm), val)
            histmap.curves[0].points[ix].handle_type = 'VECTOR'
        return histnode


def binned_statistic_sum(x, values, bins):
    x = np.asarray(x)
    values = np.asarray(values)
    bins = np.linspace(x.min(), x.max(), bins + 1)
    bin_indices = np.searchsorted(bins, x, side='right') - 1
    bin_indices = np.clip(bin_indices, 0, bins.size - 2)

    sums = np.zeros(bins.size - 1, dtype=values.dtype)
    np.add.at(sums, bin_indices, values)
    return sums


SLICE_PROJECTION_BOX_GROUP_NAME = "Slice Projection Box"


def slice_projection_box_node_group():
    node_group = bpy.data.node_groups.get(SLICE_PROJECTION_BOX_GROUP_NAME)
    if node_group is not None:
        return node_group

    node_group = bpy.data.node_groups.new(
        type='GeometryNodeTree',
        name=SLICE_PROJECTION_BOX_GROUP_NAME,
    )
    nodes = node_group.nodes
    links = node_group.links
    interface = node_group.interface

    spacing_socket = interface.new_socket(
        name="Sampling Pixel Spacing",
        in_out="INPUT",
        socket_type="NodeSocketFloat",
    )
    spacing_socket.default_value = 0.1
    spacing_socket.min_value = 1e-6
    if hasattr(spacing_socket, "subtype"):
        spacing_socket.subtype = 'DISTANCE'
    interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")

    group_input = nodes.new("NodeGroupInput")
    group_input.location = (-1000, 0)

    group_output = nodes.new("NodeGroupOutput")
    group_output.location = (500, 0)
    group_output.is_active_output = True

    self_object = nodes.new("GeometryNodeSelfObject")
    self_object.location = (-800, 260)

    self_info = nodes.new("GeometryNodeObjectInfo")
    self_info.location = (-600, 260)
    self_info.transform_space = 'RELATIVE'
    links.new(self_object.outputs["Self Object"], self_info.inputs["Object"])

    extent_unit = nodes.new("ShaderNodeVectorMath")
    extent_unit.name = "Extent in Unit Space"
    extent_unit.operation = 'MULTIPLY'
    extent_unit.location = (-400, 220)
    extent_unit.inputs[1].default_value = (2.0, 2.0, 2.0)
    links.new(self_info.outputs["Scale"], extent_unit.inputs[0])

    world_per_unit = nodes.new("ShaderNodeVectorMath")
    world_per_unit.name = "World Per Unit"
    world_per_unit.location = (-400, -40)
    world_per_unit.inputs[0].default_value = (1.0, 1.0, 1.0)

    axis_bundle = nodes.new("NodeCombineBundle")
    axis_bundle.name = "Axis Bundle"
    axis_bundle.location = (-400, -300)
    for name in AXIS_ITEM_NAMES:
        axis_bundle.bundle_items.new('BOOLEAN', name)
        axis_bundle.inputs[name].default_value = name != "frontface culling"

    scale_box = nodes.new("GeometryNodeGroup")
    scale_box.node_tree = scalebox_node_group()
    scale_box.name = "Scale Box"
    scale_box.location = (-80, 0)
    links.new(extent_unit.outputs[0], scale_box.inputs["Extent (unit)"])
    links.new(world_per_unit.outputs[0], scale_box.inputs["World per Unit"])
    links.new(group_input.outputs["Sampling Pixel Spacing"], scale_box.inputs["Tick Step (unit)"])
    links.new(axis_bundle.outputs["Bundle"], scale_box.inputs["Axis Bundle"])
    links.new(scale_box.outputs["Geometry"], group_output.inputs["Geometry"])

    return node_group
    
