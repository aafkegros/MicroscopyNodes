from .utils import *
import pytest


@pytest.mark.parametrize('level', [None, 0, 1, 2])
def test_zarr(level):
    prep_load()
    bpy.context.scene.MiN_input_file = str(Path(test_folder).parent / 'test_data' / '5D_5cube.zarr')
    
    if not level is None:
        bpy.context.scene.MiN_selected_array_option = str(bpy.context.scene.MiN_array_options[level].identifier)

    for ch in bpy.context.scene.MiN_channelList:
        ch.volume = True
        ch.surface = True
    ch_dicts = do_load()
    check_channels(ch_dicts, test_render=False)
    return



@pytest.mark.parametrize('which_not_update', [['MiN_update_data','MiN_update_settings'], ['MiN_update_data'], ['MiN_update_settings'], []])
def test_reload(which_not_update):
    prep_load()
    bpy.context.scene.MiN_input_file = str(Path(test_folder).parent  / 'test_data' / '5D_5cube.zarr')
    bpy.context.scene.MiN_selected_array_option = str(len(bpy.context.scene.MiN_array_options)-1)

    for ch in bpy.context.scene.MiN_channelList:
        ch.volume = True
        ch.surface = False
    
    ch_dicts1 = do_load()
    objects1 = set([obj.name for obj in bpy.data.objects])
    dataset1 = microscopynodes.load.Dataset(holder=bpy.context.scene.MiN_reload)
    state1 = _reload_debug_state("first", ch_dicts1, dataset1, objects1)

    assert bpy.context.scene.MiN_reload is not None
    for setting in which_not_update:
        setattr(bpy.context.scene, setting, False)

    for ch in bpy.context.scene.MiN_channelList:
        ch.volume = False
        ch.surface = True
    bpy.context.scene.MiN_channelList[0].volume = True

    bpy.context.scene.MiN_selected_array_option = str(len(bpy.context.scene.MiN_array_options) -2)
    ch_dicts2 = do_load()
    objects2 = set([obj.name for obj in bpy.data.objects])
    dataset2 = microscopynodes.load.Dataset(holder=bpy.context.scene.MiN_reload)
    state2 = _reload_debug_state("second", ch_dicts2, dataset2, objects2)
    
    if bpy.context.scene.MiN_update_data:
        assert len(objects1 - objects2) == 0, _reload_debug_message(
            which_not_update, objects1, objects2, state1, state2
        ) # existing objects are reused
        assert objects2 - objects1 == {"surface"}, _reload_debug_message(
            which_not_update, objects1, objects2, state1, state2
        ) # only the newly required surface object is added
    else:
        # surfaces were not created, so should not be checked
        for ch in ch_dicts2.channels:
            ch.viz.surface = False

    if bpy.context.scene.MiN_update_settings:
        check_channels(ch_dicts2, test_render=False)


def _reload_debug_state(label, dataset_model, dataset, object_names):
    channels = [
        {
            "ix": ch.data.ix,
            "volume": ch.viz.volume,
            "surface": ch.viz.surface,
            "labelmask": ch.viz.labelmask,
        }
        for ch in dataset_model.channels
    ]
    handles = {}
    for name in ("holder", "axes", "slicecube", "volume", "surface", "labelmask"):
        min_obj = getattr(dataset, name, None)
        handles[name] = None if min_obj is None or min_obj.object is None else min_obj.object.name
    return {
        "label": label,
        "array_option": bpy.context.scene.MiN_selected_array_option,
        "updates": {
            "data": bpy.context.scene.MiN_update_data,
            "settings": bpy.context.scene.MiN_update_settings,
        },
        "channels": channels,
        "handles": handles,
        "objects": sorted(object_names),
    }


def _reload_debug_message(which_not_update, objects1, objects2, state1, state2):
    return (
        f"which_not_update={which_not_update}\n"
        f"removed={sorted(objects1 - objects2)}\n"
        f"added={sorted(objects2 - objects1)}\n"
        f"first={state1}\n"
        f"second={state2}"
    )
