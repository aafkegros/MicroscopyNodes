from pathlib import Path

import bpy

import microscopynodes
from microscopynodes.handle_blender_structs import get_socket
from microscopynodes.handle_blender_structs.props import min_keys

from ..utils import prep_load, do_load


def _dataset_from_reload():
    return microscopynodes.load.Dataset(holder=bpy.context.scene.MiN_reload)


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
    assert shader_nodes.get("Slice Cube") is not None
    assert shader_nodes.get("Material Output") is not None

    visible_channels = [ch for ch in dataset_model.channels if ch.visible_as[min_keys.VOLUME]]
    for ch in visible_channels:
        assert gn_nodes.get(f"channel_load_{ch.identifier}") is not None
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

    slice_cube = mat.node_tree.nodes["Slice Cube"]
    material_output = mat.node_tree.nodes["Material Output"]
    output_input = material_output.inputs[surface.shader_output_name()]
    assert len(output_input.links) == 1
    mat.node_tree.links.remove(output_input.links[0])
    assert len(output_input.links) == 0

    reloaded = microscopynodes.load.Dataset(holder=bpy.context.scene.MiN_reload)
    reloaded.set_state(dataset_model)

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
        if not ch.visible_as[min_keys.VOLUME]:
            continue
        socket = get_socket(dataset.volume.node_group, ch, min_type="SWITCH")
        assert socket is not None
        assert dataset.volume.gn_mod[socket.identifier] == True
