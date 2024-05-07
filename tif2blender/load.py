import bpy
from bpy.props import (StringProperty, FloatProperty,
                        PointerProperty, IntProperty
                        )
from pathlib import Path
import numpy as np

from .initial_global_settings import preset_environment
from .handle_blender_structs import *
from .load_components import *



def changePathTif(self, context):
    # infers metadata, resets to default if not found
    # the raise gets handled upstream, so only prints to cli, somehow.
    try: 
        import tifffile
        with tifffile.TiffFile(context.scene.path_tif) as ifstif:
            try:
                context.scene.axes_order = ifstif.series[0].axes.lower().replace('s', 'c')
            except Exception as e:
                print(e)
                context.scene.property_unset("axes_order")
            try:
                context.scene.xy_size = ifstif.pages[0].tags['XResolution'].value[1]/ifstif.pages[0].tags['XResolution'].value[0]
            except Exception as e:
                print(e)
                context.scene.property_unset("xy_size")
            try:
                context.scene.z_size = dict(ifstif.imagej_metadata)['spacing']
            except Exception as e:
                print(e)
                context.scene.property_unset("z_size")
            # if this gets improved in bpy: set max of maskchannel selector
    except Exception as e:
        context.scene.property_unset("axes_order")
        context.scene.property_unset("xy_size")
        context.scene.property_unset("z_size")
        raise
    return

bpy.types.Scene.TL_remake = bpy.props.BoolProperty(
    name = "TL_remake", 
    description = "Force remaking vdb files",
    default = False
    )

bpy.types.Scene.TL_preset_environment = bpy.props.BoolProperty(
    name = "TL_preset_environment", 
    description = "Set environment variables",
    default = True
    )

bpy.types.Scene.TL_otsu = bpy.props.BoolProperty(
    name = "TL_otsu", 
    description = "Otsu on load (slow for big data)",
    default = True
    )

bpy.types.Scene.T2B_input_file = StringProperty(
        name="",
        description="tif file",
        update=changePathTif,
        options = {'TEXTEDIT_UPDATE'},
        default="",
        maxlen=1024,
        subtype='FILE_PATH')

bpy.types.Scene.T2B_cache_dir = StringProperty(
        description = 'Location to cache VDB and ABC files',
    options = {'TEXTEDIT_UPDATE'},
    default = str(Path('~', '.tif2blender').expanduser()),
    subtype = 'FILE_PATH'
    )

bpy.types.Scene.axes_order = StringProperty(
        name="",
        description="axes order (only z is used currently)",
        default="zyx",
        maxlen=6)
    
bpy.types.Scene.xy_size = FloatProperty(
        name="",
        description="xy physical pixel size in micrometer",
        default=1.0)
    
bpy.types.Scene.z_size = FloatProperty(
        name="",
        description="z physical pixel size in micrometer",
        default=1.0)

bpy.types.Scene.T2B_mask_channels = StringProperty(
        name="",
        description="channels with an integer label mask",
        )


def unpack_tif(input_file, axes_order, test=False):
    import tifffile
    with tifffile.TiffFile(input_file) as ifstif:
        imgdata = ifstif.asarray()

    if len(axes_order) != len(imgdata.shape):
        raise ValueError("axes_order length does not match data shape: " + str(imgdata.shape))

    for dim in 'tzcyx':
        if dim not in axes_order:
            imgdata = imgdata.expand_dims(axis=0)
            axes_order = dim + axes_order

    mask_channels = []
    if bpy.context.scene.T2B_mask_channels != '':
        try:
            mask_channels = [int(ch.strip()) for ch in bpy.context.scene.T2B_mask_channels.split(',') if '-' not in ch]
            # mask_channels.extend([list(np.arange(int(ch.strip().split('-')[0]),int(ch.strip().split('-')[1]))) for ch in bpy.context.scene.T2B_mask_channels.split(',')if '-' in ch])
        except:
            raise ValueError("could not interpret maskchannels")
        if max(mask_channels) >= imgdata.shape[axes_order.find('c')]:
            raise ValueError(f"mask channel is too high, max is {imgdata.shape[axes_order.find('c')]-1}, it starts counting at 0" )
    
    mask_arrays = {}
    for ch in mask_channels:
        mask_arrays[ch] = imgdata.take(indices=ch, axis=axes_order.find('c'))
    # volume_array = np.delete(imgdata, mask_channels, axis=axes_order.find('c'))
    volume_array = imgdata
    
    # normalize values per channel
    volume_array = volume_array.astype(np.float32)
    ch_first = np.moveaxis(volume_array, axes_order.find('c'), 0)
    for chix, chdata in enumerate(ch_first):
        ch_first[chix] -= np.min(chdata)
        ch_first[chix] /= np.max(chdata)
    channels = volume_array.shape[axes_order.find('c')] - len(mask_channels)
    all_channels = imgdata.shape[axes_order.find('c')]
    

    # otsu compute in z MIP
    otsus = [-1] * all_channels
    
    if bpy.context.scene.TL_otsu:
        for channel in range(channels):
            ix = sorted(list(set(range(all_channels)) - set(mask_channels)))[channel]
            if channels > 1:
                im = volume_array.take(indices=channel, axis=axes_order.find('c'))
            else:
                im = volume_array
            ch_axes = axes_order.replace("c","")
            z_MIP = np.amax(im, axis = ch_axes.find('z'))
            threshold_range = np.linspace(0,1,101)
            criterias = [compute_otsu_criteria(z_MIP, th) for th in threshold_range]
            otsus[ix] = threshold_range[np.argmin(criterias)]

    size_px = np.array([imgdata.shape[axes_order.find('x')], imgdata.shape[axes_order.find('y')], imgdata.shape[axes_order.find('z')]])
    
    return volume_array, mask_arrays, otsus, size_px, axes_order


