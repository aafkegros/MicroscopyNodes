import bpy
import numpy as np

#initialize scalebox node group
def scalebox_node_group():
    scalebox= bpy.data.node_groups.new(type = 'GeometryNodeTree', name = "_scalebox")
    links = scalebox.links
    
    # -- get IO --
    #scalebox inputs
    #input Vector
    scalebox.inputs.new('NodeSocketVector', "size (m)")
    scalebox.inputs[-1].default_value = (13.0, 10.0, 6.0)
    scalebox.inputs[-1].min_value = 0.0
    scalebox.inputs[-1].max_value = 10000000.0
    scalebox.inputs[-1].attribute_domain = 'POINT'
    
    scalebox.inputs.new('NodeSocketVector', "size (µm)")
    scalebox.inputs[-1].default_value = (7.0, 5.0, 4.0)
    scalebox.inputs[-1].min_value = 0.0
    scalebox.inputs[-1].max_value = 10000000.0
    scalebox.inputs[-1].attribute_domain = 'POINT'

     #input µm per tick
    scalebox.inputs.new('NodeSocketFloat', "µm per tick")
    scalebox.inputs[-1].default_value = 1
    scalebox.inputs[-1].min_value = 0.0
    scalebox.inputs[-1].max_value = 3.4028234663852886e+38
    scalebox.inputs[-1].attribute_domain = 'POINT'
    
     #node Group Input
    group_input = scalebox.nodes.new("NodeGroupInput")
    group_input.location = (-800,0)
    
    #output Geometry
    scalebox.outputs.new('NodeSocketGeometry', "Geometry")
    scalebox.outputs[0].attribute_domain = 'POINT'
    group_output = scalebox.nodes.new("NodeGroupOutput")
    group_output.location = (2700,0)
    
    join_geo = scalebox.nodes.new("GeometryNodeJoinGeometry")
    join_geo.location = (1830,0)

    ## -- process IO --

    loc_0 =  scalebox.nodes.new("ShaderNodeVectorMath")
    loc_0.operation = "MULTIPLY"
    loc_0.location = (-600, -100)
    loc_0.label = "location 0,0,0"
    links.new(group_input.outputs.get("size (m)"), loc_0.inputs[0])
    loc_0.inputs[1].default_value = (-0.5,-0.5,0)
    
    loc_max =  scalebox.nodes.new("ShaderNodeVectorMath")
    loc_max.operation = "MULTIPLY"
    loc_max.location = (-450, -100)
    loc_max.label = "location max val"
    links.new(group_input.outputs.get("size (m)"), loc_max.inputs[0])
    loc_max.inputs[1].default_value = (0.5,0.5,1)
    
    m_per_µm =  scalebox.nodes.new("ShaderNodeVectorMath")
    m_per_µm.operation = "DIVIDE"
    m_per_µm.location = (-600, -300)
    m_per_µm.label = "m per µm"
    links.new(group_input.outputs.get("size (m)"), m_per_µm.inputs[0])
    links.new(group_input.outputs.get("size (µm)"), m_per_µm.inputs[1])
    
    µm_ticks_float =  scalebox.nodes.new("ShaderNodeVectorMath")
    µm_ticks_float.operation = "DIVIDE"
    µm_ticks_float.location = (-600, 200)
    µm_ticks_float.label = "float-nr of ticks"
    links.new(group_input.outputs.get("size (µm)"), µm_ticks_float.inputs[0])
    links.new(group_input.outputs.get("µm per tick"), µm_ticks_float.inputs[1])

    n_ticks_int =  scalebox.nodes.new("ShaderNodeVectorMath")
    n_ticks_int.operation = "CEIL"
    n_ticks_int.location = (-450, 200)
    n_ticks_int.label = "nr of ticks"
    links.new(µm_ticks_float.outputs[0], n_ticks_int.inputs[0])
     
    ticks_offset =  scalebox.nodes.new("ShaderNodeVectorMath")
    ticks_offset.operation = "ADD"
    ticks_offset.location = (-300, 200)
    ticks_offset.label = "add 0th tick"
    links.new(n_ticks_int.outputs[0], ticks_offset.inputs[0])
    ticks_offset.inputs[1].default_value = (1,1,1)
       
    µm_overshoot =  scalebox.nodes.new("ShaderNodeVectorMath")
    µm_overshoot.operation = "MULTIPLY"
    µm_overshoot.location = (-450, 000)
    µm_overshoot.label = "µm full grid"
    links.new(n_ticks_int.outputs[0], µm_overshoot.inputs[0])
    links.new(group_input.outputs.get("µm per tick"), µm_overshoot.inputs[1])
   
    size_overshoot =  scalebox.nodes.new("ShaderNodeVectorMath")
    size_overshoot.operation = "MULTIPLY"
    size_overshoot.location = (-300, 0)
    size_overshoot.label = "overshoot size vec"
    links.new(µm_overshoot.outputs[0], size_overshoot.inputs[0])
    links.new(m_per_µm.outputs[0], size_overshoot.inputs[1])
    
    size_overshootXYZ =  scalebox.nodes.new("ShaderNodeSeparateXYZ")
    size_overshootXYZ.location = (-150, 0)
    size_overshootXYZ.label = "grid size"
    links.new(size_overshoot.outputs[0], size_overshootXYZ.inputs[0])
    
    n_ticksXYZ =  scalebox.nodes.new("ShaderNodeSeparateXYZ")
    n_ticksXYZ.location = (-150, 200)
    n_ticksXYZ.label = "n ticks"
    links.new(ticks_offset.outputs[0], n_ticksXYZ.inputs[0])
    
    
    # make principal box
    finals = []
    for sideix, side in enumerate(['bottom', 'top']):
        for axix, ax in enumerate(['xy','yz','zx']):
            grid = scalebox.nodes.new("GeometryNodeMeshGrid")
            grid.label = ax+"_"+side
            grid.name = ax+"_"+side+"_grid"
            
            for which, axis in enumerate("xyz"):
                if axis in ax:
                    links.new(size_overshootXYZ.outputs[which], grid.inputs[ax.find(axis)])
                    links.new(n_ticksXYZ.outputs[which], grid.inputs[ax.find(axis)+2])
                    
            
            transform = scalebox.nodes.new("GeometryNodeTransform")
            links.new(grid.outputs[0], transform.inputs[0])


            if side == "top":
                pretransform = scalebox.nodes.new("ShaderNodeVectorMath")
                pretransform.operation = 'MULTIPLY'
                links.new(group_input.outputs.get("size (m)"), pretransform.inputs[0])
                links.new(pretransform.outputs[0], transform.inputs.get("Translation"))
                
                # shift tops to the correct plane (out-of-axis) and calc rotation
                shift = np.array([float(axis not in ax) for axis in "xyz"]) 
                pretransform.inputs[1].default_value = tuple(shift)
            else:
                pretransform = scalebox.nodes.new("GeometryNodeFlipFaces")
                links.new(grid.outputs[0], pretransform.inputs[0])
                links.new(pretransform.outputs[0], transform.inputs[0])
            
            rot = [0,0,0]
            if ax == "yz":
                rot = [0.5,0,0.5]
            elif ax == 'zx':
                rot = [0,-0.5,-0.5]
            transform.inputs.get("Rotation").default_value = tuple(np.array(rot)*np.pi)

            
            # translocate 0,0 to be accurate for each
            bbox = scalebox.nodes.new("GeometryNodeBoundBox")
            links.new(transform.outputs[0],bbox.inputs[0])
            
            top = scalebox.nodes.new("ShaderNodeVectorMath")
            top.operation = "MULTIPLY"
            links.new(bbox.outputs[1], top.inputs[0])
            top.inputs[1].default_value =(1,1,1)
            if side == 'top':
                top.inputs[1].default_value = tuple(np.array([float(axis in ax) for axis in "xyz"]))
            
            find_0 = scalebox.nodes.new("ShaderNodeVectorMath")
            find_0.operation = "SUBTRACT"
            links.new(loc_0.outputs[0], find_0.inputs[0])
            links.new(top.outputs[0], find_0.inputs[1])
            
            set_pos = scalebox.nodes.new("GeometryNodeSetPosition")
            links.new(transform.outputs[0], set_pos.inputs[0])
            links.new(find_0.outputs[0], set_pos.inputs[-1])

            
            for locix,node in enumerate([grid,pretransform, transform,bbox,top, find_0, set_pos]):
                nodeix = (sideix*3)+axix
                node.location = (200*locix + 200, 300*2.5 + nodeix * -300)
            finals.append(set_pos)
    for final in reversed(finals):            
        links.new(final.outputs[0], join_geo.inputs[0])
    
    # set final nodes to right position
    
    pos =  scalebox.nodes.new("GeometryNodeInputPosition")
    pos.location = (2100, -100)
    
    min_axis =  scalebox.nodes.new("ShaderNodeVectorMath")
    min_axis.operation = "MINIMUM"
    min_axis.location = (2250, -100)
    links.new(pos.outputs[0], min_axis.inputs[0])
    links.new(loc_max.outputs[0], min_axis.inputs[1])
    
    
    clip_axis =  scalebox.nodes.new("GeometryNodeSetPosition")
    clip_axis.location = (2500, 0)
    clip_axis.label = "clip final axis"
    links.new(join_geo.outputs[0], clip_axis.inputs[0])
    links.new(min_axis.outputs[0], clip_axis.inputs[2])

    links.new(clip_axis.outputs[0],group_output.inputs[0])

    return scalebox

