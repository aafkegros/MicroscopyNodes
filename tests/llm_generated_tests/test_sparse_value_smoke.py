import bpy
import pytest

import microscopynodes
from microscopynodes.handle_blender_structs.min_keys import min_keys
from microscopynodes.handle_blender_structs.node_handling import get_socket

from ..utils import (
    prep_load,
    do_load,
    quick_render,
    grayscale_histogram_distance,
)


SPARSE_LOADABLE = [
    ["volume"],
    ["surface"],
    ["labelmask"],
    [],
    # ["volume", "surface"], # these look very similar which is correct, removed them for now
    "mixed",
]


def _dataset_from_reload():
    return microscopynodes.load.Dataset(holder=bpy.context.scene.MiN_reload)


def _render_histogram_shift_for_channel(dataset, ch, min_type):
    ch_obj = getattr(dataset, min_type.name.lower())
    assert ch_obj is not None
    assert ch_obj.ch_present(ch)

    socket = get_socket(ch_obj.node_group, ch, min_type="SWITCH")
    assert socket is not None

    previous_axes_hide = dataset.axes.object.hide_render if dataset.axes is not None else None
    previous_slice_hide = dataset.slicecube.object.hide_render if dataset.slicecube is not None else None
    try:
        if dataset.axes is not None:
            dataset.axes.object.hide_render = True
        if dataset.slicecube is not None:
            dataset.slicecube.object.hide_render = True

        ch_obj.gn_mod[socket.identifier] = False
        off_img = quick_render(f"{min_type.name.lower()}_off")
        ch_obj.gn_mod[socket.identifier] = True
        on_img = quick_render(f"{min_type.name.lower()}_on")
    finally:
        ch_obj.gn_mod[socket.identifier] = True
        if dataset.axes is not None:
            dataset.axes.object.hide_render = previous_axes_hide
        if dataset.slicecube is not None:
            dataset.slicecube.object.hide_render = previous_slice_hide

    return grayscale_histogram_distance(off_img, on_img)


@pytest.mark.parametrize("load_as", SPARSE_LOADABLE)
def test_sparse_nonbinary_value_visualization_changes_render_distribution(load_as):
    prep_load("3D_sparse_value")

    for ch in bpy.context.scene.MiN_channelList:
        ch.volume = False
        ch.surface = False
        ch.labelmask = False

        load_ch_as = load_as
        if load_as == "mixed":
            load_ch_as = SPARSE_LOADABLE[ch.ix % 4]

        for setting in load_ch_as:
            setattr(ch, setting, True)

    dataset_model = do_load()
    dataset = _dataset_from_reload()

    checked_any = False
    for ch in dataset_model.channels:
        for min_type in (min_keys.VOLUME, min_keys.SURFACE, min_keys.LABELMASK):
            if not getattr(ch.viz, min_type.name.lower(), False):
                continue
            checked_any = True
            distance = _render_histogram_shift_for_channel(dataset, ch, min_type)
            assert distance > 0.02, f"{min_type.name.lower()} histogram shift too small: {distance}"

    if load_as == []:
        assert checked_any is False
    else:
        assert checked_any is True
