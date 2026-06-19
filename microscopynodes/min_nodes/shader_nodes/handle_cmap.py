import bpy
from cmap import Color, Colormap


def set_color_ramp_from_ch(ch, ramp_node):
    lut, linear = colormap_to_lut(ch.viz.cmap)
    set_color_ramp(ramp_node, lut, linear, "Colormap")
    return


def colormap_to_lut(colormap, max_values=32):
    n_colors = min(max(len(colormap.color_stops), 1), max_values)
    lut = colormap.lut(n_colors)
    # Work around cmap emitting a transparent-black stop for some single-color cases.
    lut = [color for color in lut if list(color) != [0, 0, 0, 0]]
    if not lut:
        lut = [[0, 0, 0, 1]]
    linear = (colormap.interpolation == 'linear')
    return lut, linear


def get_colormap(name, single_color=(1, 1, 1)):
    name = name.lower()
    if name.startswith("black_to_single_color:"):
        return Colormap([
            (0.001, 0.001, 0.001, 1.0),
            Color(name.split(":", 1)[1]),
        ])
    if name.startswith("single_color:"):
        return Colormap([Color(name.split(":", 1)[1])])
    if name == "single_color":
        return Colormap([Color(tuple(single_color))])
    return Colormap(name)


def gamma_to_linear_channel(channel):
    channel = max(0.0, min(1.0, float(channel)))
    if channel <= 0.04045:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def gamma_to_linear_rgba(color):
    rgba = list(color)
    rgb = [gamma_to_linear_channel(channel) for channel in rgba[:3]]
    alpha = rgba[3] if len(rgba) > 3 else 1.0
    return (*rgb, alpha)


def set_color_ramp(ramp_node, lut, linear, name):
    from ...ui.preferences import addon_preferences
    if addon_preferences(bpy.context).invert_color:
        lut = list(reversed(lut))
    
    while len(ramp_node.color_ramp.elements) > 1:
        ramp_node.color_ramp.elements.remove(ramp_node.color_ramp.elements[0])

    n = len(lut)
    if n == 0:
        return

    if n == 1:
        elem = ramp_node.color_ramp.elements[0]
        elem.position = 0.5
        elem.color = gamma_to_linear_rgba(lut[0])
    else:
        denom = (n - 1) if linear else n 
        for ix, color in enumerate(lut):
            if len(ramp_node.color_ramp.elements) <= ix:
                ramp_node.color_ramp.elements.new(ix / denom)
            elem = ramp_node.color_ramp.elements[ix]
            elem.position = ix / denom
            elem.color = gamma_to_linear_rgba(color)

    ramp_node.color_ramp.interpolation = "LINEAR" if linear else "CONSTANT"
    if name.startswith("black_to_single_color:"):
        label = f"Black to {name.split(':', 1)[1]}"
    elif name.startswith("single_color:"):
        label = name.split(":", 1)[1]
    else:
        label = name
    ramp_node.label = label.capitalize()
    return
