import bpy
import cmap


def set_color_ramp_from_ch(ch, ramp_node):
    set_color_ramp(ramp_node, ch.cmap, ch.cmap_is_linear, "Colormap")
    return

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

def get_lut(name, single_color):
    if name.lower() == "single_color":
        lut = [[*single_color,1]]
        linear = True
    else:
        lut = cmap.Colormap(name.lower()).lut(min(len(cmap.Colormap(name.lower()).lut()), 32))
        linear = (cmap.Colormap(name.lower()).interpolation == 'linear')
    return lut, linear
