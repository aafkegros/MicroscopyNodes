import bpy


def add_shaders_node(count=10):
    count = max(int(count), 1)
    group_name = f"Add Shaders {count}"
    node_group = bpy.data.node_groups.get(group_name)
    if node_group:
        return node_group

    node_group = bpy.data.node_groups.new(type='ShaderNodeTree', name=group_name)
    links = node_group.links
    interface = node_group.interface
    nodes = node_group.nodes

    interface.new_socket("Shader", in_out="OUTPUT", socket_type='NodeSocketShader')
    interface.items_tree[-1].attribute_domain = 'POINT'

    for ix in range(count):
        interface.new_socket(str(ix), in_out="INPUT", socket_type='NodeSocketShader')
        interface.items_tree[-1].attribute_domain = 'POINT'

    group_input = nodes.new("NodeGroupInput")
    group_input.location = (-300, 0)

    group_output = nodes.new("NodeGroupOutput")
    group_output.location = (300 + max(count - 2, 0) * 200, 0)
    group_output.is_active_output = True

    if count == 1:
        links.new(group_input.outputs[0], group_output.inputs[0])
        return node_group

    current_outputs = list(group_input.outputs[:count])
    level = 0

    while len(current_outputs) > 1:
        next_outputs = []
        y_start = (len(current_outputs) - 1) * 70 * 0.5
        x = level * 220

        for pair_ix in range(0, len(current_outputs), 2):
            if pair_ix + 1 >= len(current_outputs):
                next_outputs.append(current_outputs[pair_ix])
                continue

            add_shader = nodes.new("ShaderNodeAddShader")
            add_shader.location = (x, y_start - pair_ix * 70)
            links.new(current_outputs[pair_ix], add_shader.inputs[0])
            links.new(current_outputs[pair_ix + 1], add_shader.inputs[1])
            next_outputs.append(add_shader.outputs[0])

        current_outputs = next_outputs
        level += 1

    links.new(current_outputs[0], group_output.inputs[0])
    return node_group
