import bpy
import os
import pytest
import tifffile
import itertools
import numpy as np
import tif_loader
from pathlib import Path
import shutil

standard_orders = ["tzcyx", "xyz", "zcyx", "zyx", "xyzc"]

orders_5d = ["".join(s) for s in itertools.permutations("tzcyx", 5)]
orders_c4d = ["".join(s) for s in itertools.permutations("zcyx", 4)]
orders_t4d  = ["".join(s) for s in itertools.permutations("tzyx", 4)]
orders_3d = ["".join(s) for s in itertools.permutations("zyx", 3)]
all_orders = orders_3d+orders_c4d+orders_t4d+orders_5d #174 orders

test_folder = Path(os.path.abspath(Path(__file__).parent / 'test_data'))

def load_with_axes_order(axes_order, shape):
    np.random.seed(1)
    data = (np.random.rand(*shape) * 255).astype(np.uint8)
    xy_size = 1.0 # not tested here, just for tifwriting
    z_size = 1.0 
    fname = test_folder / f"test_{axes_order}_.tif"
    imwrite_kwargs = {"metadata":{"axes":axes_order, "Spacing": z_size}, "resolution":(xy_size, xy_size),"photometric":'minisblack', "planarconfig":'separate'}
    tifffile.imwrite(str(fname), data, **imwrite_kwargs)

    volume_folder = test_folder / "blender_volumes"
    if volume_folder.exists():
        shutil.rmtree(volume_folder)
    assert not volume_folder.exists()

    tif_loader.load.unpack_tif_to_vdbs(fname, axes_order, test=True)
    
    for chunkfolder in [f for f in volume_folder.iterdir() if f.is_dir()]:
        timefiles = list(chunkfolder.glob(f"test_{axes_order}_*.tif"))
        if 't' in axes_order:
            assert len(timefiles) == shape[axes_order.find('t')]
        else: 
            assert len(timefiles) == 1
    t0_files = volume_folder.rglob(f"test_{axes_order}_t_0.tif")
    new_shape = np.array([0,0,0,0])
    chunkpatterns = [fname.parent.name for fname in t0_files]
    chunks = [0,0,0,0] #cxyz
    for pattern in chunkpatterns:
        chunks[1] = max(chunks[1], int(pattern[1]))
        chunks[2] = max(chunks[2], int(pattern[3]))
        chunks[3] = max(chunks[3], int(pattern[5]))
    chunks = np.array(chunks) + 1
    for chunkfile in  volume_folder.rglob(f"test_{axes_order}_t_0.tif"):
        with tifffile.TiffFile(chunkfile) as ifstif:
            imgdata = ifstif.asarray()
            new_shape += imgdata.shape
    
    for ax in range(4):
        for ax2 in range(4):
            if ax != ax2:
                new_shape[ax] /= chunks[ax2]

    expected_shape = shape.copy()
    expected_shape = np.array([shape[ax] for ax in [axes_order.find('c'), axes_order.find('x'), axes_order.find('y'), axes_order.find('z')]])
    if 'c' not in axes_order:
        expected_shape[0] = 1
    assert np.array_equal(expected_shape, new_shape)

    for created_file in test_folder.rglob(f"test_{axes_order}*.tif"):
        created_file.unlink()
    for chunkfolder in [f for f in volume_folder.iterdir() if f.is_dir()]:
        chunkfolder.rmdir()
    volume_folder.rmdir()
    return 

    

@pytest.mark.parametrize("axes_order", all_orders)
def test_loading_all(axes_order):
    shape = np.array(list(range(len(axes_order))))+2 # smallest distinguishable lengths over 1
    load_with_axes_order(axes_order, shape)

# @pytest.mark.parametrize("axes_order", all_orders)
@pytest.mark.parametrize("axes_order", standard_orders)
def test_loading_big(axes_order):
    shape = np.array(list(range(len(axes_order))))+2 # smallest distinguishable lengths over 1
    for ax_xyz in [ axes_order.find('x'), axes_order.find('y')]:
        shape[ax_xyz] += 2048
    load_with_axes_order(axes_order, shape)
    # Do this twice to try xy, yz but not make a too big array for xyz
    shape = np.array(list(range(len(axes_order))))+2 # smallest distinguishable lengths over 1
    for ax_xyz in [ axes_order.find('y'), axes_order.find('z')]:
        shape[ax_xyz] += 2048
    load_with_axes_order(axes_order, shape)
    