# scalebox = scalebox_node_group()
import bpy

def grid_verts_node_group():
    grid_verts= bpy.data.node_groups.new(type = 'GeometryNodeTree', name = "grid_verts")
    links = grid_verts.links
    
    # -- get IO --
    #grid_verts inputs
    #input Vector
    grid_verts.inputs.new('NodeSocketVector', "size (m)")
    grid_verts.inputs[-1].default_value = (13.0, 10.0, 6.0)
    grid_verts.inputs[-1].min_value = 0.0
    grid_verts.inputs[-1].max_value = 10000000.0
    grid_verts.inputs[-1].attribute_domain = 'POINT'

    #node Group Input
    group_input = grid_verts.nodes.new("NodeGroupInput")
    group_input.location = (-800,0)
    
    pos = grid_verts.nodes.new("GeometryNodeInputPosition")
    pos.location = (-600, 130)
    
    posXYZ =  grid_verts.nodes.new("ShaderNodeSeparateXYZ")
    posXYZ.location = (-400, 130)
    posXYZ.label = "posXYZ"
    links.new(pos.outputs[0], posXYZ.inputs[0])
    
    compnodes = [[],[],[]]
    for ix, side in enumerate(['min', 'max']):
        loc =  grid_verts.nodes.new("ShaderNodeVectorMath")
        loc.operation = "MULTIPLY"
        loc.location = (-600, -200 * ix)
        loc.label = "location 0,0,0"
        links.new(group_input.outputs.get("size (m)"), loc.inputs[0])
        if side == 'min':
            loc.inputs[1].default_value = (-0.5,-0.5,0)
        else: 
            loc.inputs[1].default_value = (0.5,0.5,1)
        locXYZ =  grid_verts.nodes.new("ShaderNodeSeparateXYZ")
        locXYZ.location = (-400, -130*ix)
        locXYZ.label = side + "XYZ"
        links.new(loc.outputs[0], locXYZ.inputs[0])
        
        
        for axix, ax in enumerate("XYZ"):
            # element wise compare
            compare = grid_verts.nodes.new("FunctionNodeCompare")
            compare.data_type = 'FLOAT'
            compare.operation = 'EQUAL'
            compare.mode = 'ELEMENT'
            compare.label = "value on " + side + " in " + ax
            compare.location = (-200, ((ix*3)+axix) * -200 +300)
            links.new(posXYZ.outputs[axix], compare.inputs[0])
            links.new(locXYZ.outputs[axix], compare.inputs[1])
            compnodes[axix].append(compare)
    
    ornodes = []
    for axix, ax in enumerate("XYZ"):
        ornode = grid_verts.nodes.new("FunctionNodeBooleanMath")
        ornode.operation = 'OR'
        for nix,compnode in enumerate(compnodes[axix]):
            links.new(compnode.outputs[0], ornode.inputs[nix])
        ornode.location = (0, (axix) * -200 +100)
        ornode.label = "vert in min or max of " + ax
        ornodes.append(ornode)
    
    andnodes = []
    for i in range(3):
        andnode = grid_verts.nodes.new("FunctionNodeBooleanMath")
        andnode.operation = 'AND'
        links.new(ornodes[i].outputs[0], andnode.inputs[0])
        links.new(ornodes[i-1].outputs[0], andnode.inputs[1])
        andnode.location = (200, i * -200 +100)
        andnodes.append(andnode)
    
    ornodes2 = []
    ornode = grid_verts.nodes.new("FunctionNodeBooleanMath")
    ornode.operation = 'OR'
    links.new(andnodes[0].outputs[0], ornode.inputs[0])
    links.new(andnodes[1].outputs[0], ornode.inputs[1])
    ornode.location = (400, 100)
    ornodes2.append(ornode)
    
    ornode = grid_verts.nodes.new("FunctionNodeBooleanMath")
    ornode.operation = 'OR'
    links.new(andnodes[1].outputs[0], ornode.inputs[0])
    links.new(andnodes[2].outputs[0], ornode.inputs[1])
    ornode.location = (400, -100)
    ornodes2.append(ornode)

    nornode = grid_verts.nodes.new("FunctionNodeBooleanMath")
    nornode.operation = 'NOR'
    links.new(ornodes2[0].outputs[0], nornode.inputs[0])
    links.new(ornodes2[1].outputs[0], nornode.inputs[1])
    nornode.location = (600, 100)

    #output Geometry
    grid_verts.outputs.new('NodeSocketBool', "Boolean")
    grid_verts.outputs[0].attribute_domain = 'POINT'
    group_output = grid_verts.nodes.new("NodeGroupOutput")
    group_output.location = (800,100)
    links.new(nornode.outputs[0], group_output.inputs[0])
    return grid_verts
