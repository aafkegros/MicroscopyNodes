import bpy
from ..handle_blender_structs.min_keys import min_keys
import numpy as np
from .base import MiNObject

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
        initialize = self.DATASET_INPUT_SCALE not in self.object
        _, _, dataset_extents = dataset_model.intermediate_bbox
        if initialize:
            self.object.location = dataset_extents / 2.0
            self.object.scale = np.maximum(dataset_extents / 2.0 + 1e-5, 1e-5)
        super().set_settings(dataset_model)
        self.object.display_type = 'BOUNDS'
    