# adapted from https://en.wikipedia.org/wiki/Otsu%27s_method
# TODO see if skimage is there and then use that one + do some planes, and not MIP
def compute_otsu_criteria(im, th):
    """Otsu's method to compute criteria."""
    # create the thresholded image
    # print(th)
    thresholded_im = np.zeros(im.shape)
    thresholded_im[im >= th] = 1

    # compute weights
    nb_pixels = im.size
    nb_pixels1 = np.count_nonzero(thresholded_im)
    weight1 = nb_pixels1 / nb_pixels
    weight0 = 1 - weight1

    # if one of the classes is empty, eg all pixels are below or above the threshold, that threshold will not be considered
    # in the search for the best threshold
    if weight1 == 0 or weight0 == 0:
        return np.inf

    # find all pixels belonging to each class
    val_pixels1 = im[thresholded_im == 1]
    val_pixels0 = im[thresholded_im == 0]

    # compute variance of these classes
    var1 = np.var(val_pixels1) if len(val_pixels1) > 0 else 0
    var0 = np.var(val_pixels0) if len(val_pixels0) > 0 else 0

    return weight0 * var0 + weight1 * var1


def load():
    # input_file = scn.path_tif, xy_scale=scn.xy_size, z_scale=scn.z_size, axes_order=scn.axes_order
    orig_cache = bpy.context.scene.T2B_cache_dir
    input_file = bpy.context.scene.T2B_input_file
    # this could be cleaner
    cache_dir = str(Path(bpy.context.scene.T2B_cache_dir) / Path(input_file).stem)
    
    base_coll = collection_by_name('Collection')
    collection_activate(base_coll)
    collection_by_name('cache')
    cache_coll = collection_by_name(Path(input_file).stem, supercollections=['cache'], duplicate=True)
    
    if bpy.context.scene.TL_preset_environment:
        preset_environment()
    
    # pads axes order with 1-size elements for missing axes
    volume_array, mask_arrays, otsus, size_px, axes_order = unpack_tif(input_file, axes_order)

    objects = []

    center_loc = np.array([0.5,0.5,0]) # offset of center (center in x, y, z of obj)
    init_scale = 0.02
    scale =  np.array([1,1,z_scale/xy_scale])*init_scale
    loc =  tuple(center_loc * size_px*scale)

    if len(mask_arrays) != len(otsus):
        vol_obj, vol_coll = load_volume(volume_array, otsus, scale, cache_coll, base_coll)
        surf_obj = load_surfaces(vol_coll, otsus, scale, cache_coll, base_coll)
        objects.extend([vol for vol in vol_coll.all_objects])
        objects.extend([vol_obj, surf_obj])
    
    if len(mask_arrays) > 0:
        mask_obj, mask_colls = load_labelmask(mask_arrays, scale, cache_coll, base_coll)
        [objects.extend([mask for mask in mask_coll.all_objects])for mask_coll in mask_colls]
        objects.extend([mask_obj])

    axes_obj = init_axes(size_px, init_scale, loc)
    objects.append(axes_obj)

    container = init_container(objects ,location=loc, name=Path(input_file).stem)
    collection_deactivate('cache')
    axes_obj.select_set(True)

    bpy.context.scene.T2B_cache_dir = orig_cache
    return



