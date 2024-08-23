import bpy, bpy_types


def init_holder(name, loadables, shaders):
    if len(loadables) == 0:
        return None
    if name == 'volume':
        bpy.ops.object.volume_add(align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
    else:
        bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.view_layer.objects.active
    obj.name = name
    
    bpy.ops.object.modifier_add(type='NODES')
    node_group = bpy.data.node_groups.new(name, 'GeometryNodeTree')  
    obj.modifiers[-1].node_group = node_group
    nodes = node_group.nodes
    links = node_group.links
    interface = node_group.interface
    print('finished making basic holder')
    lastnodes = []
    inputnode = nodes.new('NodeGroupInput')
    inputnode.location = (-900, 0)

    for ix, (loadable, shader) in enumerate(zip(loadables, shaders)):
        interface.new_socket(name=f"{loadable.name}", in_out="INPUT",socket_type='NodeSocketBool')
        identifier = interface.items_tree[-1].identifier
        obj.modifiers[-1][identifier] = True
        if isinstance(loadable, bpy_types.Collection):
            loadnode = nodes.new('GeometryNodeCollectionInfo')
            loadout = loadnode.outputs.get('Instances')
        elif isinstance(loadable, bpy_types.Object):
            loadnode = nodes.new('GeometryNodeObjectInfo')
            loadout = loadnode.outputs.get('Geometry')
            loadnode.inputs[1].default_value = True # load as instance
        loadnode.label = loadable.name
        loadnode.name = loadable.name
        loadnode.transform_space='RELATIVE'
        loadnode.inputs[0].default_value = loadable
        loadnode.location = (-300, ix * -200)
        # replace with material index when this is fixed for GN-objects
        # if not shared_shader:
        obj.data.materials.append(shader)
        setmat = nodes.new('GeometryNodeSetMaterial')
        links.new(loadout, setmat.inputs.get('Geometry'))
        setmat.location = (0, ix * -200)
        setmat.inputs.get('Material').default_value = shader
        setmat.name = 'Set Material ' + loadable.name

        switch = nodes.new('GeometryNodeSwitch')      
        switch.location = (200, ix * -200)  
        switch.input_type = 'GEOMETRY'
        links.new(inputnode.outputs.get(loadable.name), switch.inputs.get('Switch'))
        links.new(setmat.outputs.get('Geometry'), switch.inputs.get("True"))

        lastnodes.append(switch)
    print('finished setting nodes of holder')
    join = node_group.nodes.new("GeometryNodeJoinGeometry")
    join.location = (500, -100)
    for lastnode in reversed(lastnodes):
        links.new(lastnode.outputs[0], join.inputs[-1])
    

    node_group.interface.new_socket("Geometry",in_out="OUTPUT", socket_type='NodeSocketGeometry')
    outnode = nodes.new('NodeGroupOutput')
    outnode.location = (800, -100)
    links.new(join.outputs[0], outnode.inputs[0])

    for dim in range(3):
        obj.lock_location[dim] = True
        obj.lock_rotation[dim] = True
        obj.lock_scale[dim] = True
    return obj


def init_container(objects, location, name):
    container = bpy.ops.object.empty_add(type="PLAIN_AXES",location=location)
    container = bpy.context.view_layer.objects.active
    container.name = name 

    for obj in objects:
        if obj is None:
            continue
        obj.parent = container
        obj.matrix_parent_inverse = container.matrix_world.inverted()

    container.location = (0,0,0)
    return container