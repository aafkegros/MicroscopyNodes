import bpy
from nodebpy import TreeBuilder, shader as s


GROUP_NAME = "Volume Transparency"
GROUP_BUILDER = "nodebpy"
ALPHA_MODE_LINEAR = "Linear Alpha"
ALPHA_MODE_CONSTANT = "Constant Alpha"


def _build_volume_alpha(tree):
    tree._arrange = "simple"
    tree.tree.description = "Compute clipped volume alpha from the alpha limits ramp."

    value = tree.inputs.float(
        "Value",
        description="Normalized voxel intensity used to compute transparency.",
    )
    alpha = tree.inputs.float(
        "Alpha Multiplier",
        default_value=1.0,
        description="Overall transparency strength for the channel. This translates to brightness for emission and density for scattering.",
        min_value=0.0,
        max_value=1000.0,
    )
    alpha_mode = tree.inputs.menu(
        "Alpha Mode",
        default_value="Linear Alpha",
        description="Choose whether alpha follows the alpha limits ramp or stays constant inside those limits.",
        expanded=True,
        optional_label = True,
    )

    alpha_output = tree.outputs.float("Alpha")
    coupling_output = tree.outputs.float("Alpha-Intensity Coupling")

    alpha_switch = s.MenuSwitch.float(
        menu=alpha_mode,
        items={
            ALPHA_MODE_LINEAR: value,
            ALPHA_MODE_CONSTANT: 1.0,
        },
    )

    clip_mask = (value > 0.0) * (value < 1.0)
    alpha_switch.o.output * alpha * clip_mask >> alpha_output
    tree.link(alpha_switch.node.outputs[ALPHA_MODE_LINEAR], coupling_output)


def volume_alpha_node():
    node_group = bpy.data.node_groups.get(GROUP_NAME)
    if node_group and node_group.get("builder") == GROUP_BUILDER:
        return node_group
    if node_group:
        bpy.data.node_groups.remove(node_group, do_unlink=True)

    with TreeBuilder.shader(GROUP_NAME, arrange="simple") as tree:
        _build_volume_alpha(tree)

    tree.tree["builder"] = GROUP_BUILDER
    return tree.tree
