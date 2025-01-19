import numpy as np

def take_index(imgdata, indices, dim, axes_order):
    if dim in axes_order:
        return np.take(imgdata, indices=indices, axis=axes_order.find(dim))
    return imgdata

def len_axis(dim, axes_order, shape):
        if dim in axes_order:
            return shape[axes_order.find(dim)]
        return 1

def expand_to_xyz(arr, axes_order):
    # should only be called after computing dask, with no more t/c in the axes order
    # handles 1D, 2D, and ordering of data
    new_axes_order = axes_order
    for dim in 'xyz':
        if dim not in axes_order:
            arr = np.expand_dims(arr,axis=0)
            new_axes_order = dim + new_axes_order     
    return np.moveaxis(arr, [new_axes_order.find('x'),new_axes_order.find('y'),new_axes_order.find('z')],[0,1,2]).copy()
