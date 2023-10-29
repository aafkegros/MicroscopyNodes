import bpy

def grid_verts_node_group():
    node_group = bpy.data.node_groups.get("_grid_verts")
    if node_group:
        return node_group
    node_group= bpy.data.node_groups.new(type = 'GeometryNodeTree', name = "_grid_verts")
    links = node_group.links
    
    # -- get IO --
    #node_group inputs
    #input Vector
    node_group.inputs.new('NodeSocketVector', "size (m)")
    node_group.inputs[-1].default_value = (13.0, 10.0, 6.0)
    node_group.inputs[-1].min_value = 0.0
    node_group.inputs[-1].max_value = 10000000.0
    node_group.inputs[-1].attribute_domain = 'POINT'

    #node Group Input
    group_input = node_group.nodes.new("NodeGroupInput")
    group_input.location = (-800,0)
    
    pos = node_group.nodes.new("GeometryNodeInputPosition")
    pos.location = (-600, 130)
    
    posXYZ =  node_group.nodes.new("ShaderNodeSeparateXYZ")
    posXYZ.location = (-400, 130)
    posXYZ.label = "posXYZ"
    links.new(pos.outputs[0], posXYZ.inputs[0])
    
    compnodes = [[],[],[]]
    for ix, side in enumerate(['min', 'max']):
        loc =  node_group.nodes.new("ShaderNodeVectorMath")
        loc.operation = "MULTIPLY"
        loc.location = (-600, -200 * ix)
        loc.label = "location 0,0,0"
        links.new(group_input.outputs.get("size (m)"), loc.inputs[0])
        if side == 'min':
            loc.inputs[1].default_value = (-0.5,-0.5,0)
        else: 
            loc.inputs[1].default_value = (0.5,0.5,1)
        locXYZ =  node_group.nodes.new("ShaderNodeSeparateXYZ")
        locXYZ.location = (-400, -130*ix)
        locXYZ.label = side + "XYZ"
        links.new(loc.outputs[0], locXYZ.inputs[0])
        
        
        for axix, ax in enumerate("XYZ"):
            # element wise compare
            compare = node_group.nodes.new("FunctionNodeCompare")
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
        ornode = node_group.nodes.new("FunctionNodeBooleanMath")
        ornode.operation = 'OR'
        for nix,compnode in enumerate(compnodes[axix]):
            links.new(compnode.outputs[0], ornode.inputs[nix])
        ornode.location = (0, (axix) * -200 +100)
        ornode.label = "vert in min or max of " + ax
        ornodes.append(ornode)
    
    andnodes = []
    for i in range(3):
        andnode = node_group.nodes.new("FunctionNodeBooleanMath")
        andnode.operation = 'AND'
        links.new(ornodes[i].outputs[0], andnode.inputs[0])
        links.new(ornodes[i-1].outputs[0], andnode.inputs[1])
        andnode.location = (200, i * -200 +100)
        andnodes.append(andnode)
    
    ornodes2 = []
    ornode = node_group.nodes.new("FunctionNodeBooleanMath")
    ornode.operation = 'OR'
    links.new(andnodes[0].outputs[0], ornode.inputs[0])
    links.new(andnodes[1].outputs[0], ornode.inputs[1])
    ornode.location = (400, 100)
    ornodes2.append(ornode)
    
    ornode = node_group.nodes.new("FunctionNodeBooleanMath")
    ornode.operation = 'OR'
    links.new(andnodes[1].outputs[0], ornode.inputs[0])
    links.new(andnodes[2].outputs[0], ornode.inputs[1])
    ornode.location = (400, -100)
    ornodes2.append(ornode)

    nornode = node_group.nodes.new("FunctionNodeBooleanMath")
    nornode.operation = 'NOR'
    links.new(ornodes2[0].outputs[0], nornode.inputs[0])
    links.new(ornodes2[1].outputs[0], nornode.inputs[1])
    nornode.location = (600, 100)

    #output Geometry
    node_group.outputs.new('NodeSocketBool', "Boolean")
    node_group.outputs[0].attribute_domain = 'POINT'
    group_output = node_group.nodes.new("NodeGroupOutput")
    group_output.location = (800,100)
    links.new(nornode.outputs[0], group_output.inputs[0])
    return node_group
