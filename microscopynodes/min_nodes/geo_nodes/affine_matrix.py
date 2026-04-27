AFFINE_SOCKET_PREFIX = "Affine"


def affine_socket_name(row, column):
    return f"{AFFINE_SOCKET_PREFIX} {row}{column}"


def affine_socket_names():
    return [affine_socket_name(row, column) for row in range(4) for column in range(4)]


def _new_affine_inputs(interface, new_input):
    for row in range(4):
        for column in range(4):
            default = 1.0 if row == column else 0.0
            new_input(interface, affine_socket_name(row, column), "NodeSocketFloat", default)


def _link_affine_matrix(nodes, links, group_input, location):
    combine_matrix = nodes.new("FunctionNodeCombineMatrix")
    combine_matrix.name = "Channel Affine Matrix"
    combine_matrix.location = location
    for row in range(4):
        for column in range(4):
            socket_name = affine_socket_name(row, column)
            # Combine Matrix exposes sockets by column, with four row values per column.
            links.new(group_input.outputs[socket_name], combine_matrix.inputs[column * 4 + row])
    return combine_matrix.outputs["Matrix"]
