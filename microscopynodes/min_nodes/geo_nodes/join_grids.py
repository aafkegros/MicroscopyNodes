import bpy


GROUP_NAME = "Join Grids"
MAX_CHANNELS = 10


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


def join_grids_node_group():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group:
        return node_group

    node_group = bpy.data.node_groups.new(type='GeometryNodeTree', name=GROUP_NAME)
    node_group.color_tag = 'NONE'
    node_group.description = ""
    node_group.default_group_node_width = 140
    node_group.show_modifier_manage_panel = True

    links = node_group.links
    nodes = node_group.nodes
    interface = node_group.interface

    _new_output(interface, "Geometry", 'NodeSocketGeometry')

    total_channels = _new_input(interface, "Total channels", 'NodeSocketInt', 0)
    total_channels.min_value = -2147483648
    total_channels.max_value = 2147483647

    for ix in range(MAX_CHANNELS):
        channel_socket = _new_input(interface, str(ix), 'NodeSocketFloat', 0.0)
        channel_socket.min_value = -3.4028234663852886e+38
        channel_socket.max_value = 3.4028234663852886e+38

    group_input = nodes.new("NodeGroupInput")
    group_input.name = "Group Input"
    group_input.location = (-760, 0)

    group_output = nodes.new("NodeGroupOutput")
    group_output.name = "Group Output"
    group_output.location = (745, 0)
    group_output.is_active_output = True

    repeat_input = nodes.new("GeometryNodeRepeatInput")
    repeat_input.name = "Repeat Input"
    repeat_input.location = (-555, 60)

    repeat_output = nodes.new("GeometryNodeRepeatOutput")
    repeat_output.name = "Repeat Output"
    repeat_output.location = (555, 10)
    repeat_output.active_index = 0
    repeat_output.inspection_index = 0
    repeat_output.repeat_items.clear()
    repeat_output.repeat_items.new('GEOMETRY', "Geometry")
    for ix in range(MAX_CHANNELS):
        repeat_output.repeat_items.new('FLOAT', str(ix))

    repeat_input.pair_with_output(repeat_output)

    index_switch = nodes.new("GeometryNodeIndexSwitch")
    index_switch.name = "Index Switch"
    index_switch.location = (-260, 30)
    index_switch.data_type = 'FLOAT'
    index_switch.index_switch_items.clear()
    for _ in range(MAX_CHANNELS):
        index_switch.index_switch_items.new()

    format_string = nodes.new("FunctionNodeFormatString")
    format_string.name = "Format String"
    format_string.location = (-70, 100)
    format_string.format_items.clear()
    format_string.format_items.new('INT', "i")
    format_string.inputs["Format"].default_value = "Channel {i}"

    store_grid = nodes.new("GeometryNodeStoreNamedGrid")
    store_grid.name = "Store Named Grid"
    store_grid.location = (140, 95)
    store_grid.data_type = 'FLOAT'

    links.new(group_input.outputs["Total channels"], repeat_input.inputs["Iterations"])
    links.new(repeat_input.outputs["Iteration"], index_switch.inputs["Index"])
    links.new(repeat_input.outputs["Iteration"], format_string.inputs["i"])

    links.new(repeat_input.outputs["Geometry"], store_grid.inputs["Volume"])
    links.new(format_string.outputs["String"], store_grid.inputs["Name"])
    links.new(index_switch.outputs["Output"], store_grid.inputs["Grid"])
    links.new(store_grid.outputs["Volume"], repeat_output.inputs["Geometry"])

    for ix in range(MAX_CHANNELS):
        socket_name = str(ix)
        links.new(group_input.outputs[socket_name], repeat_input.inputs[socket_name])
        links.new(repeat_input.outputs[socket_name], index_switch.inputs[ix + 1])
        links.new(repeat_input.outputs[socket_name], repeat_output.inputs[socket_name])

    links.new(repeat_output.outputs["Geometry"], group_output.inputs["Geometry"])

    return node_group
