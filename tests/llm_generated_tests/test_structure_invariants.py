from pathlib import Path

import bpy
import numpy as np

import microscopynodes
from microscopynodes.handle_blender_structs.min_keys import min_keys
from microscopynodes.handle_blender_structs.node_handling import get_socket

from ..utils import prep_load, do_load


def _dataset_from_reload():
    return microscopynodes.load.Dataset(holder=bpy.context.scene.MiN_reload)


def _set_slice_cube_to_normalized_bounds(dataset_model, dataset, bounds_min, bounds_max):
    _, _, extent = dataset_model.intermediate_bbox
    bounds_min = np.array(bounds_min, dtype=float)
    bounds_max = np.array(bounds_max, dtype=float)
    center = (bounds_min + bounds_max) / 2.0
    size = bounds_max - bounds_min

    dataset.slicecube.object.location = dataset_model.dataset_origin_world + center * extent
    dataset.slicecube.object.scale = np.maximum(size * extent / 2.0, 1e-5)
    bpy.context.view_layer.update()


def _rounded_point_set(points):
    return {
        tuple(np.round(point, 6))
        for point in np.asarray(points, dtype=float)
    }


def _evaluate_object_for_test(obj):
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj.evaluated_get(depsgraph)
    depsgraph.update()


def _load_single_surface_with_affine_translation(translation):
    prep_load("5D_5cube")
    for ch in bpy.context.scene.MiN_channelList:
        ch.volume = False
        ch.surface = (ch.ix == 0)
        ch.labelmask = False

    dataset_model = microscopynodes.parse_inputs.parse_blender_ui()
    affine = np.array(dataset_model.channels[0].data.affine, dtype=float)
    affine[:3, 3] = np.array(translation, dtype=float)
    dataset_model.channels[0].data.affine = affine.tolist()

    microscopynodes.load.Scene.from_blender_ui()
    dataset = microscopynodes.load.Dataset(holder=bpy.context.scene.MiN_reload)
    dataset.set_state(
        dataset_model,
        update_data=bpy.context.scene.MiN_update_data,
        update_settings=bpy.context.scene.MiN_update_settings,
    )
    dataset.slicecube.object.scale = tuple(
        float(value) * 100.0
        for value in dataset.slicecube.object.scale
    )

    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = dataset.surface.object.evaluated_get(depsgraph)
    mesh = eval_obj.to_mesh()
    try:
        coords = np.array([v.co[:] for v in mesh.vertices], dtype=float)
    finally:
        eval_obj.to_mesh_clear()

    return coords.min(axis=0), coords.max(axis=0)


def test_volume_load_builds_expected_geometry_and_shader_structure():
    prep_load("5D_5cube")
    for ch in bpy.context.scene.MiN_channelList:
        ch.volume = True
        ch.surface = False
        ch.labelmask = False

    dataset_model = do_load()
    dataset = _dataset_from_reload()

    assert dataset.holder is not None
    assert dataset.axes is not None
    assert dataset.slicecube is not None
    assert dataset.volume is not None

    gn_nodes = dataset.volume.node_group.nodes
    assert gn_nodes.get("Group Input") is not None
    assert gn_nodes.get("Join") is not None
    assert gn_nodes.get("Set Material") is not None
    assert gn_nodes.get("Group Output") is not None

    mat = dataset.volume.object.data.materials[0]
    assert mat.name == f"{dataset_model.name} volume"
    shader_nodes = mat.node_tree.nodes
    assert shader_nodes.get("Add Shaders") is not None
    assert shader_nodes.get("Material Output") is not None

    visible_channels = [ch for ch in dataset_model.channels if ch.viz.volume]
    for ch in visible_channels:
        assert gn_nodes.get(f"IMPORT_{ch.identifier}") is not None
        assert gn_nodes.get(f"SLICE_CUBE_{ch.identifier}") is not None
        assert shader_nodes.get(f"[frame_{ch.identifier}]") is not None
        assert shader_nodes.get(f"[microscopy_shading_{ch.identifier}]") is not None


