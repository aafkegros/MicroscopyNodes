import bpy 
from .. import t2b_nodes

def  get_nodes_last_output(group):
    try:
        output = group.nodes['Group Output']
    except:
        output = group.nodes['Material Output']
    try:
        last = output.inputs[0].links[0].from_node
        out_input = output.inputs[0]
    except:
        last = output.inputs[1].links[0].from_node
        out_input = output.inputs[1]
    return last, output, out_input


def insert_last_node(group, node, move = True):
    last, output = get_nodes_last_output(group)
    link = group.links.new
    location = output.location
    output.location = [location[0] + 300, location[1]]
    node.location = [location[0] - 300, location[1]]
    link(last.outputs[0], node.inputs[0])
    link(node.outputs[0], output.inputs[0])

def realize_instances(obj):
    group = obj.modifiers['GeometryNodes'].node_group
    realize = group.nodes.new('GeometryNodeRealizeInstances')
    insert_last_node(group, realize)

def append(node_name, link = False):
    node = bpy.data.node_groups.get(node_name)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if not node or link:
            bpy.ops.wm.append(
                directory = os.path.join(mn_data_file, 'NodeTree'), 
                filename = node_name, 
                link = link
            )
    
    return bpy.data.node_groups[node_name]

def insert_slicing(group, slice_obj):
    nodes = group.nodes
    links = group.links
    lastnode, outnode, output_input = get_nodes_last_output(group)
    texcoord = nodes.new('ShaderNodeTexCoord')
    texcoord.object = slice_obj
    texcoord.width = 200
    texcoord.location = (outnode.location[0], outnode.location[1]+100)

    slicecube = nodes.new('ShaderNodeGroup')
    slicecube.node_tree = t2b_nodes.slice_cube_node_group()
    slicecube.name = "Slice Cube"
    slicecube.width = 250
    slicecube.location = (outnode.location[0]+ 270, outnode.location[1])
    links.new(texcoord.outputs.get('Object'),slicecube.inputs.get('Slicing Object'))


    links.new(lastnode.outputs[0], slicecube.inputs.get("Shader"))
    links.new(slicecube.outputs.get("Shader"), output_input)
    outnode.location = (outnode.location[0]+550, outnode.location[1])
    return