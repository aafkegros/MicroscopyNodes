import bpy
from pathlib import Path
import numpy as np

class ArrayLoader():
    suffix = None

    def checkPath(self):
        return Path(bpy.context.scene.MiN_input_file).suffix == self.suffix

    def changePath(self, context):
        return

    def load_array(self, input_file):
        return 

    def unpack_array(self, input_file, axes_order, mask_channels_str):
        from skimage.filters import threshold_otsu
        imgdata = self.load_array(input_file)
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
                # mask_channels.extend([list(np.arange(int(ch.strip().split('-')[0]),int(ch.strip().split('-')[1]))) for ch in bpy.context.scene.MiN_mask_channels.split(',')if '-' in ch])
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



