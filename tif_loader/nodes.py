import bpy
import numpy as np

#initialize gridbox node group
def gridbox_node_group():
    gridbox= bpy.data.node_groups.new(type = 'GeometryNodeTree', name = "gridbox.002")
    links = gridbox.links
    
    #gridbox inputs
    #input Vector
    gridbox.inputs.new('NodeSocketVector', "size (m)")
    gridbox.inputs[-1].default_value = (10.0, 10.0, 10.0)
    gridbox.inputs[-1].min_value = 0.0
    gridbox.inputs[-1].max_value = 10000000.0
    gridbox.inputs[-1].attribute_domain = 'POINT'
    
    gridbox.inputs.new('NodeSocketVector', "size (µm)")
    gridbox.inputs[-1].default_value = (7.0, 7.0, 7.0)
    gridbox.inputs[-1].min_value = 0.0
    gridbox.inputs[-1].max_value = 10000000.0
    gridbox.inputs[-1].attribute_domain = 'POINT'

    
    #input m per µm
    gridbox.inputs.new('NodeSocketFloat', "m per µm")
    gridbox.inputs[-1].default_value = 1.0
    gridbox.inputs[-1].min_value = 0.0
    gridbox.inputs[-1].max_value = 3.4028234663852886e+38
    gridbox.inputs[-1].attribute_domain = 'POINT'
    
     #input µm per tick
    gridbox.inputs.new('NodeSocketFloat', "µm per tick")
    gridbox.inputs[-1].default_value = 1.0
    gridbox.inputs[-1].min_value = 0.0
    gridbox.inputs[-1].max_value = 3.4028234663852886e+38
    gridbox.inputs[-1].attribute_domain = 'POINT'
    
     #node Group Input
    group_input = gridbox.nodes.new("NodeGroupInput")
    group_input.location = (-400,0)
    
    #output Geometry
    gridbox.outputs.new('NodeSocketGeometry', "Geometry")
    gridbox.outputs[0].attribute_domain = 'POINT'
    group_output = gridbox.nodes.new("NodeGroupOutput")
    group_output.location = (1200,0)
    
    join_geo = gridbox.nodes.new("GeometryNodeJoinGeometry")
    join_geo.location = (1030,0)

    transforms = []
    for sideix, side in enumerate(['bottom', 'top']):
        for axix, ax in enumerate(['xy','yz','xz']):
            grid = gridbox.nodes.new("GeometryNodeMeshGrid")
            grid.label = ax+"_"+side
            grid.name = ax+"_"+side+"_grid"
            
            transform = gridbox.nodes.new("GeometryNodeTransform")
            links.new(grid.outputs[0], transform.inputs[0])
            
            
            translocate_box = gridbox.nodes.new("ShaderNodeVectorMath")
            translocate_box.operation = 'MULTIPLY'
            links.new(group_input.outputs.get("size (m)"), translocate_box.inputs[0])
            links.new(translocate_box.outputs[0], transform.inputs.get("Translation"))
            
            shift = np.array([float(axis not in ax) for axis in "xyz"]) / 2
            if side == 'bottom':
                shift *= -1
            shift += np.array([0, 0, 0.5])
            translocate_box.inputs[1].default_value = tuple(shift)
            
            if np.array_equal(shift,np.array([0,0,0])):
                shift = np.array([0,1,0])
            rot = shift * np.pi
            transform.inputs.get("Rotation").default_value = tuple(rot)
            
            
            for locix,node in enumerate([grid,translocate_box, transform]):
                nodeix = (sideix*3)+axix
                node.location = (200*locix, 300*2.5 + nodeix * -300)
            transforms.append(transform)
    for transform in reversed(transforms):            
        links.new(transform.outputs[0], join_geo.inputs[0])
    links.new(join_geo.outputs[0],group_output.inputs[0])

    #initialize gridbox nodes
    #node Grid.002
#    grid_002 = gridbox.nodes.new("GeometryNodeMeshGrid")

#    #node Grid.003
#    grid_003 = gridbox.nodes.new("GeometryNodeMeshGrid")

#    #node Grid.004
#    grid_004 = gridbox.nodes.new("GeometryNodeMeshGrid")

#    #node Grid.005
#    grid_005 = gridbox.nodes.new("GeometryNodeMeshGrid")

#    #node Grid.001
#    grid_001 = gridbox.nodes.new("GeometryNodeMeshGrid")

#    #node Combine XYZ.004
#    combine_xyz_004 = gridbox.nodes.new("ShaderNodeCombineXYZ")
#    #Y
#    combine_xyz_004.inputs[1].default_value = 0.0

#    #node Vector Math.005
#    vector_math_005 = gridbox.nodes.new("ShaderNodeVectorMath")
#    vector_math_005.operation = 'MULTIPLY'
#    #Vector_001
#    vector_math_005.inputs[1].default_value = (-0.5, 0.0, 0.5)
#    #Vector_002
#    vector_math_005.inputs[2].default_value = (0.0, 0.0, 0.0)
#    #Scale
#    vector_math_005.inputs[3].default_value = 1.0

