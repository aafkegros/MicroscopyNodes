import bpy
from ..handle_blender_structs.props import min_keys
import numpy as np
from .base import *

class SliceCubeObject(MiNObject):
    min_type = min_keys.SLICECUBE
    
    def init_obj(self): 
        super().init_obj()
        slicecube = self.object
        slicecube.name = "slice cube"

        bpy.ops.object.modifier_add(type='NODES')
        # slicecube.modifiers[-1].name = f"Slice cube empty modifier (for reloading)"
        slicecube.modifiers[-1].name = f"[Microscopy Nodes slicecube]"

        mat = bpy.data.materials.new(f'Slice Cube')
        mat.blend_method = "HASHED"
        mat.use_nodes = True
        if mat.node_tree.nodes.get("Principled BSDF") is None:
            mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
        if mat.node_tree.nodes.get("Material Output") is None:
            out = mat.node_tree.nodes.new(type="ShaderNodeOutputMaterial")
            out.location = (400,0)
            mat.node_tree.links.new(
                mat.node_tree.nodes['Principled BSDF'].outputs['BSDF'],
                mat.node_tree.nodes['Material Output'].inputs['Surface']
            )
        mat.node_tree.nodes['Principled BSDF'].inputs.get("Alpha").default_value = 0
        slicecube.data.materials.append(mat)
        return slicecube

    def set_settings(self, dataset_model):
        slicecube = self.object
        mins_world, _, extent_world = dataset_model.final_bbox
        center_world = mins_world + extent_world / 2.0

        slicecube.location = center_world
        slicecube.scale = np.maximum(extent_world / 2.0, 1e-6)
        slicecube.display_type = 'BOUNDS'
    
