import bpy


def mask_grid_node_group():
    node_group = bpy.data.node_groups.get("Mask Grid")
    if node_group:
        return node_group

    node_group = bpy.data.node_groups.new(type='GeometryNodeTree', name="Mask Grid")
    node_group.color_tag = 'NONE'
    node_group.description = ""
    node_group.default_group_node_width = 140
    node_group.show_modifier_manage_panel = True

    links = node_group.links
    nodes = node_group.nodes
    interface = node_group.interface

    interface.new_socket("Masked Grid", in_out="OUTPUT", socket_type='NodeSocketFloat')
    interface.items_tree[-1].default_value = 0.0
    interface.items_tree[-1].min_value = -3.4028234663852886e+38
    interface.items_tree[-1].max_value = 3.4028234663852886e+38
    interface.items_tree[-1].attribute_domain = 'POINT'
    interface.items_tree[-1].default_input = 'VALUE'
    interface.items_tree[-1].structure_type = 'AUTO'

    interface.new_socket("Grid", in_out="INPUT", socket_type='NodeSocketFloat')
    interface.items_tree[-1].default_value = 0.5
    interface.items_tree[-1].min_value = -10000.0
    interface.items_tree[-1].max_value = 10000.0
    interface.items_tree[-1].attribute_domain = 'POINT'
    interface.items_tree[-1].default_input = 'VALUE'
    interface.items_tree[-1].structure_type = 'GRID'

    interface.new_socket("With", in_out="INPUT", socket_type='NodeSocketMenu')
    with_socket = interface.items_tree[-1]
    with_socket.attribute_domain = 'POINT'
    with_socket.default_input = 'VALUE'
    with_socket.menu_expanded = False
    with_socket.structure_type = 'AUTO'
    with_socket.optional_label = True

    interface.new_socket("Object", in_out="INPUT", socket_type='NodeSocketObject')
    interface.items_tree[-1].attribute_domain = 'POINT'
    interface.items_tree[-1].default_input = 'VALUE'
    interface.items_tree[-1].structure_type = 'AUTO'

    interface.new_socket("Collection", in_out="INPUT", socket_type='NodeSocketCollection')
    interface.items_tree[-1].attribute_domain = 'POINT'
    interface.items_tree[-1].default_input = 'VALUE'
    interface.items_tree[-1].structure_type = 'AUTO'
    interface.items_tree[-1].optional_label = True

    interface.new_socket("Mesh", in_out="INPUT", socket_type='NodeSocketGeometry')
    interface.items_tree[-1].attribute_domain = 'POINT'
    interface.items_tree[-1].description = "Becomes the output value if it is chosen by the menu input"
    interface.items_tree[-1].default_input = 'VALUE'
    interface.items_tree[-1].structure_type = 'AUTO'

    interface.new_socket("Mask Resolution", in_out="INPUT", socket_type='NodeSocketFloat')
    interface.items_tree[-1].default_value = 0.30000001192092896
    interface.items_tree[-1].min_value = 0.009999999776482582
    interface.items_tree[-1].max_value = 3.4028234663852886e+38
    interface.items_tree[-1].subtype = 'DISTANCE'
    interface.items_tree[-1].attribute_domain = 'POINT'
    interface.items_tree[-1].default_input = 'VALUE'
    interface.items_tree[-1].structure_type = 'AUTO'
    interface.items_tree[-1].optional_label = True

    interface.new_socket("Mask", in_out="INPUT", socket_type='NodeSocketFloat')
    interface.items_tree[-1].default_value = 0.0
    interface.items_tree[-1].min_value = -3.4028234663852886e+38
    interface.items_tree[-1].max_value = 3.4028234663852886e+38
    interface.items_tree[-1].attribute_domain = 'POINT'
    interface.items_tree[-1].hide_value = True
    interface.items_tree[-1].default_input = 'VALUE'
    interface.items_tree[-1].structure_type = 'AUTO'
    interface.items_tree[-1].optional_label = True

    interface.new_socket("Invert", in_out="INPUT", socket_type='NodeSocketBool')
    interface.items_tree[-1].default_value = False
    interface.items_tree[-1].attribute_domain = 'POINT'
    interface.items_tree[-1].default_input = 'VALUE'
    interface.items_tree[-1].structure_type = 'AUTO'

    group_input = nodes.new("NodeGroupInput")
    group_input.name = "Group Input"
    group_input.location = (-1155, 10)

    group_output = nodes.new("NodeGroupOutput")
    group_output.name = "Group Output"
    group_output.location = (1525, -20)
    group_output.is_active_output = True

    object_info = nodes.new("GeometryNodeObjectInfo")
    object_info.name = "Object Info"
    object_info.location = (-940, 65)
    object_info.transform_space = 'RELATIVE'
    object_info.inputs["As Instance"].default_value = False
    links.new(group_input.outputs["Object"], object_info.inputs["Object"])

    collection_info = nodes.new("GeometryNodeCollectionInfo")
    collection_info.name = "Collection Info"
    collection_info.location = (-935, -165)
    collection_info.transform_space = 'RELATIVE'
    collection_info.inputs["Separate Children"].default_value = False
    collection_info.inputs["Reset Children"].default_value = False
    links.new(group_input.outputs["Collection"], collection_info.inputs["Collection"])

    menu_switch = nodes.new("GeometryNodeMenuSwitch")
    menu_switch.name = "Menu Switch"
    menu_switch.location = (-710, -85)
    menu_switch.active_index = 3
    menu_switch.data_type = 'GEOMETRY'
    menu_switch.enum_items.clear()
    menu_switch.enum_items.new("Object")
    menu_switch.enum_items[0].description = ""
    menu_switch.enum_items.new("Collection")
    menu_switch.enum_items[1].description = ""
    menu_switch.enum_items.new("Mesh")
    menu_switch.enum_items[2].description = ""
    menu_switch.enum_items.new("Grid")
    menu_switch.enum_items[3].description = ""
    menu_switch.enum_items.new("Box")
    menu_switch.enum_items[4].description = ""
    links.new(group_input.outputs["With"], menu_switch.inputs["Menu"])
    links.new(object_info.outputs["Geometry"], menu_switch.inputs["Object"])
    links.new(collection_info.outputs["Instances"], menu_switch.inputs["Collection"])
    links.new(group_input.outputs["Mesh"], menu_switch.inputs["Mesh"])
    links.new(object_info.outputs["Geometry"], menu_switch.inputs["Box"])
    with_socket.default_value = 'Object'

    realize_instances = nodes.new("GeometryNodeRealizeInstances")
    realize_instances.name = "Realize Instances"
    realize_instances.location = (-510, -35)
    realize_instances.realize_to_point_domain = False
    realize_instances.inputs["Selection"].default_value = True
    realize_instances.inputs["Realize All"].default_value = True
    realize_instances.inputs["Depth"].default_value = 0
    links.new(menu_switch.outputs["Output"], realize_instances.inputs["Geometry"])

    mesh_to_volume = nodes.new("GeometryNodeMeshToVolume")
    mesh_to_volume.name = "Mesh to Volume"
    mesh_to_volume.location = (-305, 0)
    mesh_to_volume.width = 200
    mesh_to_volume.inputs["Density"].default_value = 1.0
    mesh_to_volume.inputs["Resolution Mode"].default_value = 'Size'
    mesh_to_volume.inputs["Voxel Amount"].default_value = 20.0
    mesh_to_volume.inputs["Interior Band Width"].default_value = 0.0
    links.new(realize_instances.outputs["Geometry"], mesh_to_volume.inputs["Mesh"])
    links.new(group_input.outputs["Mask Resolution"], mesh_to_volume.inputs["Voxel Size"])

    get_named_grid = nodes.new("GeometryNodeGetNamedGrid")
    get_named_grid.name = "Get Named Grid"
    get_named_grid.location = (-70, -10)
    get_named_grid.data_type = 'FLOAT'
    get_named_grid.inputs["Name"].default_value = "density"
    get_named_grid.inputs["Remove"].default_value = True
    links.new(mesh_to_volume.outputs["Volume"], get_named_grid.inputs["Volume"])

    box_mesh_to_volume = nodes.new("GeometryNodeMeshToVolume")
    box_mesh_to_volume.name = "Box Mesh to Volume"
    box_mesh_to_volume.location = (-305, -205)
    box_mesh_to_volume.width = 200
    box_mesh_to_volume.inputs["Density"].default_value = 1.0
    box_mesh_to_volume.inputs["Resolution Mode"].default_value = 'Amount'
    box_mesh_to_volume.inputs["Voxel Size"].default_value = 0.30000001192092896
    box_mesh_to_volume.inputs["Voxel Amount"].default_value = 20.0
    box_mesh_to_volume.inputs["Interior Band Width"].default_value = 0.0
    links.new(realize_instances.outputs["Geometry"], box_mesh_to_volume.inputs["Mesh"])

    get_box_grid = nodes.new("GeometryNodeGetNamedGrid")
    get_box_grid.name = "Get Box Grid"
    get_box_grid.location = (-70, -210)
    get_box_grid.data_type = 'FLOAT'
    get_box_grid.inputs["Name"].default_value = "density"
    get_box_grid.inputs["Remove"].default_value = True
    links.new(box_mesh_to_volume.outputs["Volume"], get_box_grid.inputs["Volume"])

    box_switch = nodes.new("GeometryNodeSwitch")
    box_switch.name = "Box Switch"
    box_switch.location = (135, -115)
    box_switch.input_type = 'FLOAT'
    links.new(menu_switch.outputs["Box"], box_switch.inputs["Switch"])
    links.new(get_named_grid.outputs["Grid"], box_switch.inputs["False"])
    links.new(get_box_grid.outputs["Grid"], box_switch.inputs["True"])

    switch = nodes.new("GeometryNodeSwitch")
    switch.name = "Switch"
    switch.location = (315, -25)
    switch.input_type = 'FLOAT'
    links.new(menu_switch.outputs["Grid"], switch.inputs["Switch"])
    links.new(box_switch.outputs["Output"], switch.inputs["False"])
    links.new(group_input.outputs["Mask"], switch.inputs["True"])

    sample_grid = nodes.new("GeometryNodeSampleGrid")
    sample_grid.name = "Sample Grid"
    sample_grid.location = (540, 20)
    sample_grid.data_type = 'FLOAT'
    sample_grid.inputs["Position"].default_value = (0.0, 0.0, 0.0)
    sample_grid.inputs["Interpolation"].default_value = 'Trilinear'
    links.new(switch.outputs["Output"], sample_grid.inputs["Grid"])

    threshold = nodes.new("ShaderNodeMath")
    threshold.name = "Threshold"
    threshold.location = (730, 30)
    threshold.operation = 'GREATER_THAN'
    threshold.use_clamp = False
    threshold.inputs[1].default_value = 0.0
    links.new(sample_grid.outputs["Value"], threshold.inputs["Value"])

    invert_mask = nodes.new("FunctionNodeBooleanMath")
    invert_mask.name = "Invert Mask"
    invert_mask.location = (915, 85)
    invert_mask.operation = 'NOT'
    links.new(threshold.outputs["Value"], invert_mask.inputs[0])

    invert_switch = nodes.new("GeometryNodeSwitch")
    invert_switch.name = "Invert Switch"
    invert_switch.location = (915, -55)
    invert_switch.input_type = 'FLOAT'
    links.new(group_input.outputs["Invert"], invert_switch.inputs["Switch"])
    links.new(threshold.outputs["Value"], invert_switch.inputs["False"])
    links.new(invert_mask.outputs["Boolean"], invert_switch.inputs["True"])

    masked_grid = nodes.new("ShaderNodeMath")
    masked_grid.name = "Masked Grid"
    masked_grid.location = (1115, -20)
    masked_grid.operation = 'MULTIPLY'
    masked_grid.use_clamp = False
    links.new(group_input.outputs["Grid"], masked_grid.inputs[0])
    links.new(invert_switch.outputs["Output"], masked_grid.inputs[1])

    prune_grid = nodes.new("GeometryNodeGridPrune")
    prune_grid.name = "Prune Grid"
    prune_grid.location = (1325, -20)
    prune_grid.data_type = 'FLOAT'
    links.new(masked_grid.outputs["Value"], prune_grid.inputs["Grid"])
    links.new(prune_grid.outputs["Grid"], group_output.inputs["Masked Grid"])

    return node_group