#    #node Grid
#    grid = gridbox.nodes.new("GeometryNodeMeshGrid")

#    #gridbox outputs
#    #output Geometry
#    gridbox.outputs.new('NodeSocketGeometry', "Geometry")
#    gridbox.outputs[0].attribute_domain = 'POINT'


#    #node Group Output
#    group_output = gridbox.nodes.new("NodeGroupOutput")

#    #node Join Geometry.002
#    join_geometry_002 = gridbox.nodes.new("GeometryNodeJoinGeometry")

#    #node Combine XYZ
#    combine_xyz = gridbox.nodes.new("ShaderNodeCombineXYZ")

#    #node Vector Math.010
#    vector_math_010 = gridbox.nodes.new("ShaderNodeVectorMath")
#    vector_math_010.operation = 'ADD'
#    #Vector_002
#    vector_math_010.inputs[2].default_value = (0.0, 0.0, 0.0)
#    #Scale
#    vector_math_010.inputs[3].default_value = 1.0

#    #node Vector Math.008
#    vector_math_008 = gridbox.nodes.new("ShaderNodeVectorMath")
#    vector_math_008.operation = 'MULTIPLY'
#    #Vector_001
#    vector_math_008.inputs[1].default_value = (0.0, 0.0, 1.0)
#    #Vector_002
#    vector_math_008.inputs[2].default_value = (0.0, 0.0, 0.0)
#    #Scale
#    vector_math_008.inputs[3].default_value = 1.0

#    #node Transform Geometry.004
#    transform_geometry_004 = gridbox.nodes.new("GeometryNodeTransform")
#    #Rotation
#    transform_geometry_004.inputs[2].default_value = (1.5707963705062866, 0.0, 0.0)
#    #Scale
#    transform_geometry_004.inputs[3].default_value = (1.0, 1.0, 1.0)

#    #node Vector Math.004
#    vector_math_004 = gridbox.nodes.new("ShaderNodeVectorMath")
#    vector_math_004.operation = 'MULTIPLY'
#    #Vector_001
#    vector_math_004.inputs[1].default_value = (0.0, -0.5, 0.5)
#    #Vector_002
#    vector_math_004.inputs[2].default_value = (0.0, 0.0, 0.0)
#    #Scale
#    vector_math_004.inputs[3].default_value = 1.0

#    #node Vector Math.014
#    vector_math_014 = gridbox.nodes.new("ShaderNodeVectorMath")
#    vector_math_014.operation = 'ADD'
#    #Vector_002
#    vector_math_014.inputs[2].default_value = (0.0, 0.0, 0.0)
#    #Scale
#    vector_math_014.inputs[3].default_value = 1.0

#    #node Vector Math.011
#    vector_math_011 = gridbox.nodes.new("ShaderNodeVectorMath")
#    vector_math_011.operation = 'ADD'
#    #Vector_002
#    vector_math_011.inputs[2].default_value = (0.0, 0.0, 0.0)
#    #Scale
#    vector_math_011.inputs[3].default_value = 1.0

#    #node Transform Geometry.005
#    transform_geometry_005 = gridbox.nodes.new("GeometryNodeTransform")
#    #Rotation
#    transform_geometry_005.inputs[2].default_value = (0.0, -1.5707963705062866, 0.0)
#    #Scale
#    transform_geometry_005.inputs[3].default_value = (1.0, 1.0, 1.0)

#    #node Vector Math.015
#    vector_math_015 = gridbox.nodes.new("ShaderNodeVectorMath")
#    vector_math_015.operation = 'ADD'
#    #Vector_002
#    vector_math_015.inputs[2].default_value = (0.0, 0.0, 0.0)
#    #Scale
#    vector_math_015.inputs[3].default_value = 1.0

#    #node Vector Math
#    vector_math = gridbox.nodes.new("ShaderNodeVectorMath")
#    vector_math.operation = 'MULTIPLY'
#    #Vector_001
#    vector_math.inputs[1].default_value = (1.0, 0.0, 1.0)
#    #Vector_002
#    vector_math.inputs[2].default_value = (0.0, 0.0, 0.0)
#    #Scale
#    vector_math.inputs[3].default_value = 1.0

#    #node Vector Math.001
#    vector_math_001 = gridbox.nodes.new("ShaderNodeVectorMath")
#    vector_math_001.operation = 'MULTIPLY'
#    #Vector_001
#    vector_math_001.inputs[1].default_value = (0.0, 1.0, 1.0)
#    #Vector_002
#    vector_math_001.inputs[2].default_value = (0.0, 0.0, 0.0)
#    #Scale
#    vector_math_001.inputs[3].default_value = 1.0

