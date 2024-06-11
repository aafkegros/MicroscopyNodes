import bpy
import pytest
import tif2blender.load_components as t2b
from tif2blender.handle_blender_structs import collection_by_name, node_handling, collection_activate, make_subcollection
from .utils import get_verts, remove_all_objects
import numpy as np
from pathlib import Path
import os
from os.path import join, dirname, realpath

# Combined volume and surface loading
scales = [[0.02,0.02,0.062], [2,1,1]]
multiframe = [False, True]
nonstartchannel = [False, True]


test_folder = Path(os.path.abspath(Path(__file__).parent / 'test_data'))
test_folder = Path(join(dirname(realpath(__file__)), "test_data"))

def old_modifier_surface_objs(volume_inputs, scale, cache_coll, base_coll):
    surf_collections = []
    # for ch_name, otsu in zip(ch_names, otsus):
    collection_activate(*cache_coll)
    for ch_name in volume_inputs:
        ch_coll = volume_inputs[ch_name]['collection']
        for vol in ch_coll.all_objects:
            surf_collection, _ = make_subcollection(f'channel {ch_name} surface')
            bpy.ops.mesh.primitive_cube_add()
            obj = bpy.context.view_layer.objects.active

            obj.name = 'surface of ' + vol.name 

            bpy.ops.object.modifier_add(type='VOLUME_TO_MESH')
            obj.modifiers[-1].object = vol
            obj.modifiers[-1].grid_name = f'data_channel_{ch_name}'
            obj.modifiers[-1].threshold = 0.5
            collection_activate(*base_coll)

    surf_collections.append(surf_collection)
    
    
    return [surf for surf in surf_collection.all_objects]

@pytest.mark.parametrize('scale, multiframe', zip(scales, multiframe))
@pytest.mark.parametrize('chunked', [False, True])
@pytest.mark.parametrize('nonstartchannel', [False, True])
def test_load_volume_surface(snapshot, scale, multiframe, chunked, nonstartchannel):
    remove_all_objects()
    volume_inputs = {
        0: {'otsu': 0.36132812, 
            'vdbs': 
                [{'directory':str(test_folder / 'permanent_vdbs/full/x0y0z0'), 
                    'files': [
                        {'name': 'Channel 0_0.vdb'}, 
                        {'name': 'Channel 0_1.vdb'}, 
                        {'name': 'Channel 0_2.vdb'}], 
                        'pos': (0, 0, 0)}]
                        }, 
        1: {'otsu': 0.16601562, 
            'vdbs': 
                [{'directory': str(test_folder / 'permanent_vdbs/full/x0y0z0'), 
                    'files': [
                        {'name': 'Channel 1_0.vdb'}, 
                        {'name': 'Channel 1_1.vdb'}, 
                        {'name': 'Channel 1_2.vdb'}], 
                        'pos': (0, 0, 0)}
                        ]
            }
        }
    if nonstartchannel:
        del volume_inputs[0]
    bbox_px = [79, 80, 10]
    if chunked:
        {
            0: {
                'otsu': 0.36132812, 
                'vdbs': [
                    {'directory': str(test_folder / 'permanent_vdbs/chunked/x0y0z0'), 'files': [{'name': 'Channel 0_0.vdb'}, {'name': 'Channel 0_1.vdb'}, {'name': 'Channel 0_2.vdb'}], 'pos': (0, 0, 0)}, 
                    {'directory': str(test_folder / 'permanent_vdbs/full/x0y1z0'), 'files': [{'name': 'Channel 0_0.vdb'}, {'name': 'Channel 0_1.vdb'}, {'name': 'Channel 0_2.vdb'}], 'pos': (0, 1, 0)}, 
                    {'directory': str(test_folder / 'permanent_vdbs/full/x1y0z0'), 'files': [{'name': 'Channel 0_0.vdb'}, {'name': 'Channel 0_1.vdb'}, {'name': 'Channel 0_2.vdb'}], 'pos': (1, 0, 0)}, 
                    {'directory':str(test_folder / 'permanent_vdbs/full/x1y1z0'), 'files': [{'name': 'Channel 0_0.vdb'}, {'name': 'Channel 0_1.vdb'}, {'name': 'Channel 0_2.vdb'}], 'pos': (1, 1, 0)}
                ]
            }, 
            1: {
                'otsu': 0.16601562, 
                'vdbs': [
                    {'directory': str(test_folder / 'permanent_vdbs/full/x0y0z0'), 'files': [{'name': 'Channel 1_0.vdb'}, {'name': 'Channel 1_1.vdb'}, {'name': 'Channel 1_2.vdb'}], 'pos': (0, 0, 0)}, 
                    {'directory': str(test_folder / 'permanent_vdbs/full/x0y1z0'), 'files': [{'name': 'Channel 1_0.vdb'}, {'name': 'Channel 1_1.vdb'}, {'name': 'Channel 1_2.vdb'}], 'pos': (0, 1, 0)}, 
                    {'directory': str(test_folder / 'permanent_vdbs/full/x1y0z0'), 'files': [{'name': 'Channel 1_0.vdb'}, {'name': 'Channel 1_1.vdb'}, {'name': 'Channel 1_2.vdb'}], 'pos': (1, 0, 0)}, 
                    {'directory': str(test_folder / 'permanent_vdbs/full/x1y1z0'), 'files': [{'name': 'Channel 1_0.vdb'}, {'name': 'Channel 1_1.vdb'}, {'name': 'Channel 1_2.vdb'}], 'pos': (1, 1, 0)}]}}
        bbox_px = [39, 26, 10] #incorrect, but that's not an issue
    
    base_coll = collection_by_name('testbase')
    cache_coll = collection_by_name('testcache')

    emission_setting = False 

    vol_obj, vol_inputs_mod = t2b.load_volume(volume_inputs, bbox_px, scale, cache_coll, base_coll, emission_setting)

    modsurf_objs = old_modifier_surface_objs(vol_inputs_mod, scale, cache_coll, base_coll)
    
    verts = get_verts(modsurf_objs, apply_modifiers=True)
    snapshot.assert_match(verts, f"surface_{np.sum(scales)}_nonstart{nonstartchannel}_chunk{chunked}")
    assert("Error" not in verts)
    assert(len(verts) > 0)

    snapshot.assert_match( str(list(vol_obj.modifiers[-1].node_group.nodes)), 'volnodes') # simple test because volumes are hard to test effectively
    
    if multiframe:
        remove_all_objects()
        vol_obj, vol_inputs_mod = t2b.load_volume(volume_inputs, bbox_px, scale, cache_coll, base_coll, emission_setting)

        bpy.context.scene.frame_set(2)
        for ch in vol_inputs_mod:
            modsurf_objs = old_modifier_surface_objs(vol_inputs_mod, scale, cache_coll, base_coll)
    
        verts2 = get_verts(modsurf_objs, apply_modifiers=True)
        snapshot.assert_match(verts, f"surface_{np.sum(scales)}_nonstart{nonstartchannel}_chunk{chunked}_frame2")
        assert("Error" not in verts)
        assert(verts != verts2)
    
    surf_obj = t2b.load_surfaces(volume_inputs, scale, cache_coll, base_coll)
    snapshot.assert_match( str(list(surf_obj.modifiers[-1].node_group.nodes)), 'surfnodes') # simple test because volumes are hard to test effectively

