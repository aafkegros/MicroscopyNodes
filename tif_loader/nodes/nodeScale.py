import bpy
import numpy as np
from .nodeScaleBox import scalebox_node_group
from .nodeGridVerts import grid_verts_node_group
#initialize scale node group
def scale_node_group():
    node_group = bpy.data.node_groups.get("Scale bars")
    if node_group:
        return node_group
    scale= bpy.data.node_groups.new(type = 'GeometryNodeTree', name = "Scale bars")
    links = scale.links
    
    # -- get Input --
    scale.inputs.new('NodeSocketVector', "size (µm)")
    scale.inputs[-1].default_value = (7.0, 5.0, 4.0)
    scale.inputs[-1].min_value = 0.0
    scale.inputs[-1].max_value = 10000000.0
    scale.inputs[-1].attribute_domain = 'POINT'

    scale.inputs.new('NodeSocketVector', "size (m)")
    scale.inputs[-1].default_value = (13.0, 10.0, 6.0)
    scale.inputs[-1].min_value = 0.0
    scale.inputs[-1].max_value = 10000000.0
    scale.inputs[-1].attribute_domain = 'POINT'

    scale.inputs.new('NodeSocketFloat', "µm per tick")
    scale.inputs[-1].default_value = 10
    scale.inputs[-1].min_value = 0.0
    scale.inputs[-1].max_value = 3.4028234663852886e+38
    scale.inputs[-1].attribute_domain = 'POINT'
    
    scale.inputs.new('NodeSocketBool', "grid")
    scale.inputs[-1].default_value = True
    scale.inputs[-1].attribute_domain = 'POINT'
    
    scale.inputs.new('NodeSocketFloat', "line thickness")
    scale.inputs[-1].default_value = 0.2
    scale.inputs[-1].min_value = 0.0
    scale.inputs[-1].max_value = 3.4028234663852886e+38
    scale.inputs[-1].attribute_domain = 'POINT'
    
    scale.inputs.new('NodeSocketFloat', "tick size")
    scale.inputs[-1].default_value = 15.0
    scale.inputs[-1].min_value = 0.0
    scale.inputs[-1].max_value = 3.4028234663852886e+38
    scale.inputs[-1].attribute_domain = 'POINT'
    
    scale.inputs.new('NodeSocketFloat', "tick thickness")
    scale.inputs[-1].default_value = 3.0
    scale.inputs[-1].min_value = 0.0
    scale.inputs[-1].max_value = 3.4028234663852886e+38
    scale.inputs[-1].attribute_domain = 'POINT'

    scale.inputs.new('NodeSocketBool', "frontface culling (only render away from view)")
    scale.inputs[-1].default_value = True
    scale.inputs[-1].attribute_domain = 'POINT'
    
    scale.inputs.new('NodeSocketColor', "Color")
    scale.inputs[-1].default_value = (1,1,1, 1)
    
    scale.inputs.new('NodeSocketMaterial', "Material")

    
    group_input = scale.nodes.new("NodeGroupInput")
    group_input.location = (-1000,0)

    # -- make scale box and read out/store normals
    scalebox = scale.nodes.new('GeometryNodeGroup')
    scalebox.node_tree = scalebox_node_group()
    scalebox.location = (-500, 500)
    links.new(group_input.outputs.get("size (m)"), scalebox.inputs.get("size (m)"))
    links.new(group_input.outputs.get("size (µm)"), scalebox.inputs.get("size (µm)"))
    links.new(group_input.outputs.get("µm per tick"), scalebox.inputs.get("µm per tick"))
    
    normal = scale.nodes.new("GeometryNodeInputNormal")
    normal.location = (-320, 450)
    
    store_normal =  scale.nodes.new("GeometryNodeStoreNamedAttribute")
    store_normal.inputs.get("Name").default_value = "orig_normal"
    store_normal.data_type = 'FLOAT_VECTOR'
    store_normal.domain = 'EDGE'
    store_normal.location = (-150, 700)
    links.new(scalebox.outputs[0], store_normal.inputs[0])
    links.new(normal.outputs[0], store_normal.inputs.get("Value"))

    cap_normal =  scale.nodes.new("GeometryNodeCaptureAttribute")
    cap_normal.data_type = 'FLOAT_VECTOR'
    cap_normal.domain = 'POINT'
    cap_normal.location = (-150, 400)
    links.new(scalebox.outputs[0], cap_normal.inputs[0])
    links.new(normal.outputs[0], cap_normal.inputs.get("Value"))
    
    # -- read out grid positions --
    grid_verts = scale.nodes.new('GeometryNodeGroup')
    grid_verts.node_tree = grid_verts_node_group()
    grid_verts.location = (-500, 100)
    links.new(group_input.outputs.get("size (m)"), grid_verts.inputs.get("size (m)"))
    
    not_grid = scale.nodes.new("FunctionNodeBooleanMath")
    not_grid.operation = 'NOT'
    links.new(group_input.outputs.get("grid"), not_grid.inputs[0])
    not_grid.location = (-500, -100)
    
    and_grid = scale.nodes.new("FunctionNodeBooleanMath")
    and_grid.operation = 'AND'
    links.new(grid_verts.outputs[0], and_grid.inputs[0])
    links.new(not_grid.outputs[0], and_grid.inputs[1])
    and_grid.location = (-320, 0)
    
    # -- scale down thickness --
    thickness =  scale.nodes.new("ShaderNodeMath")
    thickness.operation = "DIVIDE"
    thickness.location = (-500, -200)
    thickness.label = "line thickness scaled down"
    links.new(group_input.outputs.get("line thickness"), thickness.inputs[0])
    thickness.inputs[1].default_value = 100
    
    # -- make ticks -- 
    tick_size =  scale.nodes.new("ShaderNodeMath")
    tick_size.operation = "DIVIDE"
    tick_size.location = (-500, -500)
    tick_size.label = "tick length per direction"
    links.new(group_input.outputs.get("tick size"),  tick_size.inputs[0])
    tick_size.inputs[1].default_value = 100

    tick_thickness =  scale.nodes.new("ShaderNodeMath")
    tick_thickness.operation = "DIVIDE"
    tick_thickness.location = (-500, -700)
    tick_thickness.label = "tick thickness scaled down"
    links.new(group_input.outputs.get("tick thickness"), tick_thickness.inputs[0])
    tick_thickness.inputs[1].default_value = 100
    
    cubes = []
    for axix, ax in enumerate("XYZ"):
        comb = scale.nodes.new("ShaderNodeCombineXYZ")
        comb.location = (-200, -300 - 200*axix)
        for i in range(3):
            links.new(tick_thickness.outputs[0], comb.inputs[i])
        links.new(tick_size.outputs[0], comb.inputs[axix])
        cube = scale.nodes.new("GeometryNodeMeshCube")
        cube.location = (0, -300 - 200*axix)
        links.new(comb.outputs[0], cube.inputs[0])
        cubes.append(cube)
        
    join_tick = scale.nodes.new("GeometryNodeJoinGeometry")
    join_tick.location = (300, -500)
    for cube in reversed(cubes):
        links.new(cube.outputs[0], join_tick.inputs[0])
        
    # -- instantiate ticks -- 
    merge = scale.nodes.new("GeometryNodeMergeByDistance")
    links.new(cap_normal.outputs[0], merge.inputs[0])
    merge.location = (250, 100)

    ax_grid = scale.nodes.new("FunctionNodeBooleanMath")
    ax_grid.operation = 'NOT'
    links.new(grid_verts.outputs[0], ax_grid.inputs[0])
    ax_grid.location = (-250, -100)

    iop = scale.nodes.new("GeometryNodeInstanceOnPoints")
    iop.location = (500, 100)
    links.new(merge.outputs[0], iop.inputs[0])
    links.new(ax_grid.outputs[0], iop.inputs[1])
    links.new(join_tick.outputs[0], iop.inputs[2])
    
    store_normaltick =  scale.nodes.new("GeometryNodeStoreNamedAttribute")
    store_normaltick.inputs.get("Name").default_value = "orig_normal"
    store_normaltick.data_type = 'FLOAT_VECTOR'
    store_normaltick.domain = 'INSTANCE'
    store_normaltick.location = (750, 100)
    links.new(iop.outputs[0], store_normaltick.inputs[0])
    links.new(cap_normal.outputs[1], store_normaltick.inputs.get("Value"))
    
    realize =  scale.nodes.new("GeometryNodeRealizeInstances")
    realize.location = (900, 100)
    links.new(store_normaltick.outputs[0], realize.inputs[0])
    
    # -- make edges --
    delgrid =  scale.nodes.new("GeometryNodeDeleteGeometry")
    delgrid.mode = 'ALL'
    delgrid.domain = 'POINT'
    delgrid.location = (400, 600)
    links.new(store_normal.outputs[0], delgrid.inputs[0])
    links.new(and_grid.outputs[0], delgrid.inputs.get("Selection"))
    
    m2c =  scale.nodes.new("GeometryNodeMeshToCurve")
    m2c.location = (600, 600)
    links.new(delgrid.outputs[0], m2c.inputs[0])
    
    profile = scale.nodes.new("GeometryNodeCurvePrimitiveQuadrilateral")
    profile.location = (600, 400)
    profile.mode = "RECTANGLE"
    links.new(thickness.outputs[0], profile.inputs[0])
    links.new(thickness.outputs[0], profile.inputs[1])
    
    c2m =  scale.nodes.new("GeometryNodeCurveToMesh")
    c2m.location = (800, 500)
    links.new(m2c.outputs[0], c2m.inputs[0])
    links.new(profile.outputs[0], c2m.inputs[1])

    
    # -- output and passthrough values -- 
    join =  scale.nodes.new("GeometryNodeJoinGeometry")
    join.location = (1400, 0)
    links.new(c2m.outputs[0], join.inputs[0])
    links.new(realize.outputs[0], join.inputs[-1])
    
    culling =  scale.nodes.new("GeometryNodeStoreNamedAttribute")
    culling.label = "passthrough frontface culling to shader"
    culling.inputs.get("Name").default_value = "frontface culling"
    culling.data_type = 'BOOLEAN'
    culling.domain = 'POINT'
    culling.location = (1600, 10)
    links.new(join.outputs[0], culling.inputs[0])
    links.new(group_input.outputs.get('frontface culling (only render away from view)'), culling.inputs[6])
    
    color =  scale.nodes.new("GeometryNodeStoreNamedAttribute")
    color.label = "passthrough color to shader"
    color.inputs.get("Name").default_value = "color_scale_bar"
    color.data_type = 'FLOAT_COLOR'
    color.domain = 'POINT'
    color.location = (1800, 0)
    links.new(culling.outputs[0], color.inputs[0])
    links.new(group_input.outputs.get('Color'), color.inputs[5])
    
    material = scale.nodes.new("GeometryNodeSetMaterial")
    material.location = (2000,0)
    links.new(color.outputs[0], material.inputs[0])
    links.new(group_input.outputs.get('Material'), material.inputs[2])
    
    scale.outputs.new('NodeSocketGeometry', "Geometry")
    scale.outputs[0].attribute_domain = 'POINT'
    group_output = scale.nodes.new("NodeGroupOutput")
    group_output.location = (2200,0)
    links.new(material.outputs[0], group_output.inputs[0])


    return scale


