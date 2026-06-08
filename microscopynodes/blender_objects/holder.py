import bpy
import numpy as np
from databpy import create_object
from nodebpy import TreeBuilder, geometry as g
from nodebpy.builder import CustomGeometryGroup
from nodebpy.types import InputFloat, InputGeometry, InputInteger, InputVector

from .base import MiNObject
from ..handle_blender_structs.keyframe_handling import ensure_dataset_frame_animation
from ..handle_blender_structs.node_handling import set_modifier_input
from ..handle_blender_structs.min_keys import min_keys

HOLDER_NODE_GROUP_NAME = "Microscopy Nodes Holder"

HOLDER_BUNDLE_ITEMS = (
    ("INT", "Frame"),
    ("VECTOR", "Dataset BBox Min"),
    ("VECTOR", "Dataset BBox Max"),
    ("VECTOR", "Dataset BBox Extents"),
    ("FLOAT", "Dataset Input Scale"),
    ("FLOAT", "Scene World Scale Base"),
    ("FLOAT", "Scene Output Scale"),
    ("VECTOR", "Scene Import Offset"),
    ("VECTOR", "Scene Import Transform"),
)


class Holder(MiNObject):
    min_type = min_keys.HOLDER
    DATASET_INTERMEDIATE_BBOX = "_MiN_dataset_intermediate_bbox"
    DATASET_INPUT_SCALE = "_MiN_dataset_input_scale"
    SCENE_IMPORT_OFFSET = "_MiN_scene_import_offset"
    SCENE_IMPORT_TRANSFORM_ATTRIBUTE = "scene import transform"

    def init_obj(self):
        self.object = create_object(
            vertices=np.zeros((1, 3), dtype=float),
            name=self.min_type.name.lower(),
            collection=bpy.context.collection,
        )
        self.object.name = self.min_type.name.lower()
        self.ensure_gn()
        return self.object

    def set_data(self, dataset_model):
        self.object[self.DATASET_INTERMEDIATE_BBOX] = tuple(
            np.asarray(dataset_model.intermediate_bbox).ravel()
        )
        self.ensure_gn()
        mins, maxs, _ = self.dataset_intermediate_bbox
        set_modifier_input(self.gn_mod, "Dataset BBox Min", mins)
        set_modifier_input(self.gn_mod, "Dataset BBox Max", maxs)

    def set_settings(self, dataset_model):
        self.object[self.DATASET_INPUT_SCALE] = float(dataset_model.channels[0].data.unit)
        self.ensure_gn()
        ensure_dataset_frame_animation(self.object, dataset_model)
        set_modifier_input(self.gn_mod, "Dataset Input Scale", self.object[self.DATASET_INPUT_SCALE])
        self.object.hide_render = True
        self.object.display_type = 'WIRE'
        self.object.name = dataset_model.name
        self.object.rotation_euler = (0.0, 0.0, 0.0)

    def set_scene(self, scene_model):
        scene_world_scale = float(self.object[self.DATASET_INPUT_SCALE]) / float(scene_model.output_scale)
        dataset_size = self.dataset_extents * scene_world_scale
        scene_import_transform = np.asarray(scene_model.import_transform, dtype=float)

        self.object[self.SCENE_IMPORT_TRANSFORM_ATTRIBUTE] = tuple(scene_import_transform)
        self.store_named_attribute(
            np.asarray([scene_import_transform], dtype=float),
            self.SCENE_IMPORT_TRANSFORM_ATTRIBUTE,
        )
        previous_scene_import_offset = np.asarray(
            self.object.get(self.SCENE_IMPORT_OFFSET, (0.0, 0.0, 0.0)),
            dtype=float,
        )
        scene_import_offset = -scene_import_transform * dataset_size
        user_offset = np.asarray(self.object.location, dtype=float) - previous_scene_import_offset

        self.object.scale = (scene_world_scale,) * 3
        self.object.location = tuple(user_offset + scene_import_offset)

        self.object[self.SCENE_IMPORT_OFFSET] = tuple(scene_import_offset)
        set_modifier_input(self.gn_mod, "Scene World Scale Base", scene_world_scale)
        set_modifier_input(self.gn_mod, "Scene Output Scale", float(scene_model.output_scale))
        set_modifier_input(self.gn_mod, "Scene Import Transform", self.object[self.SCENE_IMPORT_TRANSFORM_ATTRIBUTE])

    @property
    def dataset_size(self):
        return self.dataset_extents * np.abs(self.object.matrix_world.to_scale())

    @property
    def dataset_intermediate_bbox(self):
        return np.asarray(self.object[self.DATASET_INTERMEDIATE_BBOX]).reshape(3, 3)

    @property
    def dataset_extents(self):
        return self.dataset_intermediate_bbox[2]

    def ensure_gn(self):
        for modifier in self.object.modifiers:
            if modifier.type == "NODES" and modifier.name == "[Microscopy Nodes holder]":
                return modifier
        modifier = self.object.modifiers.new("[Microscopy Nodes holder]", "NODES")
        modifier.node_group = holder_node_group()
        return modifier


