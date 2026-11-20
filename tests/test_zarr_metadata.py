import bpy
import clearscale as cs
import numpy as np
import pytest
import zarr

from microscopynodes.blender_state import Dataset
from microscopynodes.ui.gui_to_data_model import parse_pixel_size
from microscopynodes.ui.preferences import addon_preferences

from .utils import do_load, prep_load


@pytest.fixture(autouse=True)
def default_channel_preferences():
    prefs = addon_preferences(bpy.context)
    if len(prefs.channels) == 0:
        prefs.set_channels(bpy.context)


def axis(name, type=None, unit=None):
    return {key: value for key, value in dict(name=name, type=type, unit=unit).items() if value}


def level(path, scale):
    return {"path": path, "coordinateTransformations": [{"type": "scale", "scale": scale}]}


def write_zarr(path, attrs, shapes, zarr_format=2):
    group = zarr.open_group(path, mode="w", zarr_format=zarr_format)
    for key, shape in shapes.items():
        group.create_array(key, shape=shape, dtype="uint16", chunks=shape)
    group.attrs.update(attrs)
    return str(path)


def load(path):
    scene = bpy.context.scene
    scene.MiN_input_file = str(path)
    return scene


def czyx_attrs(scale, omero=None, ome_namespace=False):
    multiscale = {
        "axes": [axis("c", "channel"), axis("z", "space", "micrometer"), axis("y", "space", "micrometer"), axis("x", "space", "micrometer")],
        "datasets": [level("0", scale), level("1", [scale[0], scale[1], scale[2] * 2, scale[3] * 2])],
    }
    attrs = {"multiscales": [{"version": "0.4", **multiscale}]}
    if omero:
        attrs["omero"] = omero
    if ome_namespace:
        attrs = {"ome": {"version": "0.5", "multiscales": [multiscale], **({"omero": omero} if omero else {})}}
    return attrs


WINDOW = {"min": 0, "max": 65535, "start": 0, "end": 65535}
OMERO = {"channels": [{"label": "DAPI", "color": "0000FF", "window": WINDOW}, {"label": "GFP", "color": "00FF00", "window": WINDOW}]}


@pytest.mark.parametrize("version", ["0.4", "0.5"])
def test_zarr_scales_unit_and_channel_names(tmp_path, version):
    attrs = czyx_attrs([1, 2.0, 0.5, 0.5], omero=OMERO, ome_namespace=version == "0.5")
    shapes = {"0": (2, 8, 64, 64), "1": (2, 8, 32, 32)}
    scene = load(write_zarr(tmp_path / "image.zarr", attrs, shapes, zarr_format=2 if version == "0.4" else 3))

    assert scene.MiN_enable_ui
    assert scene.MiN_axes_order == "czyx"
    assert scene.MiN_unit == "MICROMETER"
    assert [channel.name for channel in scene.MiN_channelList] == ["DAPI", "GFP"]
    assert [(option.xy_size, option.z_size) for option in scene.MiN_array_options] == [(0.5, 2.0), (1.0, 2.0)]
    assert (scene.MiN_xy_size, scene.MiN_z_size) == (1.0, 2.0), "the last level is selected by default"
    assert scene.MiN_yx_size_ratio == 1.0


def test_zarr_without_axes_defaults_to_tczyx(tmp_path):
    attrs = {"multiscales": [{"version": "0.1", "datasets": [{"path": "0"}]}]}
    scene = load(write_zarr(tmp_path / "old.zarr", attrs, {"0": (2, 2, 4, 8, 8)}))

    assert scene.MiN_enable_ui
    assert scene.MiN_axes_order == "tczyx"
    assert scene.MiN_channel_nr == 2


def test_zarr_without_z_axis_uses_xy_size_for_z(tmp_path):
    attrs = {"multiscales": [{"version": "0.4", "axes": [axis("y", "space", "nanometer"), axis("x", "space", "nanometer")],
                              "datasets": [level("0", [10.0, 10.0])]}]}
    scene = load(write_zarr(tmp_path / "plane.zarr", attrs, {"0": (16, 16)}))

    assert scene.MiN_unit == "NANOMETER"
    assert (scene.MiN_xy_size, scene.MiN_z_size) == (10.0, 10.0)


def test_zarr_0_6_multiscale_loads(tmp_path):
    micrometer = cs.Unit(z="micrometer", y="micrometer", x="micrometer")
    multiscale = cs.Multiscale.from_single(
        cs.Scale(shape=cs.Shape(z=8, y=64, x=64), pixel_size=cs.PixelSize(z=2.0, y=0.5, x=0.5), unit=micrometer),
        scale_key="s0",
    ).with_coordinate_system("stage", reached_by=cs.Translation(z=100.0, y=250.0, x=250.0))
    path = write_zarr(tmp_path / "v06.zarr", cs.OmeZarrGroup.from_single(multiscale).to_attrs(version="0.6"), {"s0": (8, 64, 64)}, zarr_format=3)
    scene = load(path)

    assert scene.MiN_enable_ui
    assert scene.MiN_axes_order == "zyx"
    assert (scene.MiN_xy_size, scene.MiN_z_size) == (0.5, 2.0)


