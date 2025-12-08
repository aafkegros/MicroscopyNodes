print('trying to import stuff in slice cube')
import bpy
from ..handle_blender_structs.props import min_keys
import numpy as np
from .base import *
print('imported stuff in slice cube')

class SliceCubeObject():
    min_type = min_keys.SLICECUBE
    
    def init_obj(self): 
        super().init_obj()
        slicecube = self.object
        slicecube.name = "slice cube"
        slicecube.scale = size_px * scale /2 

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

    def set_settings(self, dataset_model):
        slicecube = self.object
        slicecube.location =  np.array(slicecube.location)+ ( np.array(slicecube.location)*(scale_factor - 1))
        slicecube.scale = np.array(slicecube.scale)  * scale_factor
        slicecube.display_type = 'BOUNDS'
    