#    #node Vector Math.007
#    vector_math_007 = gridbox.nodes.new("ShaderNodeVectorMath")
#    vector_math_007.operation = 'MULTIPLY'
#    #Vector_001
#    vector_math_007.inputs[1].default_value = (0.0, 0.0, 0.0)
#    #Vector_002
#    vector_math_007.inputs[2].default_value = (0.0, 0.0, 0.0)
#    #Scale
#    vector_math_007.inputs[3].default_value = 1.0

#    #node Vector Math.017
#    vector_math_017 = gridbox.nodes.new("ShaderNodeVectorMath")
#    vector_math_017.operation = 'MULTIPLY'
#    #Vector_001
#    vector_math_017.inputs[1].default_value = (0.0, 1.0, 1.0)
#    #Vector_002
#    vector_math_017.inputs[2].default_value = (0.0, 0.0, 0.0)
#    #Scale
#    vector_math_017.inputs[3].default_value = 1.0

#    #node Transform Geometry
#    transform_geometry = gridbox.nodes.new("GeometryNodeTransform")
#    #Rotation
#    transform_geometry.inputs[2].default_value = (0.0, 1.5707963705062866, 0.0)
#    #Scale
#    transform_geometry.inputs[3].default_value = (1.0, 1.0, 1.0)

#    #node Vector Math.002
#    vector_math_002 = gridbox.nodes.new("ShaderNodeVectorMath")
#    vector_math_002.operation = 'MULTIPLY'
#    #Vector_001
#    vector_math_002.inputs[1].default_value = (0.5, 0.0, 0.5)
#    #Vector_002
#    vector_math_002.inputs[2].default_value = (0.0, 0.0, 0.0)
#    #Scale
#    vector_math_002.inputs[3].default_value = 1.0

#    #node Vector Math.012
#    vector_math_012 = gridbox.nodes.new("ShaderNodeVectorMath")
#    vector_math_012.operation = 'ADD'
#    #Vector_002
#    vector_math_012.inputs[2].default_value = (0.0, 0.0, 0.0)
#    #Scale
#    vector_math_012.inputs[3].default_value = 1.0

#    #node Vector Math.016
#    vector_math_016 = gridbox.nodes.new("ShaderNodeVectorMath")
#    vector_math_016.operation = 'MULTIPLY'
#    #Vector_001
#    vector_math_016.inputs[1].default_value = (1.0, 1.0, 0.0)
#    #Vector_002
#    vector_math_016.inputs[2].default_value = (0.0, 0.0, 0.0)
#    #Scale
#    vector_math_016.inputs[3].default_value = 1.0

#    #node Transform Geometry.002
#    transform_geometry_002 = gridbox.nodes.new("GeometryNodeTransform")
#    #Rotation
#    transform_geometry_002.inputs[2].default_value = (0.0, 0.0, 0.0)
#    #Scale
#    transform_geometry_002.inputs[3].default_value = (1.0, 1.0, 1.0)

#    #node Transform Geometry.001
#    transform_geometry_001 = gridbox.nodes.new("GeometryNodeTransform")
#    #Rotation
#    transform_geometry_001.inputs[2].default_value = (3.1415927410125732, 0.0, 0.0)
#    #Scale
#    transform_geometry_001.inputs[3].default_value = (1.0, 1.0, 1.0)

#    #node Vector Math.018
#    vector_math_018 = gridbox.nodes.new("ShaderNodeVectorMath")
#    vector_math_018.operation = 'MULTIPLY'
#    #Vector_001
#    vector_math_018.inputs[1].default_value = (1.0, 1.0, 0.0)
#    #Vector_002
#    vector_math_018.inputs[2].default_value = (0.0, 0.0, 0.0)
#    #Scale
#    vector_math_018.inputs[3].default_value = 1.0

#    #node Vector Math.013
#    vector_math_013 = gridbox.nodes.new("ShaderNodeVectorMath")
#    vector_math_013.operation = 'ADD'
#    #Vector_002
#    vector_math_013.inputs[2].default_value = (0.0, 0.0, 0.0)
#    #Scale
#    vector_math_013.inputs[3].default_value = 1.0

#    #node Vector Math.003
#    vector_math_003 = gridbox.nodes.new("ShaderNodeVectorMath")
#    vector_math_003.operation = 'MULTIPLY'
#    #Vector_001
#    vector_math_003.inputs[1].default_value = (0.0, 0.5, 0.5)
#    #Vector_002
#    vector_math_003.inputs[2].default_value = (0.0, 0.0, 0.0)
#    #Scale
#    vector_math_003.inputs[3].default_value = 1.0

#    #node Vector Math.019
#    vector_math_019 = gridbox.nodes.new("ShaderNodeVectorMath")
#    vector_math_019.operation = 'MULTIPLY'
#    #Vector_001
#    vector_math_019.inputs[1].default_value = (1.0, 0.0, 1.0)
#    #Vector_002
#    vector_math_019.inputs[2].default_value = (0.0, 0.0, 0.0)
#    #Scale
#    vector_math_019.inputs[3].default_value = 1.0

