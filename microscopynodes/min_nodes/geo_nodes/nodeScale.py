import bpy
from .nodeScaleBox import scalebox_node_group, AXIS_ITEM_NAMES
from .nodeGridVerts import grid_verts_node_group
from .nodeHolderBundleInputs import holder_bundle_inputs_node_group


def _add_bundle_items(bundle_node, item_names, socket_type='BOOLEAN'):
    for name in item_names:
        bundle_node.bundle_items.new(socket_type, name)


def scale_node_group():
    node_group = bpy.data.node_groups.get("Scale bars")
    if node_group:
        return node_group

    node_group = bpy.data.node_groups.new(type='GeometryNodeTree', name="Scale bars")
    links = node_group.links
    interface = node_group.interface

    interface.new_socket("Holder", in_out="INPUT", socket_type='NodeSocketObject')

    interface.new_socket("Tick Step (unit)", in_out="INPUT", socket_type='NodeSocketFloat')
    interface.items_tree[-1].default_value = 1.0
    interface.items_tree[-1].min_value = 0.0
    interface.items_tree[-1].max_value = 3.4028234663852886e+38
    interface.items_tree[-1].attribute_domain = 'POINT'

    interface.new_socket("Grid", in_out="INPUT", socket_type='NodeSocketBool')
    interface.items_tree[-1].default_value = True
    interface.items_tree[-1].attribute_domain = 'POINT'

    interface.new_socket("Line thickness", in_out="INPUT", socket_type='NodeSocketFloat')
    interface.items_tree[-1].default_value = 0.1
    interface.items_tree[-1].min_value = 0.0
    interface.items_tree[-1].max_value = 3.4028234663852886e+38
    interface.items_tree[-1].attribute_domain = 'POINT'

    interface.new_socket("Tick Geometry", in_out="INPUT", socket_type='NodeSocketGeometry')
    interface.items_tree[-1].attribute_domain = 'POINT'

    interface.new_socket("Axis Bundle", in_out="INPUT", socket_type='NodeSocketBundle')
    interface.items_tree[-1].attribute_domain = 'POINT'

    interface.new_socket("Material", in_out="INPUT", socket_type='NodeSocketMaterial')

    interface.new_socket("Geometry", in_out="OUTPUT", socket_type='NodeSocketGeometry')
    interface.items_tree[-1].attribute_domain = 'POINT'

    group_input = node_group.nodes.new("NodeGroupInput")
    group_input.location = (-1400, 0)

    group_output = node_group.nodes.new("NodeGroupOutput")
    group_output.location = (2400, 0)

    self_object = node_group.nodes.new("GeometryNodeSelfObject")
    self_object.location = (-1200, 350)

    self_info = node_group.nodes.new("GeometryNodeObjectInfo")
    self_info.location = (-1000, 350)
    links.new(self_object.outputs["Self Object"], self_info.inputs["Object"])

    holder_inputs = node_group.nodes.new("GeometryNodeGroup")
    holder_inputs.node_tree = holder_bundle_inputs_node_group()
    holder_inputs.name = "Holder Bundle Inputs"
    holder_inputs.label = "Holder Bundle Inputs"
    holder_inputs.location = (-1200, 100)
    links.new(group_input.outputs["Holder"], holder_inputs.inputs["Holder"])

    world_per_unit_xyz = node_group.nodes.new("ShaderNodeCombineXYZ")
    world_per_unit_xyz.location = (-1000, 120)
    links.new(holder_inputs.outputs["Scene World Scale Base"], world_per_unit_xyz.inputs["X"])
    links.new(holder_inputs.outputs["Scene World Scale Base"], world_per_unit_xyz.inputs["Y"])
    links.new(holder_inputs.outputs["Scene World Scale Base"], world_per_unit_xyz.inputs["Z"])

    extent_unit = node_group.nodes.new("ShaderNodeVectorMath")
    extent_unit.operation = "DIVIDE"
    extent_unit.location = (-800, 350)
    links.new(self_info.outputs["Scale"], extent_unit.inputs[0])
    links.new(world_per_unit_xyz.outputs[0], extent_unit.inputs[1])

    local_per_unit = node_group.nodes.new("ShaderNodeVectorMath")
    local_per_unit.operation = "DIVIDE"
    local_per_unit.location = (-800, 120)
    links.new(world_per_unit_xyz.outputs[0], local_per_unit.inputs[0])
    links.new(self_info.outputs["Scale"], local_per_unit.inputs[1])

    scalebox = node_group.nodes.new("GeometryNodeGroup")
    scalebox.node_tree = scalebox_node_group()
    scalebox.location = (-500, 520)
    links.new(extent_unit.outputs[0], scalebox.inputs["Extent (unit)"])
    links.new(local_per_unit.outputs[0], scalebox.inputs["World per Unit"])
    links.new(group_input.outputs["Tick Step (unit)"], scalebox.inputs["Tick Step (unit)"])
    links.new(group_input.outputs["Axis Bundle"], scalebox.inputs["Axis Bundle"])

    normal = node_group.nodes.new("GeometryNodeInputNormal")
    normal.location = (-320, 430)

    store_normal = node_group.nodes.new("GeometryNodeStoreNamedAttribute")
    store_normal.location = (-120, 680)
    store_normal.inputs["Name"].default_value = "orig_normal"
    store_normal.data_type = 'FLOAT_VECTOR'
    store_normal.domain = 'EDGE'
    links.new(scalebox.outputs["Geometry"], store_normal.inputs[0])
    links.new(normal.outputs[0], store_normal.inputs["Value"])

    cap_normal = node_group.nodes.new("GeometryNodeCaptureAttribute")
    cap_normal.location = (-120, 380)
    links.new(scalebox.outputs["Geometry"], cap_normal.inputs[0])
    links.new(normal.outputs[0], cap_normal.inputs[1])

    grid_verts = node_group.nodes.new("GeometryNodeGroup")
    grid_verts.node_tree = grid_verts_node_group()
    grid_verts.location = (-500, 80)
    links.new(extent_unit.outputs[0], grid_verts.inputs["Extent (unit)"])
    links.new(local_per_unit.outputs[0], grid_verts.inputs["World per Unit"])

    nor_grid = node_group.nodes.new("FunctionNodeBooleanMath")
    nor_grid.operation = 'NOR'
    nor_grid.location = (-260, -20)
    links.new(grid_verts.outputs["Boolean"], nor_grid.inputs[0])
    links.new(group_input.outputs["Grid"], nor_grid.inputs[1])

    thickness = node_group.nodes.new("ShaderNodeMath")
    thickness.operation = "DIVIDE"
    thickness.location = (-420, -220)
    links.new(group_input.outputs["Line thickness"], thickness.inputs[0])
    thickness.inputs[1].default_value = 100.0

    iop = node_group.nodes.new("GeometryNodeInstanceOnPoints")
    iop.location = (500, 100)
    links.new(cap_normal.outputs[0], iop.inputs[0])
    links.new(grid_verts.outputs["Boolean"], iop.inputs[1])
    links.new(group_input.outputs["Tick Geometry"], iop.inputs[2])

    store_normaltick = node_group.nodes.new("GeometryNodeStoreNamedAttribute")
    store_normaltick.location = (740, 100)
    store_normaltick.inputs["Name"].default_value = "orig_normal"
    store_normaltick.data_type = 'FLOAT_VECTOR'
    store_normaltick.domain = 'INSTANCE'
    links.new(iop.outputs[0], store_normaltick.inputs[0])
    links.new(cap_normal.outputs[1], store_normaltick.inputs["Value"])

    realize = node_group.nodes.new("GeometryNodeRealizeInstances")
    realize.location = (930, 100)
    links.new(store_normaltick.outputs[0], realize.inputs[0])

    delgrid = node_group.nodes.new("GeometryNodeDeleteGeometry")
    delgrid.mode = 'ALL'
    delgrid.domain = 'POINT'
    delgrid.location = (420, 600)
    links.new(store_normal.outputs[0], delgrid.inputs[0])
    links.new(nor_grid.outputs[0], delgrid.inputs["Selection"])

    m2c = node_group.nodes.new("GeometryNodeMeshToCurve")
    m2c.location = (620, 600)
    links.new(delgrid.outputs[0], m2c.inputs[0])

    profile = node_group.nodes.new("GeometryNodeCurvePrimitiveQuadrilateral")
    profile.location = (620, 400)
    profile.mode = "RECTANGLE"
    links.new(thickness.outputs[0], profile.inputs[0])
    links.new(thickness.outputs[0], profile.inputs[1])

    c2m = node_group.nodes.new("GeometryNodeCurveToMesh")
    c2m.location = (850, 520)
    links.new(m2c.outputs[0], c2m.inputs[0])
    links.new(profile.outputs[0], c2m.inputs[1])

    join = node_group.nodes.new("GeometryNodeJoinGeometry")
    join.location = (1450, 0)
    links.new(c2m.outputs[0], join.inputs[0])
    links.new(realize.outputs[0], join.inputs[-1])

    separate_axes = node_group.nodes.new("NodeSeparateBundle")
    separate_axes.location = (1450, -350)
    _add_bundle_items(separate_axes, AXIS_ITEM_NAMES, 'BOOLEAN')
    links.new(group_input.outputs["Axis Bundle"], separate_axes.inputs["Bundle"])

    culling = node_group.nodes.new("GeometryNodeStoreNamedAttribute")
    culling.location = (1750, 10)
    culling.inputs["Name"].default_value = "frontface culling"
    culling.data_type = 'BOOLEAN'
    culling.domain = 'POINT'
    links.new(join.outputs[0], culling.inputs[0])
    links.new(separate_axes.outputs["frontface culling"], culling.inputs["Value"])

    material = node_group.nodes.new("GeometryNodeSetMaterial")
    material.location = (2050, 0)
    links.new(culling.outputs[0], material.inputs[0])
    links.new(group_input.outputs["Material"], material.inputs[2])

    links.new(material.outputs[0], group_output.inputs["Geometry"])

    return node_group
