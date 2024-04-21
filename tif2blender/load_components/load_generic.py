import bpy


def init_holder(name, colls, shaders):
    if len(colls) == 0:
        return None
    obj = bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.view_layer.objects.active
    obj.name = name
    
    bpy.ops.object.modifier_add(type='NODES')
    node_group = bpy.data.node_groups.new(name, 'GeometryNodeTree')  
    obj.modifiers[-1].node_group = node_group
    nodes = node_group.nodes
    links = node_group.links

    lastnodes = []
    for ix, (coll, shader) in enumerate(zip(colls, shaders)):
        collnode = nodes.new('GeometryNodeCollectionInfo')
        collnode.label = coll.name
        collnode.inputs[0].default_value = coll
        collnode.location = (-300, ix * -200)

        # replace with material index when this is fixed for GN-objects
        obj.data.materials.append(shader)
        setmat = nodes.new('GeometryNodeSetMaterial')
        links.new(collnode.outputs[0], setmat.inputs.get('Geometry'))
        setmat.location = (0, ix * -200)
        setmat.inputs.get('Material').default_value = shader
        lastnodes.append(setmat)
    
    join = node_group.nodes.new("GeometryNodeJoinGeometry")
    join.location = (200, -100)
    for lastnode in lastnodes:
        links.new(lastnode.outputs[0], join.inputs[-1])
    

    node_group.interface.new_socket("Geometry",in_out="OUTPUT", socket_type='NodeSocketGeometry')
    outnode = nodes.new('NodeGroupOutput')
    outnode.location = (400, -100)
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