#    #node Transform Geometry.003
#    transform_geometry_003 = gridbox.nodes.new("GeometryNodeTransform")
#    #Rotation
#    transform_geometry_003.inputs[2].default_value = (-1.5707963705062866, 0.0, 0.0)
#    #Scale
#    transform_geometry_003.inputs[3].default_value = (1.0, 1.0, 1.0)

#    #node Vector Math.009
#    vector_math_009 = gridbox.nodes.new("ShaderNodeVectorMath")
#    vector_math_009.operation = 'SUBTRACT'
#    #Vector_002
#    vector_math_009.inputs[2].default_value = (0.0, 0.0, 0.0)
#    #Scale
#    vector_math_009.inputs[3].default_value = 1.0

#    #node Vector Math.006
#    vector_math_006 = gridbox.nodes.new("ShaderNodeVectorMath")
#    vector_math_006.operation = 'MULTIPLY'
#    #Vector_002
#    vector_math_006.inputs[2].default_value = (0.0, 0.0, 0.0)
#    #Scale
#    vector_math_006.inputs[3].default_value = 1.0

#    #node Reroute
#    reroute = gridbox.nodes.new("NodeReroute")
#    #node Reroute.002
#    reroute_002 = gridbox.nodes.new("NodeReroute")
#    #node Reroute.003
#    reroute_003 = gridbox.nodes.new("NodeReroute")
#    #node Reroute.004
#    reroute_004 = gridbox.nodes.new("NodeReroute")
#    #node Reroute.006
#    reroute_006 = gridbox.nodes.new("NodeReroute")
#    #gridbox inputs
#    #input Vector
#    gridbox.inputs.new('NodeSocketVector', "Vector")
#    gridbox.inputs[0].default_value = (0.0, 0.0, 0.0)
#    gridbox.inputs[0].min_value = -10000.0
#    gridbox.inputs[0].max_value = 10000.0
#    gridbox.inputs[0].attribute_domain = 'POINT'

#    #input Size X
#    gridbox.inputs.new('NodeSocketFloatDistance', "Size X")
#    gridbox.inputs[1].default_value = 10.0
#    gridbox.inputs[1].min_value = 0.0
#    gridbox.inputs[1].max_value = 3.4028234663852886e+38
#    gridbox.inputs[1].attribute_domain = 'POINT'

#    #input Size Y
#    gridbox.inputs.new('NodeSocketFloatDistance', "Size Y")
#    gridbox.inputs[2].default_value = 10.0
#    gridbox.inputs[2].min_value = 0.0
#    gridbox.inputs[2].max_value = 3.4028234663852886e+38
#    gridbox.inputs[2].attribute_domain = 'POINT'

#    #input Vertices X
#    gridbox.inputs.new('NodeSocketInt', "Vertices X")
#    gridbox.inputs[3].default_value = 20
#    gridbox.inputs[3].min_value = 2
#    gridbox.inputs[3].max_value = 1000
#    gridbox.inputs[3].attribute_domain = 'POINT'

#    #input Vertices Y
#    gridbox.inputs.new('NodeSocketInt', "Vertices Y")
#    gridbox.inputs[4].default_value = 20
#    gridbox.inputs[4].min_value = 2
#    gridbox.inputs[4].max_value = 1000
#    gridbox.inputs[4].attribute_domain = 'POINT'

#    #input Size Y
#    gridbox.inputs.new('NodeSocketFloatDistance', "Size Y")
#    gridbox.inputs[5].default_value = 10.0
#    gridbox.inputs[5].min_value = 0.0
#    gridbox.inputs[5].max_value = 3.4028234663852886e+38
#    gridbox.inputs[5].attribute_domain = 'POINT'

#    #input Vertices Y
#    gridbox.inputs.new('NodeSocketInt', "Vertices Y")
#    gridbox.inputs[6].default_value = 20
#    gridbox.inputs[6].min_value = 2
#    gridbox.inputs[6].max_value = 1000
#    gridbox.inputs[6].attribute_domain = 'POINT'

#    #input Input
#    gridbox.inputs.new('NodeSocketFloat', "Input")
#    gridbox.inputs[7].default_value = 0.0
#    gridbox.inputs[7].min_value = -3.4028234663852886e+38
#    gridbox.inputs[7].max_value = 3.4028234663852886e+38
#    gridbox.inputs[7].attribute_domain = 'POINT'


#    #node Group Input
#    group_input = gridbox.nodes.new("NodeGroupInput")

#    #node Reroute.001
#    reroute_001 = gridbox.nodes.new("NodeReroute")
#    #node Reroute.005
#    reroute_005 = gridbox.nodes.new("NodeReroute")
#    #node Reroute.007
#    reroute_007 = gridbox.nodes.new("NodeReroute")

