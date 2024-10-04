from .utils import *
import pytest

@pytest.mark.parametrize('load_as', loadable)
@pytest.mark.parametrize('arrtype', ['5D_5cube', '2D_5x10', '5D_nonrect'])
def test_loading_types(arrtype, load_as):
    prep_load(arrtype)

    for ch in bpy.context.scene.MiN_channelList:
        ch['volume'] = False
        load_ch_as = load_as

        if load_as == 'mixed':
            load_ch_as = loadable[ch['ix'] % 4]
        for setting in load_ch_as:
            ch[setting] = True

    ch_dicts = do_load()
    check_channels(ch_dicts, test_render=True)
    return

