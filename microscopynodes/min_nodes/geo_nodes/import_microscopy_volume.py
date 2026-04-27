import bpy


GROUP_NAME = "Import Microscopy Volume"


def _set_common_socket_defaults(socket):
    socket.attribute_domain = 'POINT'
    if hasattr(socket, "default_input"):
        socket.default_input = 'VALUE'
    if hasattr(socket, "structure_type"):
        socket.structure_type = 'AUTO'


def _new_input(interface, name, socket_type, default=None):
    socket = interface.new_socket(name=name, in_out='INPUT', socket_type=socket_type)
    _set_common_socket_defaults(socket)
    if default is not None:
        socket.default_value = default
    return socket


def _new_output(interface, name, socket_type, default=None):
    socket = interface.new_socket(name=name, in_out='OUTPUT', socket_type=socket_type)
    _set_common_socket_defaults(socket)
    if default is not None:
        socket.default_value = default
    return socket


def import_microscopy_volume_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group:
        return node_group

    node_group = bpy.data.node_groups.new(type='GeometryNodeTree', name=GROUP_NAME)
    node_group.color_tag = 'NONE'
    node_group.description = ""
    node_group.default_group_node_width = 140
    node_group.is_modifier = True
    node_group.show_modifier_manage_panel = True

    links = node_group.links
    nodes = node_group.nodes
    interface = node_group.interface

    _new_output(interface, "Volume", 'NodeSocketGeometry')
    _new_output(interface, "Grid", 'NodeSocketFloat', 0.0)

    _new_input(interface, "Grid Name", 'NodeSocketString', "data")
    _new_input(interface, "Normalized", 'NodeSocketBool', True)

    vdb_minimum_socket = _new_input(interface, "VDB Minimum", 'NodeSocketFloat', 0.0)
    vdb_minimum_socket.min_value = -10000.0
    vdb_minimum_socket.max_value = 10000.0

    vdb_maximum_socket = _new_input(interface, "VDB Maximum", 'NodeSocketFloat', 1.0)
    vdb_maximum_socket.min_value = -10000.0
    vdb_maximum_socket.max_value = 10000.0

    _new_input(interface, "Original Maximum", 'NodeSocketFloat', 1.0)
    _new_input(interface, "Include", 'NodeSocketBool', False)

    _new_input(interface, "template_str", 'NodeSocketString', "")
    _new_input(interface, "cache_dir", 'NodeSocketString', "")
    _new_input(interface, "dataset_hash", 'NodeSocketString', "")
    _new_input(interface, "scale", 'NodeSocketInt', 0)
    _new_input(interface, "x", 'NodeSocketInt', 0)
    _new_input(interface, "y", 'NodeSocketInt', 0)
    _new_input(interface, "z", 'NodeSocketInt', 0)
    _new_input(interface, "channel_ix", 'NodeSocketInt', 0)
    _new_input(interface, "Frame", 'NodeSocketInt', 0)
    _new_input(interface, "original_path", 'NodeSocketString', "")
    _new_input(interface, "Channel Affine Matrix", 'NodeSocketMatrix')

    group_input = nodes.new("NodeGroupInput")
    group_input.name = "Group Input"
    group_input.location = (-760, 80)
    group_input.width = 150

    group_output = nodes.new("NodeGroupOutput")
    group_output.name = "Group Output"
    group_output.location = (1560, 20)
    group_output.is_active_output = True

    format_string = nodes.new("FunctionNodeFormatString")
    format_string.name = "Format String"
    format_string.location = (-580, -40)
    format_string.width = 410
    format_string.format_items.clear()
    for item_type, name in (
        ('STRING', "cache_dir"),
        ('STRING', "dataset_hash"),
        ('INT', "scale"),
        ('INT', "x"),
        ('INT', "y"),
        ('INT', "z"),
        ('INT', "channel_ix"),
        ('INT', "t"),
    ):
        format_string.format_items.new(item_type, name)

    links.new(group_input.outputs["template_str"], format_string.inputs["Format"])
    links.new(group_input.outputs["cache_dir"], format_string.inputs["cache_dir"])
    links.new(group_input.outputs["dataset_hash"], format_string.inputs["dataset_hash"])
    links.new(group_input.outputs["scale"], format_string.inputs["scale"])
    links.new(group_input.outputs["x"], format_string.inputs["x"])
    links.new(group_input.outputs["y"], format_string.inputs["y"])
    links.new(group_input.outputs["z"], format_string.inputs["z"])
    links.new(group_input.outputs["channel_ix"], format_string.inputs["channel_ix"])
    links.new(group_input.outputs["Frame"], format_string.inputs["t"])

    import_vdb = nodes.new("GeometryNodeImportVDB")
    import_vdb.name = "Import VDB"
    import_vdb.location = (-100, 160)
    links.new(format_string.outputs["String"], import_vdb.inputs["Path"])

    get_grid = nodes.new("GeometryNodeGetNamedGrid")
    get_grid.name = "Get Named Grid"
    get_grid.location = (90, 250)
    get_grid.data_type = 'FLOAT'
    get_grid.inputs["Name"].default_value = "data"
    get_grid.inputs["Remove"].default_value = True
    links.new(import_vdb.outputs["Volume"], get_grid.inputs["Volume"])
    links.new(group_input.outputs["Grid Name"], get_grid.inputs["Name"])

    map_range = nodes.new("ShaderNodeMapRange")
    map_range.name = "Map Range"
    map_range.location = (280, 290)
    map_range.clamp = True
    map_range.data_type = 'FLOAT'
    map_range.interpolation_type = 'LINEAR'
    map_range.inputs["To Min"].default_value = 0.0
    map_range.inputs["To Max"].default_value = 1.0
    links.new(get_grid.outputs["Grid"], map_range.inputs["Value"])
    links.new(group_input.outputs["VDB Minimum"], map_range.inputs["From Min"])
    links.new(group_input.outputs["VDB Maximum"], map_range.inputs["From Max"])

    store_normalized = nodes.new("GeometryNodeStoreNamedGrid")
    store_normalized.name = "Store Normalized Grid"
    store_normalized.location = (750, -40)
    store_normalized.data_type = 'FLOAT'
    links.new(import_vdb.outputs["Volume"], store_normalized.inputs["Volume"])
    links.new(group_input.outputs["Grid Name"], store_normalized.inputs["Name"])
    links.new(map_range.outputs["Result"], store_normalized.inputs["Grid"])

    restore_original_range = nodes.new("ShaderNodeMath")
    restore_original_range.name = "Restore Original Range"
    restore_original_range.location = (560, 265)
    restore_original_range.operation = 'MULTIPLY'
    restore_original_range.use_clamp = False
    links.new(map_range.outputs["Result"], restore_original_range.inputs["Value"])
    links.new(group_input.outputs["Original Maximum"], restore_original_range.inputs[1])

    store_original = nodes.new("GeometryNodeStoreNamedGrid")
    store_original.name = "Store Original Grid"
    store_original.location = (760, 105)
    store_original.data_type = 'FLOAT'
    links.new(import_vdb.outputs["Volume"], store_original.inputs["Volume"])
    links.new(group_input.outputs["Grid Name"], store_original.inputs["Name"])
    links.new(restore_original_range.outputs["Value"], store_original.inputs["Grid"])

    normalized_switch = nodes.new("GeometryNodeSwitch")
    normalized_switch.name = "Normalized Switch"
    normalized_switch.location = (960, 25)
    normalized_switch.input_type = 'GEOMETRY'
    links.new(group_input.outputs["Normalized"], normalized_switch.inputs["Switch"])
    links.new(store_original.outputs["Volume"], normalized_switch.inputs["False"])
    links.new(store_normalized.outputs["Volume"], normalized_switch.inputs["True"])

    include_switch = nodes.new("GeometryNodeSwitch")
    include_switch.name = "Include Switch"
    include_switch.location = (1170, 20)
    include_switch.input_type = 'GEOMETRY'
    links.new(group_input.outputs["Include"], include_switch.inputs["Switch"])
    links.new(normalized_switch.outputs["Output"], include_switch.inputs["True"])

    output_grid = nodes.new("GeometryNodeGetNamedGrid")
    output_grid.name = "Output Grid"
    output_grid.location = (1380, 30)
    output_grid.data_type = 'FLOAT'
    output_grid.inputs["Remove"].default_value = False
    links.new(include_switch.outputs["Output"], output_grid.inputs["Volume"])
    links.new(group_input.outputs["Grid Name"], output_grid.inputs["Name"])

    set_grid_transform = nodes.new("GeometryNodeSetGridTransform")
    set_grid_transform.name = "Set Channel Affine Transform"
    set_grid_transform.location = (1560, 250)
    set_grid_transform.data_type = 'FLOAT'
    links.new(output_grid.outputs["Grid"], set_grid_transform.inputs["Grid"])
    links.new(group_input.outputs["Channel Affine Matrix"], set_grid_transform.inputs["Transform"])

    store_transformed_grid = nodes.new("GeometryNodeStoreNamedGrid")
    store_transformed_grid.name = "Store Transformed Grid"
    store_transformed_grid.location = (1770, 80)
    store_transformed_grid.data_type = 'FLOAT'
    links.new(output_grid.outputs["Volume"], store_transformed_grid.inputs["Volume"])
    links.new(group_input.outputs["Grid Name"], store_transformed_grid.inputs["Name"])
    links.new(set_grid_transform.outputs["Grid"], store_transformed_grid.inputs["Grid"])

    group_output.location = (2020, 20)
    links.new(store_transformed_grid.outputs["Volume"], group_output.inputs["Volume"])
    links.new(set_grid_transform.outputs["Grid"], group_output.inputs["Grid"])

    return node_group
