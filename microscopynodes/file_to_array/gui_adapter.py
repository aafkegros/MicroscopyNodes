from pathlib import Path

import bpy

from .arrayoptions import selected_array_option
from .rescaling import with_default_rescalings
from .tif import TifLoader
from .zarr import ZarrLoader
from ..handle_blender_structs.progress_handling import log
from ..handle_blender_structs.units import unit_name

LOADERS = [
    ((".tif", ".TIF", ".tiff", ".TIFF"), TifLoader),
    ((".zarr",), ZarrLoader),
]
_DATASET_OPTIONS_CACHE = {}
_ACTIVE_DATASET_OPTIONS_KEY = None


def _is_syncing_path(scene):
    return bool(scene.get("_MiN_syncing_input_file", False))


def get_loader(path=None):
    path = str(path or bpy.context.scene.MiN_input_file)
    suffix = Path(path).suffix
    for suffixes, Loader in LOADERS:
        if suffix in suffixes or any(item in path for item in suffixes):
            return Loader()
    return None


def dataset_options(path=None, axes_order=None, refresh=False):
    path = str(path or bpy.context.scene.MiN_input_file)
    cache_key = (path, axes_order)
    if not refresh and cache_key in _DATASET_OPTIONS_CACHE:
        return _DATASET_OPTIONS_CACHE[cache_key]
    loader = get_loader(path)
    if loader is None:
        return []
    options = with_default_rescalings(loader.native_options(path, axes_order=axes_order))
    _DATASET_OPTIONS_CACHE[cache_key] = options
    return options


def selected_dataset_model():
    path = str(bpy.context.scene.MiN_input_file)
    options = None
    if _ACTIVE_DATASET_OPTIONS_KEY is not None and _ACTIVE_DATASET_OPTIONS_KEY[0] == path:
        options = _DATASET_OPTIONS_CACHE.get(_ACTIVE_DATASET_OPTIONS_KEY)
    if options is None:
        options = dataset_options(path)
    if not options:
        return None
    try:
        return options[int(bpy.context.scene.MiN_selected_array_option)]
    except (IndexError, ValueError):
        return options[-1]


def change_path(self, context):
    scn = context.scene
    scn["_MiN_syncing_input_file"] = True
    try:
        scn.MiN_channel_nr = 0
        scn.MiN_enable_ui = False
        scn.property_unset("MiN_xy_size")
        scn.property_unset("MiN_z_size")
        scn.property_unset("MiN_axes_order")
        scn.property_unset("MiN_load_start_frame")
        scn.property_unset("MiN_load_end_frame")
        scn.property_unset("MiN_selected_array_option")
        scn.property_unset("MiN_ch_names")
        scn.MiN_array_options.clear()
        log("")
        scn.property_unset("MiN_reload")
        try:
            options = dataset_options(scn.MiN_input_file, refresh=True)
        except Exception as e:
            print(e)
            log(f"Error loading file: {e}")
            return
        if not options:
            return

        _fill_array_options(options, scn)
        _set_active_options(scn.MiN_input_file, _source_axes_order(options[-1]), options)
        scn.MiN_selected_array_option = str(len(options) - 1)
        _apply_dataset_to_scene(options[-1], scn)
        scn.MiN_enable_ui = True
    finally:
        scn["_MiN_syncing_input_file"] = False


def change_array_option(self, context):
    if _is_syncing_path(context.scene):
        return

    dataset_model = selected_dataset_model()
    if dataset_model is not None:
        if context.scene.MiN_enable_ui:
            _overwrite_channel_viz_from_scene(dataset_model, context.scene)
        axes_order = context.scene.MiN_axes_order or None
        _apply_dataset_to_scene(dataset_model, context.scene, axes_order_override=axes_order)


def channel_data_model(ch_ix, axes_order=None, **data_kwargs):
    dataset_model = selected_dataset_model()
    if dataset_model is None:
        return None
    channel_data = dataset_model.channels[ch_ix].data
    data = channel_data.model_copy(deep=False)
    for key, value in data_kwargs.items():
        setattr(data, key, value)
    if axes_order is not None:
        data.axes_order = axes_order.replace("c", "")
        data.source_axes_order = axes_order
        data._data_cache = None
    return data


