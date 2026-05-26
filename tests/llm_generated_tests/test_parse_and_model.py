import bpy
import dask.array as da
import numpy as np
import pytest
from cmap import Colormap

import microscopynodes
from microscopynodes.data_model import ChannelModel, DatasetModel

from ..utils import prep_load, do_load


def _set_import_scale(scale_name):
    bpy.context.scene.MiN_import_scale = scale_name


def _make_channel(name="Channel 0", affine=None):
    if affine is None:
        affine = np.eye(4).tolist()
    return ChannelModel(
        cache_path="/tmp/example",
        data={
            "dataset_resolution": 0,
            "ix": 0,
            "data": da.zeros((4, 6, 8), dtype=np.uint16),
            "axes_order": "xyz",
            "affine": affine,
            "unit": 1e-6,
            "source": "test",
        },
        viz={
            "volume": True,
            "surface": False,
            "labelmask": False,
            "emission": True,
            "cmap": Colormap([(1.0, 1.0, 1.0, 1.0)]),
            "surf_resolution": 0,
            "name": name,
        },
    )


def test_parse_physical_scale_mode_uses_physical_pixel_sizes():
    prep_load("5D_5cube")
    bpy.context.scene.MiN_unit = "MICROMETER"
    bpy.context.scene.MiN_xy_size = 0.5
    bpy.context.scene.MiN_z_size = 2.0
    _set_import_scale("MICROMETER_SCALE")

    dataset_model = microscopynodes.parse_inputs.parse_blender_ui()
    scene = microscopynodes.load.Scene()

    assert scene.output_scale == pytest.approx(1e-6)
    assert dataset_model.unit_label == "µm"
    assert dataset_model.channels[0].data.affine[0][0] == pytest.approx(0.5)
    assert dataset_model.channels[0].data.affine[1][1] == pytest.approx(0.5)
    assert dataset_model.channels[0].data.affine[2][2] == pytest.approx(2.0)


def test_parse_physical_scale_mode_uses_physical_unit_label():
    prep_load("5D_5cube")
    _set_import_scale("MICROMETER_SCALE")

    dataset_model = microscopynodes.parse_inputs.parse_blender_ui()
    scene = microscopynodes.load.Scene()

    assert scene.output_scale == pytest.approx(1e-6)
    assert dataset_model.unit_label == "µm"


def test_import_scale_selector_rescales_loaded_holder_and_axes():
    prep_load("5D_5cube")
    bpy.context.scene.MiN_unit = "MICROMETER"
    bpy.context.scene.MiN_import_scale = "MICROMETER_SCALE"

    do_load()
    holder = bpy.context.scene.MiN_reload
    axes = next(child for child in holder.children if "axes" in child.name.lower())
    axes_modifier = next(mod for mod in axes.modifiers if "Microscopy Nodes" in mod.name)
    input_scale_input = next(
        item
        for item in axes_modifier.node_group.interface.items_tree
        if getattr(item, "item_type", None) == "SOCKET"
        and item.in_out == "INPUT"
        and item.name == "Input Scale"
    )
    output_scale_input = next(
        item
        for item in axes_modifier.node_group.interface.items_tree
        if getattr(item, "item_type", None) == "SOCKET"
        and item.in_out == "INPUT"
        and item.name == "Output Scale"
    )

    assert tuple(holder.scale) == pytest.approx((1.0, 1.0, 1.0))
    assert axes_modifier[input_scale_input.identifier] == pytest.approx(1e-6)
    assert axes_modifier[output_scale_input.identifier] == pytest.approx(1e-6)

    bpy.context.scene.MiN_import_scale = "MICROMETER_CENTIMETER_SCALE"

    assert tuple(holder.scale) == pytest.approx((0.01, 0.01, 0.01))
    assert axes_modifier[input_scale_input.identifier] == pytest.approx(1e-6)
    assert axes_modifier[output_scale_input.identifier] == pytest.approx(1e-4)


def test_dataset_bbox_and_center_properties():
    dataset_model = DatasetModel(
        name="bbox-test",
        channels=[_make_channel()],
        relative_loc=(-0.5, -0.5, 0.0),
    )

    mins, maxs, extent = dataset_model.intermediate_bbox
    np.testing.assert_allclose(mins, np.array([0.0, 0.0, 0.0]))
    np.testing.assert_allclose(maxs, np.array([4.0, 6.0, 8.0]))
    np.testing.assert_allclose(extent, np.array([4.0, 6.0, 8.0]))
    np.testing.assert_allclose(dataset_model.dataset_origin_world, np.array([-2.0, -3.0, 0.0]))
    np.testing.assert_allclose(dataset_model.dataset_center_world, np.array([0.0, 0.0, 4.0]))
