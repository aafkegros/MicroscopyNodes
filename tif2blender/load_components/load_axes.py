import bpy
import numpy as np
from pathlib import Path

from ..handle_blender_structs.collection_handling import *
from .. import t2b_nodes


def load_axes(size_px, init_scale, location, xy_size, z_size, input_file):
    axesobj = bpy.ops.mesh.primitive_cube_add(location=location)
    axesobj = bpy.context.view_layer.objects.active
    axesobj.data.name = 'axes'
    axesobj.name = 'axes'
    print(size_px, init_scale, location, xy_size, z_size, input_file)


    bpy.ops.object.modifier_add(type='NODES')
    node_group = bpy.data.node_groups.new('axes of ' + str(Path(input_file).stem) , 'GeometryNodeTree')  
    axesobj.modifiers[-1].node_group = node_group
    nodes = node_group.nodes
    links = node_group.links

    # node_group.interface.new_socket("Geometry",in_out="INPUT", socket_type='NodeSocketGeometry')

    axnode = nodes.new('FunctionNodeInputVector')
    axnode.name = "n pixels"
    axnode.label = "n pixels"
    axnode.location = (-400, 200)
    for axix in range(len(size_px)):
        axnode.vector[axix] = size_px[axix]
    
    initscale_node = nodes.new('FunctionNodeInputVector')
    initscale_node.name = 'init_scale'
    initscale_node.label = "Scale transform on load"
    initscale_node.location = (-400, 0)
    initscale_node.vector = np.array([1,1,z_size/xy_size])*init_scale

    scale_node = nodes.new('FunctionNodeInputVector')
    scale_node.name = 'input_scale'
    scale_node.label = 'scale (µm/px)'
    scale_node.vector[0] = xy_size
    scale_node.vector[1] = xy_size
    scale_node.vector[2] = z_size
    scale_node.location = (-400, -200)

    axnode_um = nodes.new('ShaderNodeVectorMath')
    axnode_um.operation = "MULTIPLY"
    axnode_um.name = "size (µm)"
    axnode_um.label = "size (µm)"
    axnode_um.location = (-50, 200)
    links.new(axnode.outputs[0], axnode_um.inputs[0])
    links.new(scale_node.outputs[0], axnode_um.inputs[1])
    
    axnode_bm = nodes.new('ShaderNodeVectorMath')
    axnode_bm.operation = "MULTIPLY"
    axnode_bm.name = "size (m)"
    axnode_bm.label = "size (m)"
    axnode_bm.location = (-50, 50)
    links.new(axnode.outputs[0], axnode_bm.inputs[0])
    links.new(initscale_node.outputs[0], axnode_bm.inputs[1])

    crosshatch = nodes.new('GeometryNodeGroup')
    crosshatch.node_tree = t2b_nodes.crosshatch_node_group()
    crosshatch.location = (-50, -140)

    axes_select = nodes.new('GeometryNodeGroup')
    axes_select.node_tree = t2b_nodes.axes_multiplexer_node_group()
    axes_select.label = "Subselect axes"
    axes_select.name = "Axis Selection"
    axes_select.width = 150
    axes_select.location = (-50, -320)

    scale_node = nodes.new('GeometryNodeGroup')
    scale_node.node_tree = t2b_nodes.scale_node_group()
    scale_node.width = 300
    scale_node.location = (200, 100)
    links.new(axnode_bm.outputs[0], scale_node.inputs.get('Size (m)'))
    links.new(axnode_um.outputs[0], scale_node.inputs.get('Size (µm)'))
    links.new(axes_select.outputs[0], scale_node.inputs.get('Axis Selection'))
    links.new(crosshatch.outputs[0], scale_node.inputs.get('Tick Geometry'))
    scale_node.inputs.get("Material").default_value = init_material_axes()
    
    node_group.interface.new_socket("Geometry",in_out="OUTPUT", socket_type='NodeSocketGeometry')
    outnode = nodes.new('NodeGroupOutput')
    outnode.location = (800,0)
    links.new(scale_node.outputs[0], outnode.inputs[0])

    # inputnode = nodes.new('NodeGroupInput')
    # join = nodes.new("GeometryNodeJoinGeometry")
    # links.new(scale_node.outputs[0], join.inputs[-1])
    # links.new(inputnode.outputs.get("Geometry"), join.inputs[-1])
    # links.new(join.outputs[0], outnode.inputs[0])

    # realize = nodes.new("GeometryNodeRealizeInstances")
    # links.new(join.outputs[0], realize.inputs[0])
    # links.new(realize.outputs[0], outnode.inputs[0])

    if axesobj.data.materials:
        axesobj.data.materials[0] = init_material_axes()
    else:
        axesobj.data.materials.append(init_material_axes())

    for dim in range(3):
        axesobj.lock_location[dim] = True
        axesobj.lock_rotation[dim] = True
        axesobj.lock_scale[dim] = True
    return axesobj

def init_material_axes():
    mat = bpy.data.materials.get("axes")
    if mat:
        return mat
    mat = bpy.data.materials.new('axes')
    mat.blend_method = "BLEND"
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    nodes.remove(nodes.get("Principled BSDF"))

    gridnormal =  nodes.new("ShaderNodeAttribute")
    gridnormal.attribute_name = 'orig_normal'
    gridnormal.location = (-800, -100)
    
    viewvec =  nodes.new("ShaderNodeCameraData")
    viewvec.location = (-800, -300)

    vectransform =  nodes.new("ShaderNodeVectorTransform")
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
    lesst.location =(-200, -200)
    links.new(dot.outputs.get("Value"), lesst.inputs[0])
    lesst.inputs[1].default_value = 0
    
    culling_bool =  nodes.new("ShaderNodeAttribute")
    culling_bool.attribute_name = 'frontface culling'
    culling_bool.location = (-200, -400)
    
    comb = nodes.new("ShaderNodeMath")
    comb.operation = "ADD"
    comb.location =(0, -300)
    links.new(lesst.outputs[0], comb.inputs[0])
    links.new(culling_bool.outputs[2], comb.inputs[1])

    and_op = nodes.new("ShaderNodeMath")
    and_op.operation = "COMPARE"
    and_op.location =(200, -300)
    links.new(comb.outputs[0], and_op.inputs[0])
    and_op.inputs[1].default_value = 2.0
    and_op.inputs[2].default_value = 0.01
    
    colorattr =  nodes.new("ShaderNodeAttribute")
    colorattr.attribute_name = 'color_scale_bar'
    colorattr.location = (200, 150)
    
    trbsdf = nodes.new("ShaderNodeBsdfTransparent")
    trbsdf.location = (200, -100)

    mix = nodes.new("ShaderNodeMixShader")
    mix.location = (450, 0)
    links.new(colorattr.outputs[0], mix.inputs[1])
    links.new(trbsdf.outputs[0], mix.inputs[2])
    links.new(and_op.outputs[0], mix.inputs[0])

    out = nodes.get("Material Output")
    out.location = (650, 0)
    links.new(mix.outputs[0], out.inputs[0])

    return mat
