from .utils import *
import pytest


@pytest.mark.parametrize('level', [None, 0, 1, 2])
def test_zarr(level):
    prep_load()
    bpy.context.scene.MiN_input_file = str(Path(test_folder).parent / 'test_data' / '5D_5cube.zarr')
    
    if not level is None:
        bpy.context.scene.MiN_selected_array_option = str(bpy.context.scene.MiN_array_options[level].identifier)

    for ch in bpy.context.scene.MiN_channelList:
        ch['volume'] = True
        ch['surface'] = True
    ch_dicts = do_load()
    check_channels(ch_dicts, test_render=False)
    return



@pytest.mark.parametrize('which_not_update', [['MiN_update_data','MiN_update_settings'], ['MiN_update_data'], ['MiN_update_settings'], []])
def test_reload(which_not_update):
    prep_load()
    bpy.context.scene.MiN_input_file = str(Path(test_folder).parent  / 'test_data' / '5D_5cube.zarr')
    bpy.context.scene.MiN_selected_array_option = str(len(bpy.context.scene.MiN_array_options)-1)
    
    ch_dicts1 = do_load()
    objects1 = set([obj.name for obj in bpy.data.objects])

    bpy.context.scene.MiN_reload = bpy.data.objects[str(Path(bpy.context.scene.MiN_input_file).stem)]
    for setting in which_not_update:
        bpy.context.scene[setting] = False
    
    for ch in bpy.context.scene.MiN_channelList:
        ch['volume'] = False
        ch['surface'] = True
    bpy.context.scene.MiN_channelList[0]['volume'] = True
    
    bpy.context.scene.MiN_selected_array_option = str(len(bpy.context.scene.MiN_array_options) -2)
    ch_dicts2 = do_load()
    objects2 = set([obj.name for obj in bpy.data.objects])
    
    if bpy.context.scene.MiN_update_data:
        assert(len(objects1 - objects2) == 1) # only old data was deleted
        assert(len(objects2 - objects1) == 5 + 1) # new data (n channels) and surfaces were added
    else:
        # surfaces were not created, so should not be checked
        for ch in ch_dicts2:    
            ch[min_keys.SURFACE] = 0

    if bpy.context.scene.MiN_update_settings:
        check_channels(ch_dicts2, test_render=False)


    