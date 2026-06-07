import bpy
import numpy as np

from ..handle_blender_structs.min_keys import min_keys
from ..handle_blender_structs.node_handling import set_modifier_input
from ..min_nodes.geo_nodes import crosshatch_node_group, scale_node_group
from .base import MiNObject


AXIS_ITEM_NAMES = [
    "frontface culling",
    "xy bottom",
    "yz bottom",
    "zx bottom",
    "xy top",
    "yz top",
    "zx top",
]


class Axes(MiNObject):
    min_type = min_keys.AXES
    TICK_STEP_PREFIX = "Tick Step"

    def init_obj(self):
        super().init_obj()
        modifier = self.object.modifiers.new("Microscopy Nodes Axes", "NODES")
        modifier.node_group = bpy.data.node_groups.new("Microscopy Nodes Axes", "GeometryNodeTree")
        self.init_gn()
        return self.object

    def _tick_step_input_name(self, dataset_model=None):
        if dataset_model is None:
            return f"{self.TICK_STEP_PREFIX} (unit)"
        return f"{self.TICK_STEP_PREFIX} ({dataset_model.unit_label})"

    def _nice_tick_step(self, extent_unit, target_ticks=6, min_ticks=3):
        max_extent = float(np.max(extent_unit))
        if max_extent <= 0:
            return 1.0

        nice = np.outer(
            np.array([1.0, 2.0, 5.0]),
            np.array([10.0 ** k for k in range(-6, 12)])
        ).ravel()

        tick_counts = max_extent / nice
        valid = tick_counts >= min_ticks

        if not np.any(valid):
            return float(max_extent)

        candidates = nice[valid]
        counts = tick_counts[valid]
        return float(candidates[np.argmin(np.abs(counts - target_ticks))])

    def set_scene(self, scene_model):
        super().set_scene(scene_model)
        self.object.data.update()
        return

    def set_input_scale(self, dataset_input_scale):
        self.object[self.DATASET_INPUT_SCALE] = float(dataset_input_scale)
        self.object.data.update()
        return

    def set_holder(self, holder):
        scale_node = self.node_group.nodes["Scale Bars"]
        scale_node.node_tree = scale_node_group()
        scale_node.inputs["Holder"].default_value = holder
        self.object.data.update()
        return
        
    def set_settings(self, dataset_model):
        initialize = self.DATASET_INPUT_SCALE not in self.object
        tick_step_input_name = self._tick_step_input_name(dataset_model)
        for item in self.node_group.interface.items_tree:
            if item.item_type == 'SOCKET' and item.in_out == 'INPUT':
                if item.name.startswith(f"{self.TICK_STEP_PREFIX} ("):
                    item.name = tick_step_input_name
                    break
        _, _, dataset_extents = dataset_model.intermediate_bbox
        
        tick_step = self._nice_tick_step(dataset_extents)
        line_thickness = 0.25

        if initialize:
            self.object.location = dataset_extents / 2.0
            self.object.scale = np.maximum(dataset_extents, 1e-6)

        super().set_settings(dataset_model)
        self.set_input_scale(dataset_model.channels[0].data.unit)

        set_modifier_input(self.min_gn, tick_step_input_name, tick_step)
        set_modifier_input(self.min_gn, "Grid", True)
        set_modifier_input(self.min_gn, "Line thickness", line_thickness)
        for i in AXIS_ITEM_NAMES:
            set_modifier_input(self.min_gn, i, True)
        return

    def ensure_links_of_objects(self, dataset):
        return

    def init_gn(self):
        node_group = self.node_group
        nodes = node_group.nodes
        links = node_group.links
        interface = node_group.interface

        nodes.clear()

        inputnode = nodes.new("NodeGroupInput")
        inputnode.location = (-900, 0)

        outputnode = nodes.new("NodeGroupOutput")
        outputnode.location = (700, 0)

        interface.new_socket(name=f"{self.TICK_STEP_PREFIX} (unit)", in_out="INPUT", socket_type='NodeSocketFloat')
        interface.items_tree[-1].default_value = 1.0
        interface.items_tree[-1].min_value = 0.0
        interface.items_tree[-1].max_value = 3.4028234663852886e+38
        interface.items_tree[-1].attribute_domain = 'POINT'

        interface.new_socket(name="Grid", in_out="INPUT", socket_type='NodeSocketBool')
        interface.items_tree[-1].default_value = True
        interface.items_tree[-1].attribute_domain = 'POINT'

        interface.new_socket(name="Line thickness", in_out="INPUT", socket_type='NodeSocketFloat')
        interface.items_tree[-1].default_value = 0.1
        interface.items_tree[-1].min_value = 0.0
        interface.items_tree[-1].max_value = 3.4028234663852886e+38
        interface.items_tree[-1].attribute_domain = 'POINT'

        for name in AXIS_ITEM_NAMES:
            interface.new_socket(name=name, in_out="INPUT", socket_type='NodeSocketBool')
            interface.items_tree[-1].default_value = True
            interface.items_tree[-1].attribute_domain = 'POINT'

        interface.new_socket("Geometry", in_out="OUTPUT", socket_type='NodeSocketGeometry')
        interface.items_tree[-1].attribute_domain = 'POINT'

        combine_axes = nodes.new("NodeCombineBundle")
        combine_axes.name = "Axis Bundle"
        combine_axes.label = "Axis Bundle"
        combine_axes.location = (-650, -250)

        for name in AXIS_ITEM_NAMES:
            combine_axes.bundle_items.new('BOOLEAN', name)

        for name in AXIS_ITEM_NAMES:
            links.new(inputnode.outputs[name], combine_axes.inputs[name])

        crosshatch = nodes.new("GeometryNodeGroup")
        crosshatch.node_tree = crosshatch_node_group()
        crosshatch.location = (-650, 150)

        scale_node = nodes.new("GeometryNodeGroup")
        scale_node.node_tree = scale_node_group()
        scale_node.name = "Scale Bars"
        scale_node.label = "Scale Bars"
        scale_node.width = 260
        scale_node.location = (-50, 0)

        links.new(inputnode.outputs["Tick Step (unit)"], scale_node.inputs["Tick Step (unit)"])
        links.new(inputnode.outputs["Grid"], scale_node.inputs["Grid"])
        links.new(inputnode.outputs["Line thickness"], scale_node.inputs["Line thickness"])
        # links.new(crosshatch.outputs[0], scale_node.inputs["Tick Geometry"])
        links.new(combine_axes.outputs["Bundle"], scale_node.inputs["Axis Bundle"])

        axes_mat = self.init_material_axes()
        scale_node.inputs["Material"].default_value = axes_mat

        links.new(scale_node.outputs["Geometry"], outputnode.inputs["Geometry"])

    def init_material_axes(self):
        mat = bpy.data.materials.get("axes")
        if mat is None:
            mat = bpy.data.materials.new("axes")

        mat.blend_method = "BLEND"
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        for node in list(nodes):
            if node.name != "Material Output":
                nodes.remove(node)

        gridnormal = nodes.new("ShaderNodeAttribute")
        gridnormal.attribute_name = "orig_normal"
        gridnormal.location = (-800, -100)

        viewvec = nodes.new("ShaderNodeCameraData")
        viewvec.location = (-800, -300)

        vectransform = nodes.new("ShaderNodeVectorTransform")
        vectransform.location = (-600, -300)
        vectransform.vector_type = 'VECTOR'
        vectransform.convert_from = "CAMERA"
        vectransform.convert_to = "OBJECT"
        links.new(viewvec.outputs[0], vectransform.inputs[0])

        dot = nodes.new("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        dot.location = (-400, -200)
        links.new(gridnormal.outputs[1], dot.inputs[0])
        links.new(vectransform.outputs[0], dot.inputs[1])

        lesst = nodes.new("ShaderNodeMath")
        lesst.operation = "LESS_THAN"
        lesst.location = (-200, -200)
        links.new(dot.outputs["Value"], lesst.inputs[0])
        lesst.inputs[1].default_value = 0.0

        culling_bool = nodes.new("ShaderNodeAttribute")
        culling_bool.attribute_name = "frontface culling"
        culling_bool.location = (-200, -400)

        comb = nodes.new("ShaderNodeMath")
        comb.operation = "ADD"
        comb.location = (0, -300)
        links.new(lesst.outputs[0], comb.inputs[0])
        links.new(culling_bool.outputs[2], comb.inputs[1])

        and_op = nodes.new("ShaderNodeMath")
        and_op.operation = "COMPARE"
        and_op.location = (200, -300)
        links.new(comb.outputs[0], and_op.inputs[0])
        and_op.inputs[1].default_value = 2.0
        and_op.inputs[2].default_value = 0.01

        colorattr = nodes.new("ShaderNodeRGB")
        colorattr.location = (200, 150)

        trbsdf = nodes.new("ShaderNodeBsdfTransparent")
        trbsdf.location = (200, -100)

        mix = nodes.new("ShaderNodeMixShader")
        mix.location = (450, 0)
        links.new(colorattr.outputs[0], mix.inputs[1])
        mix.inputs[1].show_expanded = True
        links.new(trbsdf.outputs[0], mix.inputs[2])
        links.new(and_op.outputs[0], mix.inputs[0])

        out = nodes.get("Material Output")
        if out is None:
            out = nodes.new(type='ShaderNodeOutputMaterial')
            out.name = "Material Output"
        out.location = (650, 0)
        links.new(mix.outputs[0], out.inputs[0])

        return mat