#    #Set locations
#    grid_002.location = (-628.9307861328125, 220.70315551757812)
#    grid_003.location = (-632.7459716796875, -77.05184936523438)
#    grid_004.location = (-641.9114990234375, -401.07769775390625)
#    grid_005.location = (-648.3218994140625, -714.4976196289062)
#    grid_001.location = (-635.4530029296875, 830.9165649414062)
#    combine_xyz_004.location = (-229.0850830078125, -830.9165649414062)
#    vector_math_005.location = (-22.0362548828125, -807.1533813476562)
#    grid.location = (-581.7020263671875, 532.352783203125)
#    group_output.location = (2030.98388671875, 506.4398193359375)
#    join_geometry_002.location = (1847.1170654296875, 528.277099609375)
#    combine_xyz.location = (-1695.90869140625, 371.13214111328125)
#    vector_math_010.location = (3.0, 765.3900146484375)
#    vector_math_008.location = (-414.75067138671875, 177.6831512451172)
#    transform_geometry_004.location = (424.3248291015625, -409.91339111328125)
#    vector_math_004.location = (-239.8759765625, -496.4378662109375)
#    vector_math_014.location = (204.5, -470.4169616699219)
#    vector_math_011.location = (9.499992370605469, 484.31982421875)
#    transform_geometry_005.location = (417.9144287109375, -723.3333129882812)
#    vector_math_015.location = (278.8551025390625, -820.6716918945312)
#    vector_math.location = (7.993171691894531, -501.8639831542969)
#    vector_math_001.location = (136.80419921875, -926.6790161132812)
#    vector_math_007.location = (-476.9051208496094, 459.63311767578125)
#    vector_math_017.location = (-217.0, 700.6942138671875)
#    transform_geometry.location = (223.1070556640625, 826.3408813476562)
#    vector_math_002.location = (-416.93017578125, 772.93603515625)
#    vector_math_012.location = (-1.5000057220458984, 183.635986328125)
#    vector_math_016.location = (-210.5, 398.30780029296875)
#    transform_geometry_002.location = (218.3946990966797, 247.28350830078125)
#    transform_geometry_001.location = (229.2615966796875, 558.3370361328125)
#    vector_math_018.location = (-221.5, 83.86102294921875)
#    vector_math_013.location = (213.5, -171.34800720214844)
#    vector_math_003.location = (-222.17825317382812, -169.70785522460938)
#    vector_math_019.location = (-6.5, -196.61349487304688)
#    transform_geometry_003.location = (433.4903564453125, -85.88754272460938)
#    vector_math_009.location = (-1427.1661376953125, 486.54693603515625)
#    vector_math_006.location = (-931.374267578125, 964.5263061523438)
#    reroute.location = (-1455.6314697265625, 90.54962158203125)
#    reroute_002.location = (-1453.71826171875, 137.22195434570312)
#    reroute_003.location = (-1451.677001953125, 163.00619506835938)
#    reroute_004.location = (-1450.9180908203125, 178.63455200195312)
#    reroute_006.location = (-1455.502197265625, 98.19367218017578)
#    group_input.location = (-1689.7890625, 243.885498046875)
#    reroute_001.location = (-1454.624755859375, 118.9186019897461)
#    reroute_005.location = (-1450.9180908203125, 198.87049865722656)
#    reroute_007.location = (-1455.973388671875, 69.4941635131836)