class HolderBundle(CustomGeometryGroup):
    _name = HOLDER_NODE_GROUP_NAME

    def __init__(
        self,
        geometry: InputGeometry = None,
        frame: InputInteger = 0,
        dataset_bbox_min: InputVector = (0.0, 0.0, 0.0),
        dataset_bbox_max: InputVector = (0.0, 0.0, 0.0),
        dataset_input_scale: InputFloat = 1.0,
        scene_world_scale_base: InputFloat = 1.0,
        scene_output_scale: InputFloat = 1.0,
        scene_import_transform: InputVector = (0.0, 0.0, 0.0),
    ):
        super().__init__(
            Geometry=geometry,
            Frame=frame,
            **{
                "Dataset BBox Min": dataset_bbox_min,
                "Dataset BBox Max": dataset_bbox_max,
                "Dataset Input Scale": dataset_input_scale,
                "Scene World Scale Base": scene_world_scale_base,
                "Scene Output Scale": scene_output_scale,
                "Scene Import Transform": scene_import_transform,
            },
        )

    def _build_group(self, tree):
        _build_holder_bundle(tree)


def _build_holder_bundle(tree):
    tree.tree.show_modifier_manage_panel = True

    frame = tree.inputs.integer("Frame", 0)

    inputs = {
        "Geometry": tree.inputs.geometry("Geometry"),
        "Frame": frame,
        "Dataset BBox Min": tree.inputs.vector("Dataset BBox Min", hide_in_modifier=True),
        "Dataset BBox Max": tree.inputs.vector("Dataset BBox Max", hide_in_modifier=True),
        "Dataset Input Scale": tree.inputs.float("Dataset Input Scale", default_value=1.0, hide_in_modifier=True),
        "Scene World Scale Base": tree.inputs.float("Scene World Scale Base", default_value=1.0, hide_in_modifier=True),
        "Scene Output Scale": tree.inputs.float("Scene Output Scale", default_value=1.0, hide_in_modifier=True),
        "Scene Import Transform": tree.inputs.vector("Scene Import Transform", hide_in_modifier=True),
    }
    geometry = tree.outputs.geometry("Geometry")

    extents = g.VectorMath.subtract(
        vector=inputs["Dataset BBox Max"],
        vector_001=inputs["Dataset BBox Min"],
    ).o.vector
    dataset_size = g.VectorMath.scale(
        vector=extents,
        scale=inputs["Scene World Scale Base"],
    ).o.vector
    scene_import_offset = g.VectorMath.scale(
        vector=g.VectorMath.multiply(
            vector=inputs["Scene Import Transform"],
            vector_001=dataset_size,
        ).o.vector,
        scale=-1.0,
    ).o.vector

    bundle_values = {
        **inputs,
        "Dataset BBox Extents": extents,
        "Scene Import Offset": scene_import_offset,
    }

    combine = g.CombineBundle(define_signature=True)
    for socket_type, name in HOLDER_BUNDLE_ITEMS:
        combine.node.bundle_items.new(socket_type, name)
        tree.tree.links.new(bundle_values[name].socket, combine.node.inputs[name])

    g.SetGeometryBundle(
        geometry=inputs["Geometry"],
        bundle=combine.o.bundle,
    ).o.geometry >> geometry


def holder_node_group():
    node_group = bpy.data.node_groups.get(HOLDER_NODE_GROUP_NAME)
    if node_group is not None:
        return node_group

    with TreeBuilder.geometry(HOLDER_NODE_GROUP_NAME) as tree:
        _build_holder_bundle(tree)

    return tree.tree