import bpy
import numpy as np

#initialize scale node group
def scale_node_group():
    scale= bpy.data.node_groups.new(type = 'GeometryNodeTree', name = "Overgroup_scale")
    links = scale.links
    
    # -- get Input --
    scale.inputs.new('NodeSocketVector', "size (m)")
    scale.inputs[-1].default_value = (13.0, 10.0, 6.0)
    scale.inputs[-1].min_value = 0.0
    scale.inputs[-1].max_value = 10000000.0
    scale.inputs[-1].attribute_domain = 'POINT'
    
    scale.inputs.new('NodeSocketVector', "size (µm)")
    scale.inputs[-1].default_value = (7.0, 5.0, 4.0)
    scale.inputs[-1].min_value = 0.0
    scale.inputs[-1].max_value = 10000000.0
    scale.inputs[-1].attribute_domain = 'POINT'

    scale.inputs.new('NodeSocketFloat', "µm per tick")
    scale.inputs[-1].default_value = 3
    scale.inputs[-1].min_value = 0.0
    scale.inputs[-1].max_value = 3.4028234663852886e+38
    scale.inputs[-1].attribute_domain = 'POINT'
    
    scale.inputs.new('NodeSocketBool', "grid")
    scale.inputs[-1].default_value = True
    scale.inputs[-1].attribute_domain = 'POINT'
    
    scale.inputs.new('NodeSocketFloat', "line thickness")
    scale.inputs[-1].default_value = 3.0
    scale.inputs[-1].min_value = 0.0
    scale.inputs[-1].max_value = 3.4028234663852886e+38
    scale.inputs[-1].attribute_domain = 'POINT'
    
    scale.inputs.new('NodeSocketFloat', "tick size")
    scale.inputs[-1].default_value = 15.0
    scale.inputs[-1].min_value = 0.0
    scale.inputs[-1].max_value = 3.4028234663852886e+38
    scale.inputs[-1].attribute_domain = 'POINT'
    
    scale.inputs.new('NodeSocketBool', "frontface culling")
    scale.inputs[-1].default_value = True
    scale.inputs[-1].attribute_domain = 'POINT'
    
    scale.inputs.new('NodeSocketColor', "Color")
    scale.inputs[-1].default_value = (1,1,1, 1)
    
    group_input = scale.nodes.new("NodeGroupInput")
    group_input.location = (-1000,0)

    # -- make scale box and read out/store normals
    scalebox = scale.nodes.new('GeometryNodeGroup')
    scalebox.node_tree = bpy.data.node_groups["scalebox"]
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
    grid_verts.node_tree = bpy.data.node_groups["grid_verts.021"]
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
    thickness.location = (-500, -300)
    thickness.label = "line thickness scaled down"
    links.new(group_input.outputs.get("line thickness"), thickness.inputs[0])
    thickness.inputs[1].default_value = 100
    
    # -- make ticks -- 
    tick_size =  scale.nodes.new("ShaderNodeMath")
    tick_size.operation = "MULTIPLY"
    tick_size.location = (-500, -500)
    tick_size.label = "tick length per direction"
    links.new(thickness.outputs[0], tick_size.inputs[0])
    links.new(group_input.outputs.get('tick size'), tick_size.inputs[1])
    
    cubes = []
    for axix, ax in enumerate("XYZ"):
        comb = scale.nodes.new("ShaderNodeCombineXYZ")
        comb.location = (-200, -300 - 200*axix)
        for i in range(3):
            links.new(thickness.outputs[0], comb.inputs[i])
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
    iop = scale.nodes.new("GeometryNodeInstanceOnPoints")
    iop.location = (500, 100)
    links.new(cap_normal.outputs[0], iop.inputs[0])
    links.new(join_tick.outputs[0], iop.inputs[2])
    
    delgridticks =  scale.nodes.new("GeometryNodeDeleteGeometry")
    delgridticks.domain = 'INSTANCE'
    delgridticks.location = (700, 100)
    links.new(iop.outputs[0], delgridticks.inputs[0])
    links.new(grid_verts.outputs[0], delgridticks.inputs.get("Selection"))
    
    realize =  scale.nodes.new("GeometryNodeRealizeInstances")
    realize.location = (900, 100)
    links.new(delgridticks.outputs[0], realize.inputs[0])

    store_normaltick =  scale.nodes.new("GeometryNodeStoreNamedAttribute")
    store_normaltick.inputs.get("Name").default_value = "orig_normal"
    store_normaltick.data_type = 'FLOAT_VECTOR'
    store_normaltick.domain = 'POINT'
    store_normaltick.location = (1100, 100)
    links.new(realize.outputs[0], store_normaltick.inputs[0])
    links.new(cap_normal.outputs[1], store_normaltick.inputs.get("Value"))
    
    
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
    links.new(store_normaltick.outputs[0], join.inputs[-1])
    
    culling =  scale.nodes.new("GeometryNodeStoreNamedAttribute")
    culling.label = "passthrough frontface culling to shader"
    culling.inputs.get("Name").default_value = "frontface culling"
    culling.data_type = 'BOOLEAN'
    culling.domain = 'POINT'
    culling.location = (1600, 10)
    links.new(join.outputs[0], culling.inputs[0])
    links.new(group_input.outputs.get('frontface culling'), culling.inputs[6])
     
    color =  scale.nodes.new("GeometryNodeStoreNamedAttribute")
    color.label = "passthrough color to shader"
    color.inputs.get("Name").default_value = "color"
    color.data_type = 'FLOAT_COLOR'
    color.domain = 'POINT'
    color.location = (1800, 0)
    links.new(culling.outputs[0], color.inputs[0])
    links.new(group_input.outputs.get('Color'), color.inputs[5])
    
    material = scale.nodes.new("GeometryNodeSetMaterial")
    material.location = (2000,0)
    links.new(color.outputs[0], material.inputs[0])
    
    scale.outputs.new('NodeSocketGeometry', "Geometry")
    scale.outputs[0].attribute_domain = 'POINT'
    group_output = scale.nodes.new("NodeGroupOutput")
    group_output.location = (2200,0)
    links.new(material.outputs[0], group_output.inputs[0])


    return scale

scale = scale_node_group()

