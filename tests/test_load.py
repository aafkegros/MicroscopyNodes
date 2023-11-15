# import bpy
import os
# import pytest
import tifffile
import itertools
import numpy as np
import tif_loader
from pathlib import Path

standard_orders = ["tzcyx", "xyz", "zcyx", "zyx", "xyzc"]

orders_5d = ["".join(s) for s in itertools.permutations("tzcyx", 5)]
orders_c4d = ["".join(s) for s in itertools.permutations("zcyx", 4)]
orders_t4d  = ["".join(s) for s in itertools.permutations("tzyx", 4)]
orders_3d = ["".join(s) for s in itertools.permutations("zyx", 3)]
all_orders = orders_3d+orders_c4d+orders_t4d+orders_5d #174 orders

test_folder = Path(os.path.abspath(Path(__file__).parent / 'test_data'))

def test_loading(axes_order, shape):
    data = np.random.rand(*shape)
    xy_size = 0.5
    z_size = 1.5 
    fname = test_folder / f"test_{axes_order}.tif"
    imwrite_kwargs = {"metadata":{"axes":axes_order, "Spacing": z_size}, "resolution":(xy_size, xy_size), "imagej":True}
    tifffile.imwrite(str(fname), data, **imwrite_kwargs)

    tif_loader.load_tif(input_file, xy_scale, z_scale, axes_order)

@pytest.mark.parametrize("axes_order", all_orders)
def test_loading_all(axes_order):
    shape = list(range(len(axes_order)))+2 # smallest distinguishable lengths over 1
    test_loading(axes_order, shape)

@pytest.mark.parametrize("axes_order", standard_orders)
def test_loading_big(axes_order):
    shape = [2049]*len(axes_order) 
    test_loading(axes_order, shape)
    