def test_zarr_anisotropic_xy_pixel_sizes(tmp_path):
    attrs = czyx_attrs([1, 2.0, 0.5, 0.25])
    scene = load(write_zarr(tmp_path / "aniso.zarr", attrs, {"0": (2, 8, 64, 64), "1": (2, 8, 32, 32)}))

    assert [(option.xy_size, option.y_size) for option in scene.MiN_array_options] == [(0.25, 0.5), (0.5, 1.0)]
    assert scene.MiN_yx_size_ratio == pytest.approx(2.0)
    assert np.diag(parse_pixel_size())[:3] == pytest.approx([0.5, 1.0, 2.0]), "x, y and z of the selected level"

    scene.MiN_xy_size = 0.1
    assert np.diag(parse_pixel_size())[:3] == pytest.approx([0.1, 0.2, 2.0]), "editing the xy size keeps the ratio"


def test_zarr_anisotropic_dataset_has_physical_extents(tmp_path):
    prep_load()
    attrs = {"multiscales": [{"version": "0.4",
                              "axes": [axis("z", "space", "micrometer"), axis("y", "space", "micrometer"), axis("x", "space", "micrometer")],
                              "datasets": [level("0", [1.0, 2.0, 0.5])]}]}
    load(write_zarr(tmp_path / "aniso.zarr", attrs, {"0": (8, 16, 16)}))
    do_load()

    holder = Dataset(holder=bpy.context.scene.MiN_reload).holder
    assert holder.dataset_extents == pytest.approx([16 * 0.5, 16 * 2.0, 8 * 1.0])


def test_zarr_space_axes_in_different_units_are_converted(tmp_path):
    axes = [axis("z", "space", "micrometer"), axis("y", "space", "nanometer"), axis("x", "space", "nanometer")]
    attrs = {"multiscales": [{"version": "0.4", "axes": axes, "datasets": [level("0", [2.0, 500.0, 250.0])]}]}
    scene = load(write_zarr(tmp_path / "mixed_units.zarr", attrs, {"0": (4, 8, 8)}))

    assert scene.MiN_unit == "MICROMETER", "the unit of the first space axis"
    assert (scene.MiN_xy_size, scene.MiN_yx_size_ratio, scene.MiN_z_size) == pytest.approx((0.25, 2.0, 2.0))


def test_zarr_space_axes_with_unspecified_unit_are_not_converted(tmp_path):
    axes = [axis("z", "space", "micrometer"), axis("y", "space"), axis("x", "space", "micrometer")]
    attrs = {"multiscales": [{"version": "0.4", "axes": axes, "datasets": [level("0", [2.0, 0.5, 0.25])]}]}
    scene = load(write_zarr(tmp_path / "unspecified_unit.zarr", attrs, {"0": (4, 8, 8)}))

    assert scene.MiN_enable_ui
    assert scene.MiN_unit == "MICROMETER"
    assert (scene.MiN_xy_size, scene.MiN_yx_size_ratio, scene.MiN_z_size) == pytest.approx((0.25, 2.0, 2.0))


def test_zarr_with_invalid_axis_order_is_rejected(tmp_path):
    axes = [axis("t", "time", "second"), axis("z", "space"), axis("c", "channel"), axis("y", "space"), axis("x", "space")]
    attrs = {"multiscales": [{"version": "0.4", "axes": axes, "datasets": [level("0", [1.0] * 5)]}]}
    scene = load(write_zarr(tmp_path / "tzcyx.zarr", attrs, {"0": (2, 3, 2, 8, 8)}))

    assert not scene.MiN_enable_ui
    assert len(scene.MiN_array_options) == 0
    assert scene.MiN_progress_str.startswith("Found invalid or unsupported OME-Zarr")


def test_zarr_group_without_ome_metadata_is_rejected(tmp_path):
    group = zarr.open_group(tmp_path / "plain.zarr", mode="w", zarr_format=2)
    group.attrs["something"] = "else"
    scene = load(tmp_path / "plain.zarr")

    assert not scene.MiN_enable_ui
    assert scene.MiN_progress_str.startswith("No OME-Zarr image found")


def test_zarr_scene_group_points_to_its_images(tmp_path):
    def tile():
        return cs.Multiscale.from_single(cs.Scale(shape=cs.Shape(y=16, x=16), pixel_size=cs.PixelSize(y=0.5, x=0.5)))

    tile1, tile2 = tile(), tile()
    scene_metadata = cs.Scene.from_shared_coordinate_system(
        coordinate_system="stage",
        connections=[
            cs.Scene.Connection(tile1, to_shared=cs.Translation(y=0.0, x=0.0), path="tiles/t1"),
            cs.Scene.Connection(tile2, to_shared=cs.Translation(y=0.0, x=8.0), path="tiles/t2"),
        ],
    )
    root = zarr.open_group(tmp_path / "scene.zarr", mode="w", zarr_format=3)
    root.attrs.update(cs.OmeZarrGroup.from_single(scene_metadata).to_attrs(version="0.6"))
    for child_path, child in scene_metadata.multiscale_paths.items():
        child_group = root.require_group(child_path)
        child_group.attrs.update(cs.OmeZarrGroup.from_single(child).to_attrs(version="0.6"))
        for key in child:
            child_group.create_array(key, shape=(16, 16), dtype="uint16", chunks=(16, 16))

    scene = load(tmp_path / "scene.zarr")
    assert not scene.MiN_enable_ui
    assert "tiles/t1" in scene.MiN_progress_str

    scene = load(tmp_path / "scene.zarr" / "tiles" / "t1")
    assert scene.MiN_enable_ui
    assert scene.MiN_axes_order == "yx"
    assert scene.MiN_xy_size == 0.5