#    #Set dimensions
#    grid_002.width, grid_002.height = 140.0, 100.0
#    grid_003.width, grid_003.height = 140.0, 100.0
#    grid_004.width, grid_004.height = 140.0, 100.0
#    grid_005.width, grid_005.height = 140.0, 100.0
#    grid_001.width, grid_001.height = 140.0, 100.0
#    combine_xyz_004.width, combine_xyz_004.height = 140.0, 100.0
#    vector_math_005.width, vector_math_005.height = 140.0, 100.0
#    grid.width, grid.height = 140.0, 100.0
#    group_output.width, group_output.height = 140.0, 100.0
#    join_geometry_002.width, join_geometry_002.height = 140.0, 100.0
#    combine_xyz.width, combine_xyz.height = 140.0, 100.0
#    vector_math_010.width, vector_math_010.height = 140.0, 100.0
#    vector_math_008.width, vector_math_008.height = 140.0, 100.0
#    transform_geometry_004.width, transform_geometry_004.height = 140.0, 100.0
#    vector_math_004.width, vector_math_004.height = 140.0, 100.0
#    vector_math_014.width, vector_math_014.height = 140.0, 100.0
#    vector_math_011.width, vector_math_011.height = 140.0, 100.0
#    transform_geometry_005.width, transform_geometry_005.height = 140.0, 100.0
#    vector_math_015.width, vector_math_015.height = 140.0, 100.0
#    vector_math.width, vector_math.height = 140.0, 100.0
#    vector_math_001.width, vector_math_001.height = 140.0, 100.0
#    vector_math_007.width, vector_math_007.height = 140.0, 100.0
#    vector_math_017.width, vector_math_017.height = 140.0, 100.0
#    transform_geometry.width, transform_geometry.height = 140.0, 100.0
#    vector_math_002.width, vector_math_002.height = 140.0, 100.0
#    vector_math_012.width, vector_math_012.height = 140.0, 100.0
#    vector_math_016.width, vector_math_016.height = 140.0, 100.0
#    transform_geometry_002.width, transform_geometry_002.height = 140.0, 100.0
#    transform_geometry_001.width, transform_geometry_001.height = 140.0, 100.0
#    vector_math_018.width, vector_math_018.height = 140.0, 100.0
#    vector_math_013.width, vector_math_013.height = 140.0, 100.0
#    vector_math_003.width, vector_math_003.height = 140.0, 100.0
#    vector_math_019.width, vector_math_019.height = 140.0, 100.0
#    transform_geometry_003.width, transform_geometry_003.height = 140.0, 100.0
#    vector_math_009.width, vector_math_009.height = 140.0, 100.0
#    vector_math_006.width, vector_math_006.height = 140.0, 100.0
#    reroute.width, reroute.height = 16.0, 100.0
#    reroute_002.width, reroute_002.height = 16.0, 100.0
#    reroute_003.width, reroute_003.height = 16.0, 100.0
#    reroute_004.width, reroute_004.height = 16.0, 100.0
#    reroute_006.width, reroute_006.height = 16.0, 100.0
#    group_input.width, group_input.height = 140.0, 100.0
#    reroute_001.width, reroute_001.height = 16.0, 100.0
#    reroute_005.width, reroute_005.height = 16.0, 100.0
#    reroute_007.width, reroute_007.height = 16.0, 100.0

