import bpy 

def crosshatch_node_group():
    node_group = bpy.data.node_groups.get("crosshatch")
    if node_group:
        return node_group
    node_group = bpy.data.node_groups.new(type = 'GeometryNodeTree', name = "crosshatch")
    links = node_group.links

    node_group.inputs.new('NodeSocketFloat', "size")
    node_group.inputs[-1].default_value = 15.0
    node_group.inputs[-1].min_value = 0.0
    node_group.inputs[-1].max_value = 3.4028234663852886e+38
    node_group.inputs[-1].attribute_domain = 'POINT'
    
    node_group.inputs.new('NodeSocketFloat', "thickness")
    node_group.inputs[-1].default_value = 3.0
    node_group.inputs[-1].min_value = 0.0
    node_group.inputs[-1].max_value = 3.4028234663852886e+38
    node_group.inputs[-1].attribute_domain = 'POINT'

    group_input = node_group.nodes.new("NodeGroupInput")
    group_input.location = (-1000,0)

    tick_size =  node_group.nodes.new("ShaderNodeMath")
    tick_size.operation = "DIVIDE"
    tick_size.location = (-500, -500)
    tick_size.label = "tick length per direction"
    links.new(group_input.outputs.get("size"),  tick_size.inputs[0])
    tick_size.inputs[1].default_value = 100

    tick_thickness =  node_group.nodes.new("ShaderNodeMath")
    tick_thickness.operation = "DIVIDE"
    tick_thickness.location = (-500, -700)
    tick_thickness.label = "tick thickness scaled down"
    links.new(group_input.outputs.get("thickness"), tick_thickness.inputs[0])
    tick_thickness.inputs[1].default_value = 100
    
    cubes = []
    for axix, ax in enumerate("XYZ"):
        comb = node_group.nodes.new("ShaderNodeCombineXYZ")
        comb.location = (-200, -300 - 200*axix)
        for i in range(3):
            links.new(tick_thickness.outputs[0], comb.inputs[i])
        links.new(tick_size.outputs[0], comb.inputs[axix])
        cube = node_group.nodes.new("GeometryNodeMeshCube")
        cube.location = (0, -300 - 200*axix)
        links.new(comb.outputs[0], cube.inputs[0])
        cubes.append(cube)
        
    join_tick = node_group.nodes.new("GeometryNodeJoinGeometry")
    join_tick.location = (300, -500)
    for cube in reversed(cubes):
        links.new(cube.outputs[0], join_tick.inputs[0])
    
    node_group.outputs.new('NodeSocketGeometry', "Geometry")
    node_group.outputs[0].attribute_domain = 'POINT'
    group_output = node_group.nodes.new("NodeGroupOutput")
    group_output.location = (500,-200)
    links.new(join_tick.outputs[0], group_output.inputs[0])
    return node_group
    