def channel_data(ch_ix, axes_order=None):
    return channel_data_model(ch_ix, axes_order).data


def load_array(ch_dicts):
    return None


def change_channel_ax(self, context):
    if _is_syncing_path(context.scene):
        return

    scn = context.scene
    channel_axis = _channel_axis_ix(scn.MiN_axes_order)
    if scn.get("_MiN_channel_axis_ix", channel_axis) == channel_axis:
        return

    scn["_MiN_channel_axis_ix"] = channel_axis
    try:
        options = dataset_options(
            scn.MiN_input_file,
            axes_order=scn.MiN_axes_order,
            refresh=True,
        )
    except Exception as e:
        print(e)
        log(f"Error loading file: {e}")
        return
    if not options:
        return

    selected_ix = _selected_option_ix(scn, len(options))
    _set_active_options(scn.MiN_input_file, scn.MiN_axes_order, options)
    _fill_array_options(options, scn, axes_order_override=scn.MiN_axes_order)
    scn.MiN_selected_array_option = str(selected_ix)
    _apply_dataset_to_scene(
        options[selected_ix],
        scn,
        axes_order_override=scn.MiN_axes_order,
    )


def arr_shape():
    option = selected_array_option()
    return option.shape() if option is not None else []


def _fill_array_options(options, scene, axes_order_override=None):
    scene.MiN_array_options.clear()
    for ix, dataset_model in enumerate(options):
        option = scene.MiN_array_options.add()
        axes_order = axes_order_override or _source_axes_order(dataset_model)
        option.from_dataset(dataset_model, identifier=ix, axes_order=axes_order)


def _apply_dataset_to_scene(dataset_model, scene, axes_order_override=None):
    channel_data = dataset_model.channels[0].data
    axes_order = axes_order_override or _source_axes_order(dataset_model)
    affine = channel_data.affine_matrix

    scene["_MiN_channel_axis_ix"] = _channel_axis_ix(axes_order)
    scene.MiN_axes_order = axes_order
    scene.MiN_xy_size = float(affine[0][0])
    scene.MiN_z_size = float(affine[2][2])
    scene.MiN_unit = unit_name(channel_data.unit)
    scene.MiN_channel_nr = len(dataset_model.channels)

    selected = selected_array_option()
    t_max = max(selected.len_axis('t') - 1, 0) if selected is not None else 0
    scene.MiN_load_start_frame = 0
    scene.MiN_load_end_frame = min(scene.MiN_load_end_frame, t_max)

    _fill_channel_list(dataset_model, scene)


def _fill_channel_list(dataset_model, scene):
    scene.MiN_channelList.clear()
    for channel_model in dataset_model.channels:
        channel = scene.MiN_channelList.add()
        channel.from_channelviz(channel_model.viz)


def _overwrite_channel_viz_from_scene(dataset_model, scene):
    current_viz = {
        channel.ix: channel.to_channelviz()
        for channel in scene.MiN_channelList
    }
    for channel_model in dataset_model.channels:
        viz = current_viz.get(channel_model.data.ix)
        if viz is not None:
            channel_model.viz = viz.model_copy(deep=True)


def _source_axes_order(dataset_model):
    channel_data = dataset_model.channels[0].data
    if channel_data.source_axes_order:
        return channel_data.source_axes_order
    data_axes = channel_data.axes_order
    if len(dataset_model.channels) == 1:
        return data_axes
    return "c" + data_axes


def _channel_axis_ix(axes_order):
    return axes_order.find("c") if axes_order else -1


def _selected_option_ix(scene, option_count):
    try:
        return min(int(scene.MiN_selected_array_option), option_count - 1)
    except (TypeError, ValueError):
        return option_count - 1


def _set_active_options(path, axes_order, options):
    global _ACTIVE_DATASET_OPTIONS_KEY
    _ACTIVE_DATASET_OPTIONS_KEY = (str(path), axes_order)
    _DATASET_OPTIONS_CACHE[_ACTIVE_DATASET_OPTIONS_KEY] = options
