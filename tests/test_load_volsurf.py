import bpy
import pytest
import tif2blender.load_components as t2b
from tif2blender.handle_blender_structs import collection_by_name, node_handling, collection_activate, make_subcollection
from .utils import get_verts, remove_all_objects
import numpy as np
from pathlib import Path
import os

# Combined volume and surface loading
otsus = [[0.36,0.17],[0.5,0.5]]
scales = [[0.02,0.02,0.062], [2,1,1]]
multiframe = [False, True]


test_folder = Path(os.path.abspath(Path(__file__).parent / 'test_data'))

def old_modifier_surface_objs(volume_collection, otsus, scale, cache_coll, base_coll):
    surf_collections = []
    # for ch_name, otsu in zip(ch_names, otsus):
    collection_activate(*cache_coll)
    for ch_name, ch_coll in enumerate(volume_collection.children):
        for vol in ch_coll.all_objects:
            surf_collection, _ = make_subcollection(f'channel {ch_name} surface')
            bpy.ops.mesh.primitive_cube_add()
            obj = bpy.context.view_layer.objects.active

            obj.name = 'surface of ' + vol.name 

            bpy.ops.object.modifier_add(type='VOLUME_TO_MESH')
            obj.modifiers[-1].object = vol
            obj.modifiers[-1].grid_name = f'data_channel_{ch_name}'
            print(ch_name, otsus)
            obj.modifiers[-1].threshold = otsus[ch_name]
            collection_activate(*base_coll)

    surf_collections.append(surf_collection)
    
    
    return [surf for surf in surf_collection.all_objects]

@pytest.mark.parametrize('otsus, scale, multiframe', zip(otsus, scales, multiframe))
@pytest.mark.parametrize('chunked', [False, True])
def test_load_volume_surface(snapshot, otsus, scale, multiframe, chunked):
    remove_all_objects()

    vdb_files = {(0, 0, 0): {'directory': str(test_folder / 'permanent_vdbs/full/x0y0z0'), 'channels': [[{'name': 'Channel 0_0.vdb'}, {'name': 'Channel 0_1.vdb'}, {'name': 'Channel 0_2.vdb'}], [{'name': 'Channel 1_0.vdb'}, {'name': 'Channel 1_1.vdb'}, {'name': 'Channel 1_2.vdb'}]]}}
    bbox_px = [79, 80, 10]
    if chunked:
        vdb_files = {
                    (0, 0, 0): {'directory': str(test_folder / 'permanent_vdbs/chunked/x0y0z0'), 'channels': [[{'name': 'Channel 0_0.vdb'}, {'name': 'Channel 0_1.vdb'}, {'name': 'Channel 0_2.vdb'}], [{'name': 'Channel 1_0.vdb'}, {'name': 'Channel 1_1.vdb'}, {'name': 'Channel 1_2.vdb'}]]}, 
                    (0, 1, 0): {'directory':  str(test_folder / 'permanent_vdbs/chunked/x0y1z0'), 'channels': [[{'name': 'Channel 0_0.vdb'}, {'name': 'Channel 0_1.vdb'}, {'name': 'Channel 0_2.vdb'}], [{'name': 'Channel 1_0.vdb'}, {'name': 'Channel 1_1.vdb'}, {'name': 'Channel 1_2.vdb'}]]}, 
                    (0, 2, 0): {'directory':  str(test_folder / 'permanent_vdbs/chunked/x0y2z0'), 'channels': [[{'name': 'Channel 0_0.vdb'}, {'name': 'Channel 0_1.vdb'}, {'name': 'Channel 0_2.vdb'}], [{'name': 'Channel 1_0.vdb'}, {'name': 'Channel 1_1.vdb'}, {'name': 'Channel 1_2.vdb'}]]}, 
                    (1, 0, 0): {'directory':  str(test_folder / 'permanent_vdbs/chunked/x1y0z0'), 'channels': [[{'name': 'Channel 0_0.vdb'}, {'name': 'Channel 0_1.vdb'}, {'name': 'Channel 0_2.vdb'}], [{'name': 'Channel 1_0.vdb'}, {'name': 'Channel 1_1.vdb'}, {'name': 'Channel 1_2.vdb'}]]}, 
                    (1, 1, 0): {'directory':  str(test_folder / 'permanent_vdbs/chunked/x1y1z0'), 'channels': [[{'name': 'Channel 0_0.vdb'}, {'name': 'Channel 0_1.vdb'}, {'name': 'Channel 0_2.vdb'}], [{'name': 'Channel 1_0.vdb'}, {'name': 'Channel 1_1.vdb'}, {'name': 'Channel 1_2.vdb'}]]}, 
                    (1, 2, 0): {'directory':  str(test_folder / 'permanent_vdbs/chunked/x1y2z0'), 'channels': [[{'name': 'Channel 0_0.vdb'}, {'name': 'Channel 0_1.vdb'}, {'name': 'Channel 0_2.vdb'}], [{'name': 'Channel 1_0.vdb'}, {'name': 'Channel 1_1.vdb'}, {'name': 'Channel 1_2.vdb'}]]}
                    } 
        bbox_px = [39, 26, 10]
    
    base_coll = collection_by_name('testbase')
    cache_coll = collection_by_name('testcache')

    vol_obj, vol_coll = t2b.load_volume(vdb_files, bbox_px, otsus, scale, cache_coll, base_coll)
    for vol in vol_coll.all_objects:
        print(vol)
    # surf_obj = t2b.load_surfaces(vol_coll, otsus, scale, cache_coll, base_coll)
    modsurf_objs = old_modifier_surface_objs(vol_coll, otsus, scale, cache_coll, base_coll)
    
    verts = get_verts(modsurf_objs, apply_modifiers=True)
    snapshot.assert_match(verts, f"surface_{sum(otsus)}_{np.sum(scales)}_chunk{chunked}")
    assert("Error" not in verts)
    assert(len(verts) > 0)

    snapshot.assert_match( str(list(vol_obj.modifiers[-1].node_group.nodes)), 'volnodes') # simple test because volumes are hard to test effectively
    
    if multiframe:
        remove_all_objects()
        vol_obj, vol_coll = t2b.load_volume(vdb_files, bbox_px, otsus, scale, cache_coll, base_coll)

        bpy.context.scene.frame_set(2)
        modsurf_objs = old_modifier_surface_objs(vol_coll, otsus, scale, cache_coll, base_coll)
        verts2 = get_verts(modsurf_objs, apply_modifiers=True)
        snapshot.assert_match(verts, f"surface_{sum(otsus)}_{np.sum(scales)}_frame2_chunk{chunked}")
        assert("Error" not in verts)
        assert(verts != verts2)
    
    surf_obj = t2b.load_surfaces(vol_coll, otsus, scale, cache_coll, base_coll)
    snapshot.assert_match( str(list(surf_obj.modifiers[-1].node_group.nodes)), 'surfnodes') # simple test because volumes are hard to test effectively

