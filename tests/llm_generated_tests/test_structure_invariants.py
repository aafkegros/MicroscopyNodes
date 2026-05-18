from pathlib import Path

import bpy
import numpy as np

import microscopynodes
from microscopynodes.handle_blender_structs import get_socket
from microscopynodes.handle_blender_structs.props import min_keys

from ..utils import prep_load, do_load


def _dataset_from_reload():
    return microscopynodes.load.Dataset(holder=bpy.context.scene.MiN_reload)


def _load_single_surface_with_affine_translation(translation):
    prep_load("5D_5cube")
    for ch in bpy.context.scene.MiN_channelList:
        ch["volume"] = False
        ch["surface"] = (ch.ix == 0)
        ch["labelmask"] = False

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
        ch["volume"] = True
        ch["surface"] = False
        ch["labelmask"] = False

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
        ch["volume"] = False
        ch["surface"] = True
        ch["labelmask"] = False

    dataset_model = do_load()
    dataset = _dataset_from_reload()
    surface = dataset.surface
    mat = surface.object.data.materials[0]

    material_output = mat.node_tree.nodes["Material Output"]
    output_input = material_output.inputs[surface.shader_output_name()]
    assert len(output_input.links) == 1
    mat.node_tree.links.remove(output_input.links[0])
    assert len(output_input.links) == 0

    reloaded = microscopynodes.load.Dataset(holder=bpy.context.scene.MiN_reload)
    reloaded.set_state(
        dataset_model,
        update_data=bpy.context.scene.MiN_update_data,
        update_settings=bpy.context.scene.MiN_update_settings,
    )

    assert len(material_output.inputs[surface.shader_output_name()].links) == 0


def test_visibility_socket_matches_channel_visibility():
    prep_load("5D_5cube")
    for ch in bpy.context.scene.MiN_channelList:
        ch["volume"] = (ch.ix % 2 == 0)
        ch["surface"] = False
        ch["labelmask"] = False

    dataset_model = do_load()
    dataset = _dataset_from_reload()

    for ch in dataset_model.channels:
        if not ch.viz.volume:
            continue
        socket = get_socket(dataset.volume.node_group, ch, min_type="SWITCH")
        assert socket is not None
        assert dataset.volume.gn_mod[socket.identifier] == True


def test_parse_clears_reload_when_holder_no_longer_passes_poll():
    prep_load("5D_5cube")
    for ch in bpy.context.scene.MiN_channelList:
        ch["volume"] = True
        ch["surface"] = False
        ch["labelmask"] = False

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
        ch["volume"] = True
        ch["surface"] = False
        ch["labelmask"] = False

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
