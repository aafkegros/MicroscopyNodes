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
    from skimage.filters import threshold_otsu
    with tifffile.TiffFile(input_file) as ifstif:
        imgdata = ifstif.asarray()

    if len(axes_order) != len(imgdata.shape):
        raise ValueError("axes_order length does not match data shape: " + str(imgdata.shape))

    size_px = np.array([imgdata.shape[axes_order.find('x')], imgdata.shape[axes_order.find('y')], imgdata.shape[axes_order.find('z')]])

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
    volume_arrays = {}
    for ch in range(imgdata.shape[axes_order.find('c')]):
        if ch in mask_channels:
            mask_arrays[ch] = {'data':imgdata.take(indices=ch, axis=axes_order.find('c'))}
        else:
            volume_arrays[ch] = {'data':imgdata.take(indices=ch, axis=axes_order.find('c'))}
    axes_order = axes_order.replace("c","")

    # normalize values per channel
    for ch in volume_arrays:
        volume_array = volume_arrays[ch]['data']
        volume_array = volume_array.astype(np.float32)
        volume_array -= np.min(volume_array)
        volume_array /= np.max(volume_array)
        volume_arrays[ch]['data'] = volume_array
        volume_arrays[ch]['otsu'] = threshold_otsu(np.amax(volume_array, axis = axes_order.find('z')))

    return volume_arrays, mask_arrays, size_px, axes_order
