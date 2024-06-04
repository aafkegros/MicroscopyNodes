import numpy as np


def changePathTif(self, context):
    # infers metadata, resets to default if not found
    # the raise gets handled upstream, so only prints to cli, somehow.
    try: 
        import tifffile
        with tifffile.TiffFile(context.scene.T2B_input_file) as ifstif:
            try:
                context.scene.T2B_axes_order = ifstif.series[0].axes.lower().replace('s', 'c')
            except Exception as e:
                print(e)
                context.scene.property_unset("T2B_axes_order")
            try:
                context.scene.T2B_xy_size = ifstif.pages[0].tags['XResolution'].value[1]/ifstif.pages[0].tags['XResolution'].value[0]
            except Exception as e:
                print(e)
                context.scene.property_unset("T2B_xy_size")
            try:
                context.scene.T2B_z_size = dict(ifstif.imagej_metadata)['spacing']
            except Exception as e:
                print(e)
                context.scene.property_unset("T2B_z_size")
    except Exception as e:
        context.scene.property_unset("axes_order")
        context.scene.property_unset("xy_size")
        context.scene.property_unset("z_size")
        raise
    return

def unpack_tif(input_file, axes_order, mask_channels_str, test=False):
    import tifffile
    with tifffile.TiffFile(input_file) as ifstif:
        imgdata = ifstif.asarray()

    if len(axes_order) != len(imgdata.shape):
        raise ValueError("axes_order length does not match data shape: " + str(imgdata.shape))

    for dim in 'tzcyx':
        if dim not in axes_order:
            imgdata = np.expand_dims(imgdata,axis=0)
            axes_order = dim + axes_order

    mask_channels = []
    if mask_channels_str != '':
        try:
            mask_channels = [int(ch.strip()) for ch in mask_channels_str.split(',') if '-' not in ch]
            # mask_channels.extend([list(np.arange(int(ch.strip().split('-')[0]),int(ch.strip().split('-')[1]))) for ch in bpy.context.scene.T2B_mask_channels.split(',')if '-' in ch])
        except:
            raise ValueError("could not interpret maskchannels")
        if max(mask_channels) >= imgdata.shape[axes_order.find('c')]:
            raise ValueError(f"mask channel is too high, max is {imgdata.shape[axes_order.find('c')]-1}, it starts counting at 0" )
    
    mask_arrays = {}
    for ch in mask_channels:
        mask_arrays[ch] = imgdata.take(indices=ch, axis=axes_order.find('c'))
        # maybe check input here?
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
    
    
    for channel in range(channels):
        ix = sorted(list(set(range(all_channels)) - set(mask_channels)))[channel]
        if channels > 1:
            im = volume_array.take(indices=channel, axis=axes_order.find('c'))
        else:
            im = volume_array
        ch_axes = axes_order.replace("c","")
        z_MIP = np.amax(im, axis = ch_axes.find('z'))
        threshold_range = np.linspace(0,1,101)
        try:
            from skimage.filters import threshold_otsu
            otsus[ix] = threshold_otsu(z_MIP)
            print('used scikit image' )
        except:
            criterias = [compute_otsu_criteria(z_MIP, th) for th in threshold_range]
            otsus[ix] = threshold_range[np.argmin(criterias)]

    size_px = np.array([imgdata.shape[axes_order.find('x')], imgdata.shape[axes_order.find('y')], imgdata.shape[axes_order.find('z')]])
    print(otsus)
    return volume_array, mask_arrays, otsus, size_px, axes_order


# adapted from https://en.wikipedia.org/wiki/Otsu%27s_method
# TODO see if skimage is there and then use that one + do some planes, and not MIP
def compute_otsu_criteria(im, th):
    """Otsu's method to compute criteria."""
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
