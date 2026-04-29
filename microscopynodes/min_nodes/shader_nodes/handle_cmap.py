import bpy
from cmap import Colormap


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
    if name.lower() == "single_color":
        return Colormap([[*single_color, 1.0]])
    return Colormap(name.lower())

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
        elem.color = tuple(lut[0])
    else:
        denom = (n - 1) if linear else n 
        for ix, color in enumerate(lut):
            if len(ramp_node.color_ramp.elements) <= ix:
                ramp_node.color_ramp.elements.new(ix / denom)
            elem = ramp_node.color_ramp.elements[ix]
            elem.position = ix / denom
            elem.color = tuple(color)

    ramp_node.color_ramp.interpolation = "LINEAR" if linear else "CONSTANT"
    ramp_node.label = name.capitalize()
    return
