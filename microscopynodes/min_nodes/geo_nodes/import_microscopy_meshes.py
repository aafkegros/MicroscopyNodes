import bpy


GROUP_NAME = "Import Microscopy Meshes"


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


def _new_output(interface, name, socket_type):
    socket = interface.new_socket(name=name, in_out='OUTPUT', socket_type=socket_type)
    _set_common_socket_defaults(socket)
    return socket


def import_microscopy_meshes_node_group():
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

    _new_output(interface, "Geometry", 'NodeSocketGeometry')

    _new_input(interface, "Include", 'NodeSocketBool', False)
    _new_input(interface, "template_str", 'NodeSocketString', "")
    _new_input(interface, "cache_dir", 'NodeSocketString', "")
    _new_input(interface, "dataset_hash", 'NodeSocketString', "")
    _new_input(interface, "scale", 'NodeSocketInt', 0)
    _new_input(interface, "resolution", 'NodeSocketInt', 0)
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
    group_output.location = (2010, -150)
    group_output.is_active_output = True

    format_string = nodes.new("FunctionNodeFormatString")
    format_string.name = "Format String"
    format_string.location = (-575, -15)
    format_string.width = 410
    format_string.format_items.clear()
    for item_type, name in (
        ('STRING', "cache_dir"),
        ('STRING', "dataset_hash"),
        ('INT', "scale"),
        ('INT', "resolution"),
        ('INT', "channel_ix"),
        ('INT', "t"),
    ):
        format_string.format_items.new(item_type, name)

    links.new(group_input.outputs["template_str"], format_string.inputs["Format"])
    links.new(group_input.outputs["cache_dir"], format_string.inputs["cache_dir"])
    links.new(group_input.outputs["dataset_hash"], format_string.inputs["dataset_hash"])
    links.new(group_input.outputs["scale"], format_string.inputs["scale"])
    links.new(group_input.outputs["resolution"], format_string.inputs["resolution"])
    links.new(group_input.outputs["channel_ix"], format_string.inputs["channel_ix"])
    links.new(group_input.outputs["Frame"], format_string.inputs["t"])

    obj_suffix = nodes.new("FunctionNodeInputString")
    obj_suffix.name = "OBJ Suffix"
    obj_suffix.location = (-130, -150)
    obj_suffix.string = ".obj"

    obj_path = nodes.new("GeometryNodeStringJoin")
    obj_path.name = "OBJ Path"
    obj_path.location = (60, -125)
    obj_path.inputs["Delimiter"].default_value = ""
    links.new(obj_suffix.outputs["String"], obj_path.inputs["Strings"])
    links.new(format_string.outputs["String"], obj_path.inputs["Strings"])


    import_obj = nodes.new("GeometryNodeImportOBJ")
    import_obj.name = "Import OBJ"
    import_obj.location = (275, -140)
    links.new(obj_path.outputs["String"], import_obj.inputs["Path"])

    csv_suffix = nodes.new("FunctionNodeInputString")
    csv_suffix.name = "CSV Suffix"
    csv_suffix.location = (-130, -240)
    csv_suffix.string = ".csv"

    csv_path = nodes.new("GeometryNodeStringJoin")
    csv_path.name = "CSV Path"
    csv_path.location = (60, -215)
    csv_path.inputs["Delimiter"].default_value = ""
    links.new(csv_suffix.outputs["String"], csv_path.inputs["Strings"])
    links.new(format_string.outputs["String"], csv_path.inputs["Strings"])


    import_csv = nodes.new("GeometryNodeImportCSV")
    import_csv.name = "Import CSV"
    import_csv.location = (275, -230)
    import_csv.inputs["Delimiter"].default_value = ","
    links.new(csv_path.outputs["String"], import_csv.inputs["Path"])

    foreach_in = nodes.new("GeometryNodeForeachGeometryElementInput")
    foreach_in.name = "For Each Mesh Island"
    foreach_in.location = (710, -110)
    foreach_in.inputs["Selection"].default_value = True
    links.new(import_obj.outputs["Instances"], foreach_in.inputs[0])

    foreach_out = nodes.new("GeometryNodeForeachGeometryElementOutput")
    foreach_out.name = "Store Object IDs"
    foreach_out.location = (1620, -105)
    foreach_out.domain = 'INSTANCE'
    foreach_out.generation_items.clear()
    foreach_out.generation_items.new('GEOMETRY', "Geometry")
    foreach_out.generation_items[0].domain = 'POINT'
    foreach_out.input_items.clear()
    foreach_out.main_items.clear()
    foreach_in.pair_with_output(foreach_out)

    named_oid = nodes.new("GeometryNodeInputNamedAttribute")
    named_oid.name = "CSV oid"
    named_oid.location = (960, -245)
    named_oid.data_type = 'INT'
    named_oid.inputs["Name"].default_value = "oid"

    sample_oid = nodes.new("GeometryNodeSampleIndex")
    sample_oid.name = "Sample oid"
    sample_oid.location = (1175, -235)
    sample_oid.clamp = False
    sample_oid.data_type = 'INT'
    sample_oid.domain = 'POINT'
    links.new(import_csv.outputs["Point Cloud"], sample_oid.inputs[0])
    links.new(named_oid.outputs["Attribute"], sample_oid.inputs[1])
    links.new(foreach_in.outputs["Index"], sample_oid.inputs[2])

    store_oid = nodes.new("GeometryNodeStoreNamedAttribute")
    store_oid.name = "Store oid"
    store_oid.location = (1430, -110)
    store_oid.data_type = 'INT'
    store_oid.domain = 'POINT'
    store_oid.inputs["Selection"].default_value = True
    store_oid.inputs["Name"].default_value = "oid"
    links.new(foreach_in.outputs["Element"], store_oid.inputs[0])
    links.new(sample_oid.outputs["Value"], store_oid.inputs[3])
    links.new(store_oid.outputs["Geometry"], foreach_out.inputs[1])

    transform_geometry = nodes.new("GeometryNodeTransform")
    transform_geometry.name = "Apply Channel Affine"
    transform_geometry.location = (1810, -105)
    transform_geometry.inputs[1].default_value = 'Matrix'
    links.new(foreach_out.outputs[2], transform_geometry.inputs["Geometry"])
    links.new(group_input.outputs["Channel Affine Matrix"], transform_geometry.inputs["Transform"])

    include_switch = nodes.new("GeometryNodeSwitch")
    include_switch.name = "Include Switch"
    include_switch.location = (2030, -150)
    include_switch.input_type = 'GEOMETRY'
    links.new(group_input.outputs["Include"], include_switch.inputs["Switch"])
    links.new(transform_geometry.outputs["Geometry"], include_switch.inputs["True"])
    links.new(include_switch.outputs["Output"], group_output.inputs["Geometry"])
    group_output.location = (2210, -150)

    return node_group
