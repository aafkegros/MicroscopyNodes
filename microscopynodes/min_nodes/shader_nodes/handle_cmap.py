import bpy
import cmap


def set_color_ramp(ch, ramp_node):
    lut, linear = get_lut(ch)
    for stop in range(len(ramp_node.color_ramp.elements) -2):
        ramp_node.color_ramp.elements.remove( ramp_node.color_ramp.elements[0] )

    for ix, color in enumerate(lut):
        if len(ramp_node.color_ramp.elements) <= ix:
            ramp_node.color_ramp.elements.new(ix/(len(lut)-linear))
        ramp_node.color_ramp.elements[ix].position = ix/(len(lut)-linear)
        ramp_node.color_ramp.elements[ix].color = (color[0],color[1],color[2],color[3])
    if not linear:
        ramp_node.color_ramp.interpolation = "CONSTANT"
    else:
        ramp_node.color_ramp.interpolation = "LINEAR"
    ramp_node.label = ch['cmap'].capitalize()
    return

def get_lut(ch):
    name = ch['cmap']
    if name.lower() == "single_color":
        lut = [[0,0,0,1], [*ch['single_color'],1]]
        linear = True
    else:
        lut = cmap.Colormap(name.lower()).lut(min(len(cmap.Colormap(name.lower()).lut()), 32))
        linear = (cmap.Colormap(name.lower()).interpolation == 'linear')
    return lut, linear