def test_surface_reload_does_not_reconnect_removed_shader_link():
    prep_load("5D_5cube")
    for ch in bpy.context.scene.MiN_channelList:
        ch.volume = False
        ch.surface = True
        ch.labelmask = False

    dataset_model = do_load()
    dataset = _dataset_from_reload()
    surface = dataset.surface
    mat = surface.object.data.materials[0]

    material_output = mat.node_tree.nodes["Material Output"]
    output_input = material_output.inputs["Surface"]
    assert len(output_input.links) == 1
    mat.node_tree.links.remove(output_input.links[0])
    assert len(output_input.links) == 0

    reloaded = microscopynodes.load.Dataset(holder=bpy.context.scene.MiN_reload)
    reloaded.set_state(
        dataset_model,
        update_data=bpy.context.scene.MiN_update_data,
        update_settings=bpy.context.scene.MiN_update_settings,
    )

    assert len(material_output.inputs["Surface"].links) == 0


def test_visibility_socket_matches_channel_visibility():
    prep_load("5D_5cube")
    for ch in bpy.context.scene.MiN_channelList:
        ch.volume = (ch.ix % 2 == 0)
        ch.surface = False
        ch.labelmask = False

    dataset_model = do_load()
    dataset = _dataset_from_reload()

    for ch in dataset_model.channels:
        if not ch.viz.volume:
            continue
        socket = get_socket(dataset.volume.node_group, ch, min_type="SWITCH")
        assert socket is not None
        assert dataset.volume.gn_mod[socket.identifier] == True


def test_volume_ensure_visibility_mask_without_moving_slice_cube_returns_normalized_points():
    prep_load("5D_5cube")
    for ch in bpy.context.scene.MiN_channelList:
        ch.volume = True
        ch.surface = False
        ch.labelmask = False

    do_load()
    dataset = _dataset_from_reload()
    
    _evaluate_object_for_test(dataset.volume.object)
    
    dataset.ensure_visibility_mask()
    locs = np.array(dataset.visibility.read_normalized_points(), dtype=float)
    voxel_extents = np.array(dataset.visibility.read_voxel_extents(), dtype=float)
    assert len(locs) > 0
    assert locs.shape[1] == 3
    assert np.all(locs >= -1e-6)
    assert np.all(locs <= 1.0 + 1e-6)
    assert np.allclose(voxel_extents, (1 / 20, 1 / 20, 1 / 10))


def test_load_with_mask_toggle_adds_visibility_mask_child():
    prep_load("5D_5cube")
    for ch in bpy.context.scene.MiN_channelList:
        ch.volume = True
        ch.surface = False
        ch.labelmask = False

    do_load()
    holder = bpy.context.scene.MiN_reload
    assert holder is not None

    bpy.context.scene.MiN_load_with_mask = True
    assert len([child for child in holder.children if child.name.startswith("visibility mask")]) == 1

    bpy.context.scene.MiN_load_with_mask = False
    assert len([child for child in holder.children if child.name.startswith("visibility mask")]) == 1


def test_volume_ensure_visibility_mask_tracks_moved_slice_cube_in_normalized_bbox():
    prep_load("5D_5cube")
    for ch in bpy.context.scene.MiN_channelList:
        ch.volume = True
        ch.surface = False
        ch.labelmask = False

    dataset_model = do_load()
    dataset = _dataset_from_reload()

    # _evaluate_object_for_test(dataset.volume.object)
    dataset.ensure_visibility_mask()
    full_locs = np.array(dataset.visibility.read_normalized_points(), dtype=float)
    assert len(full_locs) > 0

    full_min = full_locs.min(axis=0)
    full_max = full_locs.max(axis=0)
    slice_min = full_min + (full_max - full_min) * 0.25
    slice_max = full_min + (full_max - full_min) * 0.75

    _set_slice_cube_to_normalized_bounds(dataset_model, dataset, slice_min, slice_max)

    _evaluate_object_for_test(dataset.volume.object)
    dataset.ensure_visibility_mask()
    moved_locs = np.array(dataset.visibility.read_normalized_points(), dtype=float)
    moved_locs_in_full_bbox = slice_min + moved_locs * (slice_max - slice_min)
    expected_locs = full_locs[
        np.all((full_locs >= slice_min - 1e-6) & (full_locs <= slice_max + 1e-6), axis=1)
    ]

    assert len(moved_locs) > 0
    assert len(moved_locs) < len(full_locs)
    assert len(expected_locs) > 0
    assert np.all(moved_locs_in_full_bbox >= slice_min - 1e-6)
    assert np.all(moved_locs_in_full_bbox <= slice_max + 1e-6)


