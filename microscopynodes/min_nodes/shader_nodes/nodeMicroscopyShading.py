import bpy

from .nodeNormalizeLuminance import normalize_luminance_node


def microscopy_shading_node():
    node_group = bpy.data.node_groups.get("Microscopy Shading")
    if node_group and node_group.interface.items_tree.get("Emission / Scattering"):
        return node_group

    node_group = bpy.data.node_groups.new(type='ShaderNodeTree', name="Microscopy Shading")
    node_group.color_tag = 'SHADER'
    node_group.description = ""
    node_group.default_group_node_width = 180

    links = node_group.links
    interface = node_group.interface
    nodes = node_group.nodes

    interface.new_socket("Shader", in_out="OUTPUT", socket_type='NodeSocketShader')
    interface.items_tree[-1].attribute_domain = 'POINT'

    interface.new_socket("Color", in_out="INPUT", socket_type='NodeSocketColor')
    interface.items_tree[-1].default_value = (1.0, 1.0, 1.0, 1.0)
    interface.items_tree[-1].attribute_domain = 'POINT'
    interface.items_tree[-1].description = "Channel color after LUT mapping."

    interface.new_socket("Alpha", in_out="INPUT", socket_type='NodeSocketFloat')
    interface.items_tree[-1].default_value = 1.0
    interface.items_tree[-1].min_value = 0.0
    interface.items_tree[-1].max_value = 100.0
    interface.items_tree[-1].attribute_domain = 'POINT'
    interface.items_tree[-1].description = "Overall channel strength. This translates to brightness for emission and density for scattering."

    interface.new_socket("Alpha-Intensity Coupling", in_out="INPUT", socket_type='NodeSocketFloat')
    interface.items_tree[-1].default_value = 1.0
    interface.items_tree[-1].min_value = 0.0
    interface.items_tree[-1].max_value = 1.0
    interface.items_tree[-1].subtype = 'FACTOR'
    interface.items_tree[-1].attribute_domain = 'POINT'
    interface.items_tree[-1].description = "The amount of intensity coupling, used for normalizing the colormap brightness to achieve linear values"

    interface.new_socket("Emission / Scattering", in_out="INPUT", socket_type='NodeSocketFloat')
    interface.items_tree[-1].default_value = 0.0
    interface.items_tree[-1].min_value = 0.0
    interface.items_tree[-1].max_value = 1.0
    interface.items_tree[-1].subtype = 'FACTOR'
    interface.items_tree[-1].attribute_domain = 'POINT'
    interface.items_tree[-1].description = "Slide between emitting light (bright volume, at 0) and scattering light (dark volume, at 1)"

    group_input = nodes.new("NodeGroupInput")
    group_input.location = (-700, 0)

    group_output = nodes.new("NodeGroupOutput")
    group_output.location = (650, 0)
    group_output.is_active_output = True

    normalize = nodes.new("ShaderNodeGroup")
    normalize.node_tree = normalize_luminance_node()
    normalize.location = (-450, 130)
    normalize.label = "Ensure linear scaling"
    links.new(group_input.outputs["Color"], normalize.inputs["Color"])
    links.new(group_input.outputs["Alpha-Intensity Coupling"], normalize.inputs["Alpha-Intensity Coupling"])

    emission_strength = nodes.new("ShaderNodeMath")
    emission_strength.location = (-450, -80)
    emission_strength.operation = 'DIVIDE'
    emission_strength.inputs[1].default_value = 10
    emission_strength.label = "Divide by 10"
    links.new(group_input.outputs["Alpha"], emission_strength.inputs[0])

    emission = nodes.new("ShaderNodeEmission")
    emission.location = (-150, 160)
    links.new(normalize.outputs["Color"], emission.inputs["Color"])
    links.new(emission_strength.outputs[0], emission.inputs["Strength"])

    absorption = nodes.new("ShaderNodeVolumeAbsorption")
    absorption.location = (-150, -20)
    links.new(normalize.outputs["Color"], absorption.inputs["Color"])
    links.new(group_input.outputs["Alpha"], absorption.inputs["Density"])

    scatter = nodes.new("ShaderNodeVolumeScatter")
    scatter.location = (-150, -190)
    links.new(normalize.outputs["Color"], scatter.inputs["Color"])
    links.new(group_input.outputs["Alpha"], scatter.inputs["Density"])

    scatter_absorption = nodes.new("ShaderNodeAddShader")
    scatter_absorption.location = (150, -110)
    links.new(absorption.outputs["Volume"], scatter_absorption.inputs[0])
    links.new(scatter.outputs["Volume"], scatter_absorption.inputs[1])

    emission_scattering = nodes.new("ShaderNodeMixShader")
    emission_scattering.location = (400, 20)
    emission_scattering.label = "Emission / Scattering"
    links.new(group_input.outputs["Emission / Scattering"], emission_scattering.inputs["Fac"])
    links.new(emission.outputs["Emission"], emission_scattering.inputs[1])
    links.new(scatter_absorption.outputs["Shader"], emission_scattering.inputs[2])
    links.new(emission_scattering.outputs["Shader"], group_output.inputs["Shader"])

    return node_group
