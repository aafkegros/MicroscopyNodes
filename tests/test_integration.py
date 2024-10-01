from microscopynodes.handle_blender_structs import *
import bpy
from microscopynodes.file_to_array import *

test_folder = Path(join(dirname(realpath(__file__)), "test_data"))

def make_tif(arrtype):
    



loadable = [['volume'],['surface'],['labelmask'], [], ['volume', 'surface'], 'mixed']

@pytest.mark.parametrize('load_as', loadable)
@pytest.mark.parametrize('arrtype', ['5D_5cube_nonrandom', '2D_5x10_nonrandom', '5D_random'])
def test_loading(arrtype, load_as)
    path = test_folder / arrtype.tif
    tif, arr, axes_order = make_tif(path, arrtype)
    scn = bpy.context.scene
    scn.MiN_input_file = str(path)
    assert(len(scn.MiN_channelList) == arr_shape[axes_order.find('c')])
    for ch in scn.MiN_channelList:
        ch['volume'] = False
        load_ch_as = load_as
        if load_as = 'mixed'
            load_ch_as = loadable[ch['ix'] % 4]
        for setting in load_ch_as:
            ch[setting] = True
        print(ch)
    


    return