def test_reload_with_visibility_mask_keeps_masked_data_after_slice_cube_reset():
    prep_load("5D_5cube")
    for ch in bpy.context.scene.MiN_channelList:
        ch.volume = True
        ch.surface = False
        ch.labelmask = False

    dataset_model = do_load()
    dataset = _dataset_from_reload()
    dataset.ensure_visibility_mask()
    full_locs = np.array(dataset.visibility.read_normalized_points(), dtype=float)
    assert len(full_locs) > 0

    slice_min = np.array((0.25, 0.25, 0.25), dtype=float)
    slice_max = np.array((0.75, 0.75, 0.75), dtype=float)
    _set_slice_cube_to_normalized_bounds(dataset_model, dataset, slice_min, slice_max)

    bpy.context.scene.MiN_load_with_mask = True
    reload_model = microscopynodes.parse_inputs.parse_blender_ui()
    reload_dataset = _dataset_from_reload()
    assert all(channel.data.mask_indices is not None for channel in reload_model.channels)

    result = reload_model.make_local_files()
    assert result["ok"], result["error"]
    for channel in reload_model.channels:
        constructors = channel.file_constructors[min_keys.VOLUME]
        assert all(constructor["masked"] != "False" for constructor in constructors)
        assert all("mask_False" not in str(Path(str(constructor["template_str"]).format(**constructor))) for constructor in constructors)
    reload_dataset.set_state(
        reload_model,
        update_data=bpy.context.scene.MiN_update_data,
        update_settings=bpy.context.scene.MiN_update_settings,
    )

    _set_slice_cube_to_normalized_bounds(reload_model, reload_dataset, (0, 0, 0), (1, 1, 1))
    _evaluate_object_for_test(reload_dataset.volume.object)
    reload_dataset.ensure_visibility_mask()
    reset_locs = np.array(reload_dataset.visibility.read_normalized_points(), dtype=float)

    assert len(reset_locs) > 0
    assert len(reset_locs) < len(full_locs)
    visibility_children = [
        child
        for child in reload_dataset.holder.object.children
        if child.name == "visibility mask" or child.name.startswith("visibility mask.")
    ]
    assert len(visibility_children) == 1


def test_parse_clears_reload_when_holder_no_longer_passes_poll():
    prep_load("5D_5cube")
    for ch in bpy.context.scene.MiN_channelList:
        ch.volume = True
        ch.surface = False
        ch.labelmask = False

    do_load()
    holder = bpy.context.scene.MiN_reload
    assert holder is not None

    for child in list(holder.children):
        bpy.data.objects.remove(child, do_unlink=True)

    bpy.context.scene.MiN_update_data = False
    bpy.context.scene.MiN_update_settings = False

    microscopynodes.parse_inputs.parse_blender_ui()

    assert bpy.context.scene.MiN_reload is None
    assert bpy.context.scene.MiN_update_data is True
    assert bpy.context.scene.MiN_update_settings is True


def test_parse_clears_reload_when_holder_is_unlinked_from_scene():
    prep_load("5D_5cube")
    for ch in bpy.context.scene.MiN_channelList:
        ch.volume = True
        ch.surface = False
        ch.labelmask = False

    do_load()
    holder = bpy.context.scene.MiN_reload
    assert holder is not None

    for collection in list(holder.users_collection):
        collection.objects.unlink(holder)

    bpy.context.scene.MiN_update_data = False
    bpy.context.scene.MiN_update_settings = False

    microscopynodes.parse_inputs.parse_blender_ui()

    assert bpy.context.scene.MiN_reload is None
    assert bpy.context.scene.MiN_update_data is True
    assert bpy.context.scene.MiN_update_settings is True


def test_surface_affine_translation_offsets_local_mesh_vertices():
    base_mins, base_maxs = _load_single_surface_with_affine_translation((0.0, 0.0, 0.0))
    translated_mins, translated_maxs = _load_single_surface_with_affine_translation((7.0, 11.0, 13.0))

    np.testing.assert_allclose(translated_mins - base_mins, np.array([7.0, 11.0, 13.0]), atol=1e-4)
    np.testing.assert_allclose(translated_maxs - base_maxs, np.array([7.0, 11.0, 13.0]), atol=1e-4)
