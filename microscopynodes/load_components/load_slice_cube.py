import bpy
from .. import handle_blender_structs

def load_slice_cube(to_be_sliced, size_px, scale, slicecube=None):
    print('slice obj', slicecube)
    if slicecube is None:
        bpy.ops.mesh.primitive_cube_add(location=size_px*scale/2)
        slicecube = bpy.context.active_object
        slicecube.name = "slice cube"
        slicecube.scale = size_px * scale /2 

        bpy.ops.object.modifier_add(type='NODES')
        # slicecube.modifiers[-1].name = f"Slice cube empty modifier (for reloading)"
        slicecube.modifiers[-1].name = f"[Microscopy Nodes slicecube]"

        mat = bpy.data.materials.new(f'Slice Cube')
        mat.blend_method = "HASHED"
        mat.use_nodes = True
        mat.node_tree.nodes['Principled BSDF'].inputs.get("Alpha").default_value = 0
        slicecube.data.materials.append(mat)

    for obj in to_be_sliced:
        if obj is not None:
            for mat in obj.data.materials:
                if mat.node_tree.nodes.get("Slice Cube") is None:
                    handle_blender_structs.node_handling.insert_slicing(mat.node_tree, slicecube)

    
    return slicecube