#    #initialize gridbox links
#    #vector_math_014.Vector -> transform_geometry_004.Translation
#    gridbox.links.new(vector_math_014.outputs[0], transform_geometry_004.inputs[1])
#    #transform_geometry_001.Geometry -> join_geometry_002.Geometry
#    gridbox.links.new(transform_geometry_001.outputs[0], join_geometry_002.inputs[0])
#    #vector_math_010.Vector -> transform_geometry.Translation
#    gridbox.links.new(vector_math_010.outputs[0], transform_geometry.inputs[1])
#    #grid_001.Mesh -> transform_geometry.Geometry
#    gridbox.links.new(grid_001.outputs[0], transform_geometry.inputs[0])
#    #vector_math_012.Vector -> transform_geometry_002.Translation
#    gridbox.links.new(vector_math_012.outputs[0], transform_geometry_002.inputs[1])
#    #transform_geometry_005.Geometry -> join_geometry_002.Geometry
#    gridbox.links.new(transform_geometry_005.outputs[0], join_geometry_002.inputs[0])
#    #transform_geometry_002.Geometry -> join_geometry_002.Geometry
#    gridbox.links.new(transform_geometry_002.outputs[0], join_geometry_002.inputs[0])
#    #grid_005.Mesh -> transform_geometry_005.Geometry
#    gridbox.links.new(grid_005.outputs[0], transform_geometry_005.inputs[0])
#    #transform_geometry_004.Geometry -> join_geometry_002.Geometry
#    gridbox.links.new(transform_geometry_004.outputs[0], join_geometry_002.inputs[0])
#    #transform_geometry_003.Geometry -> join_geometry_002.Geometry
#    gridbox.links.new(transform_geometry_003.outputs[0], join_geometry_002.inputs[0])
#    #grid_003.Mesh -> transform_geometry_003.Geometry
#    gridbox.links.new(grid_003.outputs[0], transform_geometry_003.inputs[0])
#    #vector_math_015.Vector -> transform_geometry_005.Translation
#    gridbox.links.new(vector_math_015.outputs[0], transform_geometry_005.inputs[1])
#    #vector_math_011.Vector -> transform_geometry_001.Translation
#    gridbox.links.new(vector_math_011.outputs[0], transform_geometry_001.inputs[1])
#    #grid_004.Mesh -> transform_geometry_004.Geometry
#    gridbox.links.new(grid_004.outputs[0], transform_geometry_004.inputs[0])
#    #grid_002.Mesh -> transform_geometry_002.Geometry
#    gridbox.links.new(grid_002.outputs[0], transform_geometry_002.inputs[0])
#    #reroute_003.Output -> grid_002.Size Y
#    gridbox.links.new(reroute_003.outputs[0], grid_002.inputs[1])
#    #reroute_003.Output -> grid.Size Y
#    gridbox.links.new(reroute_003.outputs[0], grid.inputs[1])
#    #reroute_003.Output -> grid_005.Size Y
#    gridbox.links.new(reroute_003.outputs[0], grid_005.inputs[1])
#    #reroute_003.Output -> grid_001.Size Y
#    gridbox.links.new(reroute_003.outputs[0], grid_001.inputs[1])
#    #reroute_005.Output -> vector_math_003.Vector
#    gridbox.links.new(reroute_005.outputs[0], vector_math_003.inputs[0])
#    #group_input.Vector -> vector_math_002.Vector
#    gridbox.links.new(group_input.outputs[0], vector_math_002.inputs[0])
#    #group_input.Vector -> vector_math_007.Vector
#    gridbox.links.new(group_input.outputs[0], vector_math_007.inputs[0])
#    #reroute_005.Output -> vector_math_008.Vector
#    gridbox.links.new(reroute_005.outputs[0], vector_math_008.inputs[0])
#    #reroute_005.Output -> vector_math_004.Vector
#    gridbox.links.new(reroute_005.outputs[0], vector_math_004.inputs[0])
#    #reroute_005.Output -> vector_math_005.Vector
#    gridbox.links.new(reroute_005.outputs[0], vector_math_005.inputs[0])
#    #reroute_004.Output -> grid_002.Size X
#    gridbox.links.new(reroute_004.outputs[0], grid_002.inputs[0])
#    #reroute_004.Output -> grid.Size X
#    gridbox.links.new(reroute_004.outputs[0], grid.inputs[0])
#    #reroute_004.Output -> grid_003.Size X
#    gridbox.links.new(reroute_004.outputs[0], grid_003.inputs[0])
#    #reroute_004.Output -> grid_004.Size X
#    gridbox.links.new(reroute_004.outputs[0], grid_004.inputs[0])
#    #reroute_004.Output -> combine_xyz_004.X
#    gridbox.links.new(reroute_004.outputs[0], combine_xyz_004.inputs[0])
#    #reroute_002.Output -> grid_002.Vertices X
#    gridbox.links.new(reroute_002.outputs[0], grid_002.inputs[2])
#    #reroute_002.Output -> grid.Vertices X
#    gridbox.links.new(reroute_002.outputs[0], grid.inputs[2])
#    #reroute_002.Output -> grid_003.Vertices X
#    gridbox.links.new(reroute_002.outputs[0], grid_003.inputs[2])
#    #reroute_002.Output -> grid_004.Vertices X
#    gridbox.links.new(reroute_002.outputs[0], grid_004.inputs[2])
#    #reroute_001.Output -> grid_002.Vertices Y
#    gridbox.links.new(reroute_001.outputs[0], grid_002.inputs[3])
#    #reroute_001.Output -> grid.Vertices Y
#    gridbox.links.new(reroute_001.outputs[0], grid.inputs[3])
#    #reroute_001.Output -> grid_005.Vertices Y
#    gridbox.links.new(reroute_001.outputs[0], grid_005.inputs[3])
#    #reroute_001.Output -> grid_001.Vertices Y
#    gridbox.links.new(reroute_001.outputs[0], grid_001.inputs[3])
#    #reroute.Output -> grid_003.Size Y
#    gridbox.links.new(reroute.outputs[0], grid_003.inputs[1])
#    #reroute.Output -> grid_004.Size Y
#    gridbox.links.new(reroute.outputs[0], grid_004.inputs[1])
#    #reroute.Output -> grid_005.Size X
#    gridbox.links.new(reroute.outputs[0], grid_005.inputs[0])
#    #reroute.Output -> grid_001.Size X
#    gridbox.links.new(reroute.outputs[0], grid_001.inputs[0])
#    #reroute.Output -> combine_xyz_004.Z
#    gridbox.links.new(reroute.outputs[0], combine_xyz_004.inputs[2])
#    #join_geometry_002.Geometry -> group_output.Geometry
#    gridbox.links.new(join_geometry_002.outputs[0], group_output.inputs[0])
#    #group_input.Size X -> combine_xyz.X
#    gridbox.links.new(group_input.outputs[1], combine_xyz.inputs[0])
#    #group_input.Size Y -> combine_xyz.Y
#    gridbox.links.new(group_input.outputs[2], combine_xyz.inputs[1])
#    #group_input.Size Y -> combine_xyz.Z
#    gridbox.links.new(group_input.outputs[5], combine_xyz.inputs[2])
#    #vector_math_009.Vector -> vector_math_006.Vector
#    gridbox.links.new(vector_math_009.outputs[0], vector_math_006.inputs[0])
#    #transform_geometry.Geometry -> join_geometry_002.Geometry
#    gridbox.links.new(transform_geometry.outputs[0], join_geometry_002.inputs[0])
#    #vector_math_002.Vector -> vector_math_010.Vector
#    gridbox.links.new(vector_math_002.outputs[0], vector_math_010.inputs[0])
#    #vector_math_017.Vector -> vector_math_010.Vector
#    gridbox.links.new(vector_math_017.outputs[0], vector_math_010.inputs[1])
#    #vector_math_007.Vector -> vector_math_011.Vector
#    gridbox.links.new(vector_math_007.outputs[0], vector_math_011.inputs[0])
#    #vector_math_016.Vector -> vector_math_011.Vector
#    gridbox.links.new(vector_math_016.outputs[0], vector_math_011.inputs[1])
#    #vector_math_008.Vector -> vector_math_012.Vector
#    gridbox.links.new(vector_math_008.outputs[0], vector_math_012.inputs[0])
#    #vector_math_003.Vector -> vector_math_013.Vector
#    gridbox.links.new(vector_math_003.outputs[0], vector_math_013.inputs[0])
#    #vector_math_004.Vector -> vector_math_014.Vector
#    gridbox.links.new(vector_math_004.outputs[0], vector_math_014.inputs[0])
#    #vector_math_005.Vector -> vector_math_015.Vector
#    gridbox.links.new(vector_math_005.outputs[0], vector_math_015.inputs[0])
#    #vector_math_013.Vector -> transform_geometry_003.Translation
#    gridbox.links.new(vector_math_013.outputs[0], transform_geometry_003.inputs[1])
#    #vector_math.Vector -> vector_math_014.Vector
#    gridbox.links.new(vector_math.outputs[0], vector_math_014.inputs[1])
#    #vector_math_001.Vector -> vector_math_015.Vector
#    gridbox.links.new(vector_math_001.outputs[0], vector_math_015.inputs[1])
#    #vector_math_006.Vector -> vector_math.Vector
#    gridbox.links.new(vector_math_006.outputs[0], vector_math.inputs[0])
#    #vector_math_006.Vector -> vector_math_001.Vector
#    gridbox.links.new(vector_math_006.outputs[0], vector_math_001.inputs[0])
#    #vector_math_006.Vector -> vector_math_016.Vector
#    gridbox.links.new(vector_math_006.outputs[0], vector_math_016.inputs[0])
#    #vector_math_006.Vector -> vector_math_017.Vector
#    gridbox.links.new(vector_math_006.outputs[0], vector_math_017.inputs[0])
#    #vector_math_018.Vector -> vector_math_012.Vector
#    gridbox.links.new(vector_math_018.outputs[0], vector_math_012.inputs[1])
#    #vector_math_006.Vector -> vector_math_018.Vector
#    gridbox.links.new(vector_math_006.outputs[0], vector_math_018.inputs[0])
#    #grid.Mesh -> transform_geometry_001.Geometry
#    gridbox.links.new(grid.outputs[0], transform_geometry_001.inputs[0])
#    #vector_math_019.Vector -> vector_math_013.Vector
#    gridbox.links.new(vector_math_019.outputs[0], vector_math_013.inputs[1])
#    #vector_math_006.Vector -> vector_math_019.Vector
#    gridbox.links.new(vector_math_006.outputs[0], vector_math_019.inputs[0])
#    #combine_xyz.Vector -> vector_math_009.Vector
#    gridbox.links.new(combine_xyz.outputs[0], vector_math_009.inputs[0])
#    #group_input.Vector -> vector_math_009.Vector
#    gridbox.links.new(group_input.outputs[0], vector_math_009.inputs[1])
#    #reroute_006.Output -> vector_math_006.Vector
#    gridbox.links.new(reroute_006.outputs[0], vector_math_006.inputs[1])
#    #group_input.Size Y -> reroute.Input
#    gridbox.links.new(group_input.outputs[5], reroute.inputs[0])
#    #group_input.Vertices Y -> reroute_001.Input
#    gridbox.links.new(group_input.outputs[4], reroute_001.inputs[0])
#    #group_input.Vertices X -> reroute_002.Input
#    gridbox.links.new(group_input.outputs[3], reroute_002.inputs[0])
#    #group_input.Size Y -> reroute_003.Input
#    gridbox.links.new(group_input.outputs[2], reroute_003.inputs[0])
#    #group_input.Size X -> reroute_004.Input
#    gridbox.links.new(group_input.outputs[1], reroute_004.inputs[0])
#    #group_input.Input -> reroute_006.Input
#    gridbox.links.new(group_input.outputs[7], reroute_006.inputs[0])
#    #group_input.Vertices Y -> reroute_007.Input
#    gridbox.links.new(group_input.outputs[6], reroute_007.inputs[0])
#    #group_input.Vector -> reroute_005.Input
#    gridbox.links.new(group_input.outputs[0], reroute_005.inputs[0])
#    #reroute_007.Output -> grid_003.Vertices Y
#    gridbox.links.new(reroute_007.outputs[0], grid_003.inputs[3])
#    #reroute_007.Output -> grid_004.Vertices Y
#    gridbox.links.new(reroute_007.outputs[0], grid_004.inputs[3])
#    #reroute_007.Output -> grid_005.Vertices X
#    gridbox.links.new(reroute_007.outputs[0], grid_005.inputs[2])
#    #reroute_007.Output -> grid_001.Vertices X
#    gridbox.links.new(reroute_007.outputs[0], grid_001.inputs[2])
    return gridbox

gridbox = gridbox_node